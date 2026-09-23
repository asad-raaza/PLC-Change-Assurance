"""Named scenarios for the research matrix. Ground truth stays in the harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from app.domain.models import ApprovedChange, ChangeRequest, utcnow
from tests.helpers import approval, context, snapshot


@dataclass
class Scenario:
    name: str
    family: str
    attack_type: str
    label: str  # benign | attack
    privilege: str
    speed: str
    build: callable
    expected_full: str
    notes: str = ""


def _ctx_allow():
    return context()


def _ctx_unknown_host():
    return context(source_host="unknown-workstation", change_ticket=None, approvals=[])


def _ctx_unauthorized_identity():
    return context(source_identity="intruder", source_host="unknown-workstation", change_ticket=None, approvals=[])


def _ctx_expired():
    return context(approvals=[approval(valid_until=utcnow() - timedelta(minutes=10))])


def _ctx_wrong_plc():
    return context(approvals=[approval(plc_id="other-plc")])


def _ctx_wrong_parameter():
    return context(parameter="Temperature_SP", requested_value=40, previous_value=40)


def _ctx_out_of_range():
    return context(requested_value=250, change_ticket=None, approvals=[])


def _ctx_wrong_state():
    return context(requested_value=95, current_process_state="IDLE", change_ticket=None, approvals=[])


def _ctx_combo():
    snap = snapshot(parameters={"PumpSpeed": 10, "InletValve": 10, "pump-plc-01.PumpSpeed": 10, "valve-plc-01.InletValve": 10})
    return context(
        plc_id="pump-plc-01",
        parameter="PumpSpeed",
        previous_value=10,
        requested_value=90,
        change_ticket=None,
        approvals=[],
        snapshot=snap,
    )


def _ctx_ramp():
    now = utcnow()
    recent = [
        ChangeRequest(parameter="TankLevel_SP", previous_value=60, requested_value=63, plc_id="tank-plc-01", timestamp=now - timedelta(seconds=12)),
        ChangeRequest(parameter="TankLevel_SP", previous_value=63, requested_value=66, plc_id="tank-plc-01", timestamp=now - timedelta(seconds=8)),
        ChangeRequest(parameter="TankLevel_SP", previous_value=66, requested_value=69, plc_id="tank-plc-01", timestamp=now - timedelta(seconds=4)),
    ]
    return context(previous_value=69, requested_value=72, change_ticket=None, approvals=[], recent_changes=recent)


def _ctx_invalid_transition():
    return context(
        parameter="OperatingMode",
        previous_value="IDLE",
        requested_value="PROCESSING",
        current_process_state="IDLE",
        change_ticket=None,
        approvals=[],
    )


def _ctx_replay():
    return context(approvals=[approval(consumed=True)])


def _ctx_maintenance():
    now = utcnow()
    apr = approval(
        change_ticket="CHG-M-9",
        allowed_old_value=50,
        allowed_new_value=55,
        allowed_process_states=["MAINTENANCE"],
        object="TankLevel_SP",
    )
    return context(
        requested_value=55,
        current_process_state="MAINTENANCE",
        change_ticket="CHG-M-9",
        approvals=[apr],
    )


def _ctx_operator_adjust():
    return context(
        parameter="OutletValve",
        plc_id="valve-plc-01",
        previous_value=10,
        requested_value=15,
        source_identity="operator-1",
        source_host="operator-panel-1",
        change_ticket=None,
        approvals=[],
    )


def _ctx_cross_plc():
    snap = snapshot(
        parameters={
            "PumpSpeed": 10,
            "InletValve": 0,
            "pump-plc-01.PumpSpeed": 10,
            "valve-plc-01.InletValve": 0,
        }
    )
    return context(
        plc_id="pump-plc-01",
        parameter="PumpSpeed",
        previous_value=10,
        requested_value=90,
        change_ticket=None,
        approvals=[],
        snapshot=snap,
    )


def _ctx_no_approval_valid_state():
    return context(requested_value=55, change_ticket=None, approvals=[])


def _ctx_temp_pressure():
    snap = snapshot(parameters={"Temperature_SP": 80, "Pressure": 75, "Heater": 1})
    return context(
        parameter="Temperature_SP",
        previous_value=80,
        requested_value=96,
        current_process_state="HEATING",
        change_ticket=None,
        approvals=[],
        snapshot=snap,
    )


SCENARIOS: list[Scenario] = [
    Scenario("authorized_setpoint", "normal", "none", "benign", "engineer", "normal", _ctx_allow, "ALLOW"),
    Scenario("approved_maintenance", "normal", "none", "benign", "engineer", "normal", _ctx_maintenance, "ALLOW"),
    Scenario("operator_adjustment", "normal", "none", "benign", "operator", "normal", _ctx_operator_adjust, "ALLOW"),
    Scenario("unknown_workstation", "unauthorized", "unknown_host", "attack", "none", "normal", _ctx_unknown_host, "BLOCK"),
    Scenario("unauthorized_identity", "unauthorized", "unknown_identity", "attack", "none", "normal", _ctx_unauthorized_identity, "BLOCK"),
    Scenario("expired_approval", "unauthorized", "expired_approval", "attack", "engineer", "normal", _ctx_expired, "HOLD"),
    Scenario("wrong_plc_approval", "unauthorized", "wrong_plc", "attack", "engineer", "normal", _ctx_wrong_plc, "REQUIRE_APPROVAL"),
    Scenario("wrong_parameter", "unauthorized", "wrong_parameter", "attack", "engineer", "normal", _ctx_wrong_parameter, "REQUIRE_APPROVAL"),
    Scenario("out_of_range", "safety", "out_of_range", "attack", "engineer", "normal", _ctx_out_of_range, "BLOCK"),
    Scenario("wrong_state", "safety", "wrong_state", "attack", "engineer", "normal", _ctx_wrong_state, "BLOCK"),
    Scenario("unsafe_combination", "safety", "unsafe_combination", "attack", "engineer", "normal", _ctx_combo, "BLOCK"),
    Scenario("slow_ramp", "stealth", "slow_ramp", "attack", "engineer", "slow", _ctx_ramp, "BLOCK"),
    Scenario("invalid_transition", "safety", "invalid_transition", "attack", "engineer", "normal", _ctx_invalid_transition, "BLOCK"),
    Scenario("replay", "stealth", "replay", "attack", "engineer", "normal", _ctx_replay, "BLOCK"),
    Scenario("cross_plc_conflict", "multi_plc", "cross_plc", "attack", "engineer", "normal", _ctx_cross_plc, "BLOCK"),
    Scenario("compromised_host_no_ticket", "compromised_trusted_host", "missing_intent", "attack", "engineer", "normal", _ctx_no_approval_valid_state, "REQUIRE_APPROVAL"),
    Scenario("temp_and_pressure", "multi_variable", "temp_pressure", "attack", "engineer", "normal", _ctx_temp_pressure, "BLOCK"),
]
