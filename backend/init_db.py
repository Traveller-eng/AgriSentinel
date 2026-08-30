"""Create the AgriSentinel SQLite database and tables."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Base, DB_PATH, engine


def init_db() -> None:
    """Create agrisentinel.db and all ORM tables if they do not already exist.

    Safe to call multiple times: SQLAlchemy ``create_all()`` is idempotent and
    will not drop or alter existing tables.

    Returns:
        None
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
