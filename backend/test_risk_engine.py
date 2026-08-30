"""Unit tests for compute_risk()."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from risk_engine import compute_risk

# (label, confidence, humidity, rainfall_3day_mm, growth_stage, nearby, expected_level)
CASES = [
    (
        "all five true (score 7)",
        0.92,
        85.0,
        25.0,
        "Flowering",
        3,
        "HIGH",
    ),
    (
        "all five false (score 0)",
        0.70,
        80.0,
        20.0,
        "Seedling",
        2,
        "LOW",
    ),
    (
        "score == 5 HIGH boundary",
        0.71,
        81.0,
        0.0,
        "Vegetative",
        3,
        "HIGH",
    ),
    (
        "score == 3 MEDIUM lower edge",
        0.50,
        81.0,
        21.0,
        "Fruiting",
        0,
        "MEDIUM",
    ),
    (
        "score == 4 MEDIUM upper edge",
        0.80,
        70.0,
        0.0,
        "Maturity",
        3,
        "MEDIUM",
    ),
]


def test_all_five_factors_true_is_high() -> None:
    level, checklist = compute_risk(0.92, 85.0, 25.0, "Flowering", 3)
    assert level == "HIGH"
    assert len(checklist) == 5
    assert all(item["passed"] for item in checklist)


def test_all_five_factors_false_is_low() -> None:
    level, checklist = compute_risk(0.70, 80.0, 20.0, "Seedling", 2)
    assert level == "LOW"
    assert len(checklist) == 5
    assert not any(item["passed"] for item in checklist)


def test_score_exactly_5_is_high() -> None:
    # +2 confidence, +1 humidity, +2 nearby = 5
    level, checklist = compute_risk(0.71, 81.0, 0.0, "Vegetative", 3)
    assert level == "HIGH"
    assert len(checklist) == 5
    assert [item["passed"] for item in checklist] == [True, True, False, False, True]


def test_score_exactly_3_is_medium() -> None:
    # +1 humidity, +1 rainfall, +1 stage = 3
    level, checklist = compute_risk(0.50, 81.0, 21.0, "Fruiting", 0)
    assert level == "MEDIUM"
    assert len(checklist) == 5
    assert [item["passed"] for item in checklist] == [False, True, True, True, False]


def test_score_exactly_4_is_medium() -> None:
    # +2 confidence, +2 nearby = 4
    level, checklist = compute_risk(0.80, 70.0, 0.0, "Maturity", 3)
    assert level == "MEDIUM"
    assert len(checklist) == 5
    assert [item["passed"] for item in checklist] == [True, False, False, False, True]


def test_checklist_always_has_five_entries() -> None:
    for _label, conf, hum, rain, stage, nearby, _expected in CASES:
        _level, checklist = compute_risk(conf, hum, rain, stage, nearby)
        assert len(checklist) == 5
        for item in checklist:
            assert set(item.keys()) == {"factor", "passed", "detail"}
            assert isinstance(item["passed"], bool)
            assert isinstance(item["factor"], str)
            assert isinstance(item["detail"], str)


if __name__ == "__main__":
    print(f"{'case':<32} {'level':<8} {'conf':>6} {'hum':>6} {'rain':>7} {'stage':<12} {'near':>4}")
    print("-" * 82)
    for label, conf, hum, rain, stage, nearby, expected in CASES:
        level, checklist = compute_risk(conf, hum, rain, stage, nearby)
        marker = "OK" if level == expected else f"MISMATCH (want {expected})"
        print(
            f"{label:<32} {level:<8} {conf:6.2f} {hum:6.1f} {rain:7.1f} {stage:<12} {nearby:4d}  {marker}  checklist={len(checklist)}"
        )
