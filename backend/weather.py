"""Open-Meteo weather fetch with SQLite cache and demo-day fallbacks."""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from sqlalchemy import desc
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from models import WeatherCache, session_scope

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 5
FALLBACK_DEFAULTS = {"temp": 28.0, "humidity": 70.0, "rainfall_3day_mm": 0.0}


def _coerce_lat_lon(lat: object, lon: object) -> tuple[float, float] | None:
    """Return (lat, lon) as floats, or None if coercion fails."""
    try:
        return float(lat), float(lon)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _safe_float(value: object, default: float) -> float:
    """Coerce a numeric API field to float, substituting ``default`` if missing."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _row_to_payload(
    row: WeatherCache,
    source: str,
    stale: bool | None = None,
) -> dict:
    """Build the locked get_weather return dict from a cache row."""
    payload: dict[str, Any] = {
        "temp": _safe_float(row.temp, FALLBACK_DEFAULTS["temp"]),
        "humidity": _safe_float(row.humidity, FALLBACK_DEFAULTS["humidity"]),
        "rainfall_3day_mm": _safe_float(
            row.rainfall_mm, FALLBACK_DEFAULTS["rainfall_3day_mm"]
        ),
        "source": source,
    }
    if stale:
        payload["stale"] = True
    return payload


def _parse_open_meteo(payload: dict) -> dict:
    """Extract today's temp, humidity, and 3-day rainfall from an Open-Meteo body.

    Daily fields confirmed against current Open-Meteo Forecast API docs
    (https://open-meteo.com/en/docs): ``precipitation_sum``,
    ``temperature_2m_mean``. ``relative_humidity_2m_mean`` is accepted by
    ``/v1/forecast`` as a daily aggregation even though it is incomplete in
    some doc tables. ``past_days`` and ``timezone`` are official query params.

    Raises:
        ValueError: If the daily arrays are missing or unusable.
    """
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Open-Meteo response missing 'daily' object")

    times = daily.get("time") or []
    temps = daily.get("temperature_2m_mean") or []
    hums = daily.get("relative_humidity_2m_mean") or []
    rains = daily.get("precipitation_sum") or []
    if not times:
        raise ValueError("Open-Meteo daily.time is empty")

    today = datetime.utcnow().date()
    today_str = today.isoformat()
    try:
        today_idx = times.index(today_str)
    except ValueError:
        parsed_dates = []
        for item in times:
            try:
                parsed_dates.append(date.fromisoformat(str(item)[:10]))
            except ValueError as exc:
                raise ValueError(f"Unparseable daily.time value: {item!r}") from exc
        eligible = [i for i, d in enumerate(parsed_dates) if d <= today]
        if not eligible:
            raise ValueError("Open-Meteo daily series has no dates on or before today")
        today_idx = eligible[-1]

    start_idx = max(0, today_idx - 2)
    rain_slice = rains[start_idx : today_idx + 1]
    rainfall_3day_mm = 0.0
    for item in rain_slice:
        rainfall_3day_mm += _safe_float(item, 0.0)

    temp = _safe_float(
        temps[today_idx] if today_idx < len(temps) else None,
        FALLBACK_DEFAULTS["temp"],
    )
    humidity = _safe_float(
        hums[today_idx] if today_idx < len(hums) else None,
        FALLBACK_DEFAULTS["humidity"],
    )
    return {
        "temp": temp,
        "humidity": humidity,
        "rainfall_3day_mm": rainfall_3day_mm,
    }


def _upsert_cache(district: str, day: date, values: dict) -> None:
    """Insert or update the (district, date) weather_cache row."""
    now = datetime.utcnow()
    with session_scope() as session:
        stmt = sqlite_insert(WeatherCache).values(
            district=district,
            date=day,
            temp=values["temp"],
            humidity=values["humidity"],
            rainfall_mm=values["rainfall_3day_mm"],
            fetched_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["district", "date"],
            set_={
                "temp": values["temp"],
                "humidity": values["humidity"],
                "rainfall_mm": values["rainfall_3day_mm"],
                "fetched_at": now,
            },
        )
        session.execute(stmt)


def _fetch_open_meteo(lat: float, lon: float) -> dict:
    """Call Open-Meteo and return parsed temp / humidity / 3-day rainfall.

    Raises:
        requests.exceptions.RequestException: Network or HTTP errors.
        ValueError: Malformed JSON or missing daily fields.
        Exception: Any other parse/request failure (caller catches broadly).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
        "past_days": 3,
        "timezone": "Asia/Kolkata",
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _parse_open_meteo(response.json())


def get_weather(lat: float, lon: float, district: str) -> dict:
    """Return today's weather for a farm location, cache-first.

    Lookup order: today's cache row for ``district``; else live Open-Meteo;
    else most recent cache row for that district (``stale=True``);
    else hardcoded defaults.

    Parameters:
        lat: Farm latitude (coerced with float()).
        lon: Farm longitude (coerced with float()).
        district: Cache key / district name.

    Returns:
        Dict with keys ``temp``, ``humidity``, ``rainfall_3day_mm`` (sum of
        daily precipitation for today and the two previous days, millimetres),
        and ``source`` of ``"cache"``, ``"api"``, or ``"fallback_default"``.
        Stale cache hits also include ``"stale": True``. The SQLite column
        remains ``weather_cache.rainfall_mm``; it stores this same 3-day sum.

    Raises:
        This function does not raise. Any failure yields a usable dict.
    """
    coords = _coerce_lat_lon(lat, lon)
    district_key = str(district).strip() if district is not None else ""
    today = datetime.utcnow().date()

    if not district_key:
        logger.warning("get_weather: empty district; using fallback defaults")
        return {**FALLBACK_DEFAULTS, "source": "fallback_default"}

    try:
        with session_scope() as session:
            today_row = (
                session.query(WeatherCache)
                .filter(WeatherCache.district == district_key, WeatherCache.date == today)
                .one_or_none()
            )
            if today_row is not None:
                return _row_to_payload(today_row, source="cache")
    except Exception:
        logger.exception("get_weather: failed reading today's cache for %s", district_key)

    if coords is None:
        logger.warning(
            "get_weather: invalid lat/lon %r, %r; skipping API",
            lat,
            lon,
        )
    else:
        try:
            parsed = _fetch_open_meteo(coords[0], coords[1])
            try:
                _upsert_cache(district_key, today, parsed)
            except Exception:
                logger.exception(
                    "get_weather: fetched API weather but failed to upsert cache for %s",
                    district_key,
                )
            return {
                "temp": parsed["temp"],
                "humidity": parsed["humidity"],
                "rainfall_3day_mm": parsed["rainfall_3day_mm"],
                "source": "api",
            }
        except Exception:
            logger.warning(
                "get_weather: Open-Meteo request failed for district=%s lat=%s lon=%s",
                district_key,
                lat,
                lon,
                exc_info=True,
            )

    try:
        with session_scope() as session:
            stale_row = (
                session.query(WeatherCache)
                .filter(WeatherCache.district == district_key)
                .order_by(desc(WeatherCache.fetched_at))
                .first()
            )
            if stale_row is not None:
                return _row_to_payload(stale_row, source="cache", stale=True)
    except Exception:
        logger.exception("get_weather: failed reading stale cache for %s", district_key)

    return {**FALLBACK_DEFAULTS, "source": "fallback_default"}
