from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.persistence.orm import Base  # noqa: E402
from app.services.runtime import AssuranceRuntime  # noqa: E402


@pytest.fixture
def session_runtime():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True)
    session = factory()
    runtime = AssuranceRuntime()
    runtime.settings.operating_mode = "advisory"
    runtime.settings.lab_mode = False
    runtime.seed(session)
    session.commit()
    yield session, runtime
    session.close()
    engine.dispose()
