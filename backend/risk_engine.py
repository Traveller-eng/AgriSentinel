"""Crop-health risk scoring for AgriSentinel."""

from __future__ import annotations

CONFIDENCE_THRESHOLD = 0.7
HUMIDITY_THRESHOLD = 80.0  # percent
RAINFALL_THRESHOLD_MM = 20.0  # 3-day cumulative rainfall
HIGH_RISK_STAGES = {"Flowering", "Fruiting"}
NEARBY_CASE_THRESHOLD = 3
NEARBY_RADIUS_KM = 5.0  # used by get_nearby_confirmed_count
SCORE_HIGH_CUTOFF = 5
SCORE_MEDIUM_CUTOFF = 3


def _as_float(value: object, name: str, default: float) -> float:
    """Coerce ``value`` to float, returning ``default`` on failure."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_int(value: object, name: str, default: int) -> int:
    """Coerce ``value`` to int, returning ``default`` on failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def compute_risk(
    confidence: float,
    humidity: float,
    rainfall_3day_mm: float,
    growth_stage: str,
    nearby_confirmed_count: int,
) -> tuple[str, list[dict]]:
    """Score outbreak risk from model, weather, crop stage, and nearby cases.

    Parameters:
        confidence: Model confidence on a 0.0–1.0 scale.
        humidity: Relative humidity in percent.
        rainfall_3day_mm: Cumulative rainfall over three days, in millimetres.
        growth_stage: Crop growth stage string (compared to HIGH_RISK_STAGES).
        nearby_confirmed_count: Count of confirmed reports within the nearby radius.

    Returns:
        A tuple ``(level, checklist)`` where ``level`` is ``"LOW"``, ``"MEDIUM"``,
        or ``"HIGH"``, and ``checklist`` is a five-item list of dicts with keys
        ``factor``, ``passed``, and ``detail`` (one entry per scoring rule,
        in scoring order, including rules that did not fire).

    Raises:
        This function does not raise. Invalid numeric inputs are coerced to
        safe defaults (0); an unusable growth_stage simply fails that rule.
    """
    confidence_f = _as_float(confidence, "confidence", 0.0)
    humidity_f = _as_float(humidity, "humidity", 0.0)
    rainfall_f = _as_float(rainfall_3day_mm, "rainfall_3day_mm", 0.0)
    nearby_i = _as_int(nearby_confirmed_count, "nearby_confirmed_count", 0)
    stage = str(growth_stage) if growth_stage is not None else ""

    conf_passed = confidence_f > CONFIDENCE_THRESHOLD
    hum_passed = humidity_f > HUMIDITY_THRESHOLD
    rain_passed = rainfall_f > RAINFALL_THRESHOLD_MM
    stage_passed = stage in HIGH_RISK_STAGES
    nearby_passed = nearby_i >= NEARBY_CASE_THRESHOLD

    score = 0
    if conf_passed:
        score += 2
    if hum_passed:
        score += 1
    if rain_passed:
        score += 1
    if stage_passed:
        score += 1
    if nearby_passed:
        score += 2

    if score >= SCORE_HIGH_CUTOFF:
        level = "HIGH"
    elif score >= SCORE_MEDIUM_CUTOFF:
        level = "MEDIUM"
    else:
        level = "LOW"

    checklist = [
        {
            "factor": "Model confidence",
            "passed": conf_passed,
            "detail": (
                f"{confidence_f * 100:.0f}% confidence "
                f"(threshold: {CONFIDENCE_THRESHOLD * 100:.0f}%)"
            ),
        },
        {
            "factor": "Humidity",
            "passed": hum_passed,
            "detail": (
                f"{humidity_f:.0f}% relative humidity "
                f"(threshold: {HUMIDITY_THRESHOLD:.0f}%)"
            ),
        },
        {
            "factor": "3-day rainfall",
            "passed": rain_passed,
            "detail": (
                f"{rainfall_f:.1f} mm over 3 days "
                f"(threshold: {RAINFALL_THRESHOLD_MM:.0f} mm)"
            ),
        },
        {
            "factor": "Growth stage",
            "passed": stage_passed,
            "detail": (
                f"Stage '{stage}' "
                f"(high-risk stages: {', '.join(sorted(HIGH_RISK_STAGES))})"
            ),
        },
        {
            "factor": "Nearby confirmed cases",
            "passed": nearby_passed,
            "detail": (
                f"{nearby_i} confirmed case(s) nearby "
                f"(threshold: {NEARBY_CASE_THRESHOLD})"
            ),
        },
    ]
    return level, checklist
