from __future__ import annotations

from app.domain.enums import Decision
from app.domain.models import ChangeRequest


def test_seed_creates_lab_users_without_plaintext(session_runtime):
    session, runtime = session_runtime
    from sqlalchemy import select

    from app.persistence.orm import UserRow

    users = session.scalars(select(UserRow)).all()
    assert {u.username for u in users} >= {"engineer-a", "admin"}
    assert all(not u.password_hash.startswith("lab-") for u in users)
    assert all("$" in u.password_hash or u.password_hash.startswith("$2") for u in users)


def test_end_to_end_allow_then_state_block_then_ramp(session_runtime):
    session, runtime = session_runtime
    runtime.plant.transition("IDLE")

    allow = runtime.evaluate(
        session,
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
    assert allow.decision == Decision.ALLOW
    session.commit()

    blocked = runtime.evaluate(
        session,
        ChangeRequest(
            plc_id="tank-plc-01",
            parameter="TankLevel_SP",
            previous_value=60,
            requested_value=95,
            source_identity="unknown",
            source_host="attacker-pc",
            current_process_state="IDLE",
        ),
        authenticated=False,
    )
    assert blocked.decision == Decision.BLOCK
    assert blocked.hard_violation is True
    assert any("IDLE" in r or "Unauthorized" in r or "workstation" in r for r in blocked.reasons)
    session.commit()

    # Slow ramp from the allowed 60
    runtime.plant.tank_level_sp = 60
    values = [63, 66, 69, 72]
    last = None
    prev = 60
    for value in values:
        last = runtime.evaluate(
            session,
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
        session.commit()
        prev = value
    assert last is not None
    assert last.decision in {Decision.BLOCK, Decision.HOLD}
    assert last.checks["temporal_validation"].value == "FAIL"


def test_fail_closed_on_engine_error(session_runtime):
    session, runtime = session_runtime
    runtime.settings.fail_safe_mode = "fail_closed"

    def boom(*_a, **_k):
        raise RuntimeError("state model unavailable")

    runtime.build_context = boom  # type: ignore[method-assign]
    result = runtime.evaluate(
        session,
        ChangeRequest(plc_id="tank-plc-01", parameter="TankLevel_SP", requested_value=55),
        authenticated=True,
        persist=False,
    )
    assert result.decision == Decision.BLOCK
    assert any("fail-safe" in r.lower() for r in result.reasons)


def test_enforcement_requires_lab_mode(session_runtime):
    session, runtime = session_runtime
    runtime.settings.operating_mode = "enforcement"
    runtime.settings.lab_mode = False
    assert runtime.settings.enforcement_enabled is False
    runtime.evaluate(
        session,
        ChangeRequest(
            plc_id="tank-plc-01",
            parameter="TankLevel_SP",
            previous_value=50,
            requested_value=95,
            source_identity="attacker",
            source_host="bad",
            current_process_state="IDLE",
        ),
        authenticated=False,
    )
    # Without lab mode, interceptor must not act as a silent PEP-only block of physics
    # but the decision is still BLOCK. Advisory apply still happens.
    assert runtime.plant.tank_level_sp == 95


def test_lab_enforcement_blocks_apply(session_runtime):
    session, runtime = session_runtime
    runtime.settings.operating_mode = "enforcement"
    runtime.settings.lab_mode = True
    runtime.plant.tank_level_sp = 50
    runtime.evaluate(
        session,
        ChangeRequest(
            plc_id="tank-plc-01",
            parameter="TankLevel_SP",
            previous_value=50,
            requested_value=95,
            source_identity="attacker",
            source_host="bad",
            current_process_state="IDLE",
        ),
        authenticated=False,
    )
    assert runtime.settings.enforcement_enabled is True
    assert runtime.plant.tank_level_sp == 50
