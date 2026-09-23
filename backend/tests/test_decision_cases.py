"""Section 38 cases: reasons are asserted, not only decision codes."""

from __future__ import annotations

from datetime import timedelta

from hypothesis import given
from hypothesis import strategies as st

from app.catalog import DEFAULT_CATALOG
from app.domain.enums import Decision
from app.domain.models import ChangeRequest, utcnow
from app.engines.baselines import compare_all
from app.engines.decision import evaluate_change
from tests.helpers import approval, context, snapshot


def test_authorized_legitimate_change_allow():
    result = evaluate_change(context(), DEFAULT_CATALOG)
    assert result.decision == Decision.ALLOW
    assert result.hard_violation is False
    assert result.checks["authorization"].value == "PASS"
    assert result.checks["change_provenance"].value == "PASS"
    assert result.checks["state_validation"].value == "PASS"


def test_unauthorized_source_blocks():
    result = evaluate_change(context(source_identity="unknown-attacker", source_host="laptop-7"), DEFAULT_CATALOG)
    assert result.decision in {Decision.HOLD, Decision.BLOCK}
    assert any("Unauthorized identity" in r or "not an authorized" in r for r in result.reasons)


def test_unknown_workstation_blocks():
    result = evaluate_change(context(source_host="rogue-laptop"), DEFAULT_CATALOG)
    assert result.decision == Decision.BLOCK
    assert any("workstation" in r.lower() for r in result.reasons)


def test_valid_value_wrong_state_blocks():
    result = evaluate_change(
        context(requested_value=95, current_process_state="IDLE", change_ticket=None, approvals=[]),
        DEFAULT_CATALOG,
    )
    assert result.decision == Decision.BLOCK
    assert result.hard_violation is True
    assert any("not permitted in IDLE" in r for r in result.reasons)
    # Globally valid — static baseline must miss this.
    algos = compare_all(context(requested_value=95, current_process_state="IDLE", change_ticket=None, approvals=[]), DEFAULT_CATALOG)
    assert algos["static_range"] == Decision.ALLOW
    assert algos["fsm"] == Decision.BLOCK


def test_unsafe_combination_blocks():
    snap = snapshot(parameters={"PumpSpeed": 20, "InletValve": 10, "pump-plc-01.PumpSpeed": 20, "valve-plc-01.InletValve": 10})
    result = evaluate_change(
        context(
            plc_id="pump-plc-01",
            parameter="PumpSpeed",
            previous_value=20,
            requested_value=90,
            change_ticket=None,
            approvals=[],
            snapshot=snap,
        ),
        DEFAULT_CATALOG,
    )
    assert result.decision == Decision.BLOCK
    assert any("InletValve" in r for r in result.reasons)


def test_slow_ramp_exceeding_temporal_rule_blocks():
    now = utcnow()
    recent = []
    value = 60.0
    for step in (63, 66, 69):
        recent.append(
            ChangeRequest(
                parameter="TankLevel_SP",
                previous_value=value,
                requested_value=step,
                plc_id="tank-plc-01",
                timestamp=now - timedelta(seconds=20 - len(recent)),
            )
        )
        value = float(step)
    ctx = context(
        previous_value=69,
        requested_value=72,
        change_ticket=None,
        approvals=[],
        recent_changes=recent,
    )
    result = evaluate_change(ctx, DEFAULT_CATALOG)
    assert result.decision == Decision.BLOCK
    assert any("10 units" in r or "30 seconds" in r for r in result.reasons)
    algos = compare_all(ctx, DEFAULT_CATALOG)
    assert algos["static_range"] == Decision.ALLOW
    assert algos["fsm"] == Decision.ALLOW
    assert algos["fsm_temporal"] == Decision.BLOCK


def test_expired_approval_hold():
    expired = approval(valid_until=utcnow() - timedelta(minutes=5))
    result = evaluate_change(context(approvals=[expired]), DEFAULT_CATALOG)
    assert result.decision in {Decision.HOLD, Decision.BLOCK}
    assert any("expired" in r.lower() for r in result.reasons)


def test_replayed_approval_blocks():
    used = approval(consumed=True, consumed_by_request="req-old")
    result = evaluate_change(context(approvals=[used]), DEFAULT_CATALOG)
    assert result.decision == Decision.BLOCK
    assert any("consumed" in r.lower() or "replay" in r.lower() for r in result.reasons)


def test_safe_state_transition_allow():
    result = evaluate_change(
        context(
            parameter="OperatingMode",
            previous_value="IDLE",
            requested_value="FILLING",
            current_process_state="IDLE",
            change_ticket=None,
            approvals=[],
            snapshot=snapshot(parameters={"InletValve": 40, "TankLevel": 50}),
        ),
        DEFAULT_CATALOG,
    )
    assert result.decision in {Decision.ALLOW, Decision.ALLOW_WITH_ALERT, Decision.REQUIRE_APPROVAL}
    assert result.checks["transition_validation"].value == "PASS"


def test_invalid_transition_blocks():
    result = evaluate_change(
        context(
            parameter="OperatingMode",
            previous_value="IDLE",
            requested_value="PROCESSING",
            current_process_state="IDLE",
            change_ticket=None,
            approvals=[],
        ),
        DEFAULT_CATALOG,
    )
    assert result.decision == Decision.BLOCK
    assert any("Invalid process transition" in r for r in result.reasons)


def test_hard_violation_not_overridden_by_low_score():
    result = evaluate_change(
        context(requested_value=95, current_process_state="IDLE", change_ticket=None, approvals=[]),
        DEFAULT_CATALOG,
    )
    assert result.hard_violation is True
    assert result.decision != Decision.ALLOW
    assert result.risk_score >= 0


@given(st.floats(min_value=0, max_value=70))
def test_idle_level_setpoint_within_state_bounds_not_hard_blocked(value: float):
    if value < 20:
        return
    result = evaluate_change(
        context(requested_value=round(value, 2), change_ticket=None, approvals=[]),
        DEFAULT_CATALOG,
    )
    assert result.checks["state_validation"].value != "FAIL"
    if result.hard_violation:
        assert result.decision != Decision.ALLOW


def test_cross_plc_conflict_blocks():
    snap = snapshot(
        parameters={
            "PumpSpeed": 20,
            "InletValve": 0,
            "pump-plc-01.PumpSpeed": 20,
            "valve-plc-01.InletValve": 0,
        }
    )
    result = evaluate_change(
        context(
            plc_id="pump-plc-01",
            parameter="PumpSpeed",
            previous_value=20,
            requested_value=90,
            change_ticket=None,
            approvals=[],
            snapshot=snap,
        ),
        DEFAULT_CATALOG,
    )
    assert result.decision == Decision.BLOCK
    assert any("globally unsafe" in r or "InletValve" in r for r in result.reasons)


def test_compromised_host_valid_user_invalid_operation():
    result = evaluate_change(
        context(requested_value=55, change_ticket=None, approvals=[]),
        DEFAULT_CATALOG,
    )
    assert result.decision == Decision.REQUIRE_APPROVAL
    assert any("No approved change" in r for r in result.reasons)
    algos = compare_all(context(requested_value=55, change_ticket=None, approvals=[]), DEFAULT_CATALOG)
    assert algos["static_range"] == Decision.ALLOW
    assert algos["full_framework"] == Decision.REQUIRE_APPROVAL
