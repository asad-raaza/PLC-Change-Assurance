"""Section 53 demonstration: ALLOW, state BLOCK, slow-ramp HOLD/BLOCK, combination BLOCK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.domain.models import ChangeRequest  # noqa: E402
from app.persistence.orm import Base  # noqa: E402
from app.services.runtime import AssuranceRuntime  # noqa: E402


def show(title: str, result) -> None:
    print(f"\n=== {title} ===")
    print(result.decision.value, "risk", result.risk_score, "hard", result.hard_violation)
    for reason in result.reasons:
        print(" -", reason)


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, future=True)()
    runtime = AssuranceRuntime()
    runtime.settings.operating_mode = "advisory"
    runtime.seed(db)
    runtime.plant.transition("IDLE")

    allow = runtime.evaluate(
        db,
        ChangeRequest(
            plc_id="tank-plc-01",
            parameter="TankLevel_SP",
            previous_value=50,
            requested_value=60,
            source_identity="engineer-a",
            source_host="eng-ws-02",
            current_process_state="IDLE",
            change_ticket="CHG-1234",
        ),
        authenticated=True,
    )
    show("Legitimate 50 -> 60", allow)
    db.commit()

    blocked = runtime.evaluate(
        db,
        ChangeRequest(
            plc_id="tank-plc-01",
            parameter="TankLevel_SP",
            previous_value=60,
            requested_value=95,
            source_identity="attacker",
            source_host="unknown-ws",
            current_process_state="IDLE",
        ),
        authenticated=False,
    )
    show("Attack 60 -> 95", blocked)
    db.commit()

    prev = 60
    last = None
    for value in (63, 66, 69, 72):
        last = runtime.evaluate(
            db,
            ChangeRequest(
                plc_id="tank-plc-01",
                parameter="TankLevel_SP",
                previous_value=prev,
                requested_value=value,
                source_identity="engineer-a",
                source_host="eng-ws-02",
                current_process_state="IDLE",
            ),
            authenticated=True,
        )
        db.commit()
        prev = value
    show("Slow ramp ending 72", last)

    combo = runtime.evaluate(
        db,
        ChangeRequest(
            plc_id="pump-plc-01",
            parameter="PumpSpeed",
            previous_value=20,
            requested_value=90,
            source_identity="engineer-a",
            source_host="eng-ws-02",
            current_process_state="IDLE",
        ),
        authenticated=True,
    )
    show("Pump high while valve low", combo)
    print("\nMetrics:", json.dumps(runtime.metrics.snapshot(), indent=2))
    db.close()


if __name__ == "__main__":
    main()
