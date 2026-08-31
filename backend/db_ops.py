"""Database read/write operations for AgriSentinel reports and traps."""

from __future__ import annotations

import logging
import math
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    DISEASE_CLASSES,
    GROWTH_STAGES,
    Report,
    TrapObservation,
    session_scope,
)
from risk_engine import NEARBY_RADIUS_KM, compute_risk
from weather import get_weather

logger = logging.getLogger(__name__)

VALID_STATUSES = ("pending", "confirmed", "rejected", "sent_to_lab")
_EARTH_RADIUS_KM = 6371.0
_RISK_SORT_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _require_float(value: object, name: str) -> float:
    """Coerce ``value`` to float or raise ValueError."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a float, got {value!r}") from exc


def _require_nonempty_str(value: object, name: str) -> str:
    """Coerce ``value`` to a non-empty string or raise ValueError."""
    if value is None:
        raise ValueError(f"{name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be a non-empty string")
    return text


def _require_confidence(value: object) -> float:
    """Coerce confidence to a 0.0–1.0 float or raise ValueError."""
    confidence = _require_float(value, "confidence")
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError(f"confidence must be between 0.0 and 1.0, got {confidence}")
    return confidence


def _parse_iso_date(value: object, name: str) -> date:
    """Parse a YYYY-MM-DD date string or raise ValueError."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a YYYY-MM-DD date, got {value!r}") from exc


