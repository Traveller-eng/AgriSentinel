"""SQLAlchemy ORM models and shared database session helpers for AgriSentinel."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DISEASE_CLASSES = [
    "Bacterial Spot",
    "Early Blight",
    "Late Blight",
    "Yellow Leaf Curl Virus",
    "Healthy",
]

GROWTH_STAGES = [
    "Seedling",
    "Vegetative",
    "Flowering",
    "Fruiting",
    "Maturity",
]

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, os.pardir))
DB_PATH = os.path.join(PROJECT_ROOT, "agrisentinel.db")

Base = declarative_base()

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a fresh SQLAlchemy session and close it after the call.

    Yields:
        Session: A new session bound to the SQLite engine.

    Raises:
        Exception: Re-raises after rollback if the caller leaves an error uncaught.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class Report(Base):
    """A farmer-submitted crop-health report."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farm_id = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    crop = Column(String, nullable=False, default="Tomato")
    growth_stage = Column(String, nullable=False)
    predicted_disease = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    gradcam_path = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    district = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expert_notes = Column(String, nullable=True)


class TrapObservation(Base):
    """A pest trap count recorded in the field."""

    __tablename__ = "trap_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farm_id = Column(String, nullable=False)
    pest_name = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    trap_type = Column(String, nullable=False)
    observed_at = Column(Date, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    district = Column(String, nullable=False)


class WeatherCache(Base):
    """One cached weather snapshot per district per calendar date."""

    __tablename__ = "weather_cache"
    __table_args__ = (
        UniqueConstraint("district", "date", name="uq_weather_district_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    district = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    temp = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rainfall_mm = Column(Float, nullable=True)  # stores 3-day sum (API name: rainfall_3day_mm)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
