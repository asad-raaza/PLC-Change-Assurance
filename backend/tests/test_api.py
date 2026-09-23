from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import db_session, runtime_dep
from app.main import app
from app.persistence.orm import Base
from app.services.runtime import AssuranceRuntime


def test_health_and_login_and_evaluate():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True)
    runtime = AssuranceRuntime()
    session = factory()
    runtime.seed(session)
    session.commit()
    session.close()

    def _db():
        db = factory()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app.dependency_overrides[db_session] = _db
    app.dependency_overrides[runtime_dep] = lambda: runtime
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    token = client.post(
        "/api/auth/login",
        data={"username": "engineer-a", "password": "lab-engineer-change-me"},
    )
    assert token.status_code == 200
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    allowed = client.post(
        "/api/change-requests",
        headers=headers,
        json={
            "plc_id": "tank-plc-01",
            "parameter": "TankLevel_SP",
            "requested_value": 60,
            "previous_value": 50,
            "source_host": "eng-ws-02",
            "change_ticket": "CHG-1234",
        },
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["decision"] == "ALLOW"
    assert body["hard_violation"] is False
    blocked = client.post(
        "/api/change-requests",
        headers=headers,
        json={
            "plc_id": "tank-plc-01",
            "parameter": "TankLevel_SP",
            "requested_value": 95,
            "previous_value": 60,
            "source_identity": "attacker",
            "source_host": "rogue",
        },
    )
    assert blocked.json()["decision"] == "BLOCK"
    assert blocked.json()["reasons"]
    app.dependency_overrides.clear()
    engine.dispose()
