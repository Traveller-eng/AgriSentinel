"""Seed AgriSentinel with simulated Maharashtra crop-health reports.

The generated rows are explicitly simulated for SIH internal-round demos.
They are useful for Extension and Official dashboards before field data exists.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_ops import evaluate_and_update_risk, insert_report, insert_trap_observation, update_report_status
from init_db import init_db
from models import DISEASE_CLASSES, GROWTH_STAGES, Report, TrapObservation, WeatherCache, session_scope

VILLAGES = [
    {"name": "Narayangaon", "district": "Pune", "lat": 19.1176, "lon": 73.9654},
    {"name": "Talegaon Dabhade", "district": "Pune", "lat": 18.7350, "lon": 73.6756},
    {"name": "Rahata", "district": "Ahmednagar", "lat": 19.7167, "lon": 74.4833},
    {"name": "Sinnar", "district": "Nashik", "lat": 19.8500, "lon": 74.0000},
    {"name": "Lasalgaon", "district": "Nashik", "lat": 20.1420, "lon": 74.2390},
    {"name": "Karjat", "district": "Ahmednagar", "lat": 18.5510, "lon": 75.0080},
    {"name": "Baramati", "district": "Pune", "lat": 18.1517, "lon": 74.5777},
    {"name": "Jalna", "district": "Jalna", "lat": 19.8410, "lon": 75.8864},
    {"name": "Pandharpur", "district": "Solapur", "lat": 17.6792, "lon": 75.3270},
    {"name": "Akluj", "district": "Solapur", "lat": 17.8833, "lon": 75.0167}
]


def _jitter(value: float, spread: float = 0.035) -> float:
    return value + random.uniform(-spread, spread)


def _set_created_at(report_id: int, created_at: datetime) -> None:
    with session_scope() as session:
        row = session.query(Report).filter(Report.id == report_id).one_or_none()
        if row is not None:
            row.created_at = created_at


def seed_reports(count: int, reset: bool = False, seed: int = 26131) -> None:
    random.seed(seed)
    init_db()

    if reset:
        with session_scope() as session:
            session.query(TrapObservation).delete()
            session.query(WeatherCache).delete()
            session.query(Report).delete()

    uploads = ROOT / "uploads" / "demo"
    uploads.mkdir(parents=True, exist_ok=True)
    placeholder = uploads / "simulated_leaf_placeholder.txt"
    placeholder.write_text("Simulated report placeholder; live demo uploads real images.\n", encoding="utf-8")

    created = 0
    for idx in range(1, count + 1):
        village = random.choice(VILLAGES)
        disease = random.choices(
            DISEASE_CLASSES,
            weights=[20, 24, 18, 23, 15],
            k=1,
        )[0]
        confidence = random.uniform(0.55, 0.96) if disease != "Healthy" else random.uniform(0.62, 0.91)
        stage = random.choice(GROWTH_STAGES)
        lat = _jitter(village["lat"])
        lon = _jitter(village["lon"])
        report_id = insert_report(
            farm_id=f"SIM-FARM-{idx:03d}",
            image_path=str(placeholder),
            crop="Tomato",
            growth_stage=stage,
            predicted_disease=disease,
            confidence=round(confidence, 3),
            lat=lat,
            lon=lon,
            district=village["district"],
        )
        level, _ = evaluate_and_update_risk(report_id)
        status = random.choices(
            ["confirmed", "pending", "rejected", "sent_to_lab"],
            weights=[58, 25, 10, 7],
            k=1,
        )[0]
        note = f"Simulated {level.lower()} risk case near {village['name']}."
        update_report_status(report_id, status, note)
        _set_created_at(report_id, datetime.utcnow() - timedelta(days=random.randint(0, 20)))
        created += 1

    for idx in range(1, max(8, count // 4) + 1):
        village = random.choice(VILLAGES)
        insert_trap_observation(
            farm_id=f"SIM-FARM-{random.randint(1, count):03d}",
            pest_name=random.choice(["Whitefly", "Fruit borer", "Aphid", "Leaf miner"]),
            count=random.randint(3, 45),
            trap_type=random.choice(["Yellow sticky trap", "Pheromone trap", "Light trap"]),
            observed_at=(datetime.utcnow() - timedelta(days=random.randint(0, 12))).date().isoformat(),
            lat=_jitter(village["lat"]),
            lon=_jitter(village["lon"]),
            district=village["district"],
        )

    print(f"Seeded {created} simulated crop-health reports.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--seed", type=int, default=26131)
    args = parser.parse_args()
    seed_reports(count=args.count, reset=args.reset, seed=args.seed)


if __name__ == "__main__":
    main()
