"""Seed the demo plant, users, policy, and CHG-1234 approval."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.persistence.database import get_engine, get_session_factory  # noqa: E402
from app.persistence.orm import Base  # noqa: E402
from app.services.runtime import get_runtime  # noqa: E402


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    db = get_session_factory()()
    get_runtime().seed(db)
    db.commit()
    db.close()
    print("Seeded lab environment")


if __name__ == "__main__":
    main()