def _report_to_dict(row: Report) -> dict[str, Any]:
    """Serialize a Report ORM row to a plain dict."""
    return {
        "id": row.id,
        "farm_id": row.farm_id,
        "image_path": row.image_path,
        "crop": row.crop,
        "growth_stage": row.growth_stage,
        "predicted_disease": row.predicted_disease,
        "confidence": row.confidence,
        "gradcam_path": row.gradcam_path,
        "severity": row.severity,
        "status": row.status,
        "lat": row.lat,
        "lon": row.lon,
        "district": row.district,
        "created_at": row.created_at,
        "expert_notes": row.expert_notes,
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 points.

    Parameters:
        lat1, lon1: Origin latitude and longitude in degrees.
        lat2, lon2: Destination latitude and longitude in degrees.

    Returns:
        Distance in kilometres.

    Raises:
        ValueError: If any coordinate cannot be coerced to float.
    """
    lat1_f = _require_float(lat1, "lat1")
    lon1_f = _require_float(lon1, "lon1")
    lat2_f = _require_float(lat2, "lat2")
    lon2_f = _require_float(lon2, "lon2")
    phi1 = math.radians(lat1_f)
    phi2 = math.radians(lat2_f)
    d_phi = math.radians(lat2_f - lat1_f)
    d_lambda = math.radians(lon2_f - lon1_f)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def insert_report(
    farm_id: str,
    image_path: str,
    crop: str,
    growth_stage: str,
    predicted_disease: str,
    confidence: float,
    lat: float,
    lon: float,
    district: str,
    gradcam_path: str | None = None,
) -> int:
    """Insert a pending crop-health report and return its id.

    Parameters:
        farm_id: Simulated farmer/farm identifier.
        image_path: Path to the uploaded leaf image (saved by M3).
        crop: Crop name stored as a real column (not hardcoded).
        growth_stage: Must be one of GROWTH_STAGES.
        predicted_disease: Must be one of DISEASE_CLASSES.
        confidence: Model confidence on a 0.0–1.0 scale.
        lat: Farm latitude.
        lon: Farm longitude.
        district: District name used for weather cache and filters.
        gradcam_path: Optional Grad-CAM image path; NULL if omitted.

    Returns:
        The new report's integer primary key.

    Raises:
        ValueError: Invalid growth_stage, predicted_disease, lat, lon,
            confidence, or missing required strings.
        RuntimeError: Database write failed after validation.
    """
    farm_id_s = _require_nonempty_str(farm_id, "farm_id")
    image_path_s = _require_nonempty_str(image_path, "image_path")
    crop_s = _require_nonempty_str(crop, "crop")
    growth_stage_s = _require_nonempty_str(growth_stage, "growth_stage")
    predicted_disease_s = _require_nonempty_str(predicted_disease, "predicted_disease")
    district_s = _require_nonempty_str(district, "district")

    if growth_stage_s not in GROWTH_STAGES:
        raise ValueError(
            f"growth_stage must be one of {GROWTH_STAGES}, got {growth_stage_s!r}"
        )
    if predicted_disease_s not in DISEASE_CLASSES:
        raise ValueError(
            f"predicted_disease must be one of {DISEASE_CLASSES}, got {predicted_disease_s!r}"
        )

    confidence_f = _require_confidence(confidence)
    lat_f = _require_float(lat, "lat")
    lon_f = _require_float(lon, "lon")
    gradcam = None if gradcam_path is None else str(gradcam_path)

    try:
        with session_scope() as session:
            row = Report(
                farm_id=farm_id_s,
                image_path=image_path_s,
                crop=crop_s,
                growth_stage=growth_stage_s,
                predicted_disease=predicted_disease_s,
                confidence=confidence_f,
                gradcam_path=gradcam,
                severity=None,
                status="pending",
                lat=lat_f,
                lon=lon_f,
                district=district_s,
                created_at=datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            return int(row.id)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("insert_report: database write failed")
        raise RuntimeError("insert_report failed to write the report") from exc


def get_nearby_confirmed_count(
    lat: float,
    lon: float,
    radius_km: float,
    days: int = 14,
) -> int:
    """Count confirmed reports within ``radius_km`` in the last ``days`` days.

    Loads matching rows then filters with ``haversine_km`` in Python.

    Parameters:
        lat: Origin latitude.
        lon: Origin longitude.
        radius_km: Inclusive radius in kilometres.
        days: Lookback window in days (default 14).

    Returns:
        Integer count. Returns 0 if inputs are unusable or the query fails.

    Raises:
        This function does not raise to callers; errors are logged.
    """
    try:
        lat_f = _require_float(lat, "lat")
        lon_f = _require_float(lon, "lon")
        radius_f = _require_float(radius_km, "radius_km")
        days_i = int(days)
        if days_i < 0:
            raise ValueError("days must be >= 0")
    except (TypeError, ValueError):
        logger.exception("get_nearby_confirmed_count: invalid arguments")
        return 0

    cutoff = datetime.utcnow() - timedelta(days=days_i)
    try:
        with session_scope() as session:
            rows = (
                session.query(Report)
                .filter(Report.status == "confirmed", Report.created_at >= cutoff)
                .all()
            )
            count = 0
            for row in rows:
                try:
                    distance = haversine_km(lat_f, lon_f, row.lat, row.lon)
                except ValueError:
                    continue
                if distance <= radius_f:
                    count += 1
            return count
    except Exception:
        logger.exception("get_nearby_confirmed_count: query failed")
        return 0


def evaluate_and_update_risk(report_id: int) -> tuple[str, list[dict]]:
    """Compute risk for a report, persist severity, and return the checklist.

    Looks up the report, calls ``get_weather`` and ``get_nearby_confirmed_count``,
    scores with ``compute_risk`` using ``weather["rainfall_3day_mm"]``, writes
    ``severity``, and returns ``(level, checklist)``.

    Parameters:
        report_id: Primary key of an existing reports row.

    Returns:
        ``(level, checklist)`` from ``compute_risk``.

    Raises:
        ValueError: If ``report_id`` is not an int or no such report exists.
        RuntimeError: If the severity update fails after scoring.
    """
    try:
        report_id_i = int(report_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"report_id must be an integer, got {report_id!r}") from exc

    try:
        with session_scope() as session:
            row = session.query(Report).filter(Report.id == report_id_i).one_or_none()
            if row is None:
                raise ValueError(f"report_id {report_id_i} not found")
            snapshot = {
                "lat": row.lat,
                "lon": row.lon,
                "district": row.district,
                "confidence": row.confidence,
                "growth_stage": row.growth_stage,
            }
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("evaluate_and_update_risk: failed to load report %s", report_id_i)
        raise RuntimeError("evaluate_and_update_risk failed to load the report") from exc

    weather = get_weather(snapshot["lat"], snapshot["lon"], snapshot["district"])
    nearby = get_nearby_confirmed_count(
        snapshot["lat"],
        snapshot["lon"],
        NEARBY_RADIUS_KM,
        days=14,
    )
    level, checklist = compute_risk(
        confidence=snapshot["confidence"],
        humidity=weather.get("humidity", 70.0),
        rainfall_3day_mm=weather.get("rainfall_3day_mm", 0.0),
        growth_stage=snapshot["growth_stage"],
        nearby_confirmed_count=nearby,
    )

    try:
        with session_scope() as session:
            row = session.query(Report).filter(Report.id == report_id_i).one_or_none()
            if row is None:
                raise ValueError(f"report_id {report_id_i} not found")
            row.severity = level
    except ValueError:
        raise
    except Exception as exc:
        logger.exception(
            "evaluate_and_update_risk: failed to write severity for report %s",
            report_id_i,
        )
        raise RuntimeError("evaluate_and_update_risk failed to update severity") from exc

    return level, checklist


def get_reports(
    sort_by: str = "risk",
    status_filter: str | None = None,
) -> list[dict]:
    """Return reports as plain dicts, optionally filtered and sorted.

    Parameters:
        sort_by: If ``"risk"``, order HIGH then MEDIUM then LOW, then
            ``created_at`` descending within each group. Any other value
            sorts by ``created_at`` descending only.
        status_filter: If provided, only rows with this status are returned.

    Returns:
        List of report dicts. Returns an empty list on query failure.

    Raises:
        This function does not raise to callers; errors are logged.
    """
    try:
        with session_scope() as session:
            query = session.query(Report)
            if status_filter is not None:
                status_s = str(status_filter).strip()
                query = query.filter(Report.status == status_s)
            rows = query.all()
            payload = [_report_to_dict(row) for row in rows]
    except Exception:
        logger.exception("get_reports: query failed")
        return []

    if sort_by == "risk":
        payload.sort(
            key=lambda item: (
                _RISK_SORT_RANK.get(item.get("severity") or "", 3),
                -(
                    item["created_at"].timestamp()
                    if isinstance(item.get("created_at"), datetime)
                    else 0.0
                ),
            )
        )
    else:
        payload.sort(
            key=lambda item: item.get("created_at") or datetime.min,
            reverse=True,
        )
    return payload


def update_report_status(
    report_id: int,
    new_status: str,
    expert_notes: str | None = None,
) -> bool:
    """Update a report's review status and optional expert notes.

    Parameters:
        report_id: Target report primary key.
        new_status: One of ``pending``, ``confirmed``, ``rejected``,
            or ``sent_to_lab``.
        expert_notes: Optional notes written by the extension worker.

    Returns:
        True if a row was updated, False if ``report_id`` does not exist.

    Raises:
        ValueError: If ``new_status`` is not an allowed status, or ``report_id``
            is not an integer.
        RuntimeError: Database write failed after validation.
    """
    try:
        report_id_i = int(report_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"report_id must be an integer, got {report_id!r}") from exc

    status_s = str(new_status).strip() if new_status is not None else ""
    if status_s not in VALID_STATUSES:
        raise ValueError(
            f"new_status must be one of {list(VALID_STATUSES)}, got {new_status!r}"
        )

    notes = None if expert_notes is None else str(expert_notes)

    try:
        with session_scope() as session:
            row = session.query(Report).filter(Report.id == report_id_i).one_or_none()
            if row is None:
                return False
            row.status = status_s
            row.expert_notes = notes
            return True
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("update_report_status: database write failed")
        raise RuntimeError("update_report_status failed to write the update") from exc


def insert_trap_observation(
    farm_id: str,
    pest_name: str,
    count: int,
    trap_type: str,
    observed_at: str,
    lat: float,
    lon: float,
    district: str,
) -> int:
    """Insert a pest-trap observation and return its id.

    Parameters:
        farm_id: Simulated farmer/farm identifier.
        pest_name: Pest common name.
        count: Non-negative integer trap count.
        trap_type: Trap kind, e.g. ``"pheromone trap"``.
        observed_at: Field date as ``YYYY-MM-DD``.
        lat: Observation latitude.
        lon: Observation longitude.
        district: District name.

    Returns:
        The new trap observation's integer primary key.

    Raises:
        ValueError: Negative or non-integer count, bad date, bad lat/lon,
            or missing required strings.
        RuntimeError: Database write failed after validation.
    """
    farm_id_s = _require_nonempty_str(farm_id, "farm_id")
    pest_name_s = _require_nonempty_str(pest_name, "pest_name")
    trap_type_s = _require_nonempty_str(trap_type, "trap_type")
    district_s = _require_nonempty_str(district, "district")
    observed_date = _parse_iso_date(observed_at, "observed_at")
    lat_f = _require_float(lat, "lat")
    lon_f = _require_float(lon, "lon")

    try:
        count_i = int(count)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"count must be a non-negative integer, got {count!r}") from exc
    if isinstance(count, bool) or count_i < 0:
        raise ValueError(f"count must be a non-negative integer, got {count!r}")
    if float(count) != count_i:
        raise ValueError(f"count must be a non-negative integer, got {count!r}")

    try:
        with session_scope() as session:
            row = TrapObservation(
                farm_id=farm_id_s,
                pest_name=pest_name_s,
                count=count_i,
                trap_type=trap_type_s,
                observed_at=observed_date,
                lat=lat_f,
                lon=lon_f,
                district=district_s,
            )
            session.add(row)
            session.flush()
            return int(row.id)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("insert_trap_observation: database write failed")
        raise RuntimeError("insert_trap_observation failed to write the row") from exc


def get_reports_filtered(
    disease: str | None = None,
    date_range: tuple[str, str] | None = None,
    district: str | None = None,
    confirmed_only: bool = True,
) -> list[dict]:
    """Return map-ready report dicts, optionally filtered.

    Each dict includes at least ``lat``, ``lon``, ``severity``,
    ``predicted_disease``, ``created_at``, and ``district``.

    Parameters:
        disease: If set, only this ``predicted_disease`` value.
        date_range: Optional ``(start, end)`` as ``YYYY-MM-DD`` strings,
            inclusive on the date of ``created_at``.
        district: If set, only this district.
        confirmed_only: If True (default), only ``status=="confirmed"`` rows.

    Returns:
        List of dicts. Returns an empty list on query or filter-parse failure.

    Raises:
        This function does not raise to callers; errors are logged.
    """
    try:
        with session_scope() as session:
            query = session.query(Report)
            if confirmed_only:
                query = query.filter(Report.status == "confirmed")
            if disease is not None:
                query = query.filter(Report.predicted_disease == str(disease))
            if district is not None:
                query = query.filter(Report.district == str(district))
            if date_range is not None:
                try:
                    start_d = _parse_iso_date(date_range[0], "date_range[0]")
                    end_d = _parse_iso_date(date_range[1], "date_range[1]")
                except (TypeError, ValueError, IndexError):
                    logger.exception("get_reports_filtered: invalid date_range %r", date_range)
                    return []
                start_dt = datetime(start_d.year, start_d.month, start_d.day)
                end_dt = datetime(end_d.year, end_d.month, end_d.day) + timedelta(days=1)
                query = query.filter(Report.created_at >= start_dt, Report.created_at < end_dt)
            rows = query.all()
            return [
                {
                    "id": row.id,
                    "farm_id": row.farm_id,
                    "lat": row.lat,
                    "lon": row.lon,
                    "severity": row.severity,
                    "predicted_disease": row.predicted_disease,
                    "created_at": row.created_at,
                    "district": row.district,
                }
                for row in rows
            ]
    except Exception:
        logger.exception("get_reports_filtered: query failed")
        return []


def get_case_counts_by_day(disease: str | None = None) -> list[dict]:
    """Return per-day report counts for a line chart.

    Parameters:
        disease: If set, only this ``predicted_disease`` value.

    Returns:
        ``[{"date": "YYYY-MM-DD", "count": int}, ...]`` sorted by date
        ascending. Returns an empty list on query failure.

    Raises:
        This function does not raise to callers; errors are logged.
    """
    try:
        with session_scope() as session:
            query = session.query(Report)
            if disease is not None:
                query = query.filter(Report.predicted_disease == str(disease))
            rows = query.all()
    except Exception:
        logger.exception("get_case_counts_by_day: query failed")
        return []

    counts: dict[str, int] = {}
    for row in rows:
        created = row.created_at
        if created is None:
            continue
        if isinstance(created, datetime):
            key = created.date().isoformat()
        elif isinstance(created, date):
            key = created.isoformat()
        else:
            continue
        counts[key] = counts.get(key, 0) + 1

    return [{"date": day, "count": counts[day]} for day in sorted(counts)]
