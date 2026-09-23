from __future__ import annotations

from app.adapters.modbus import ModbusTCPAdapter
from app.catalog import DEFAULT_CATALOG
from app.domain.enums import Decision
from app.domain.models import ChangeRequest
from app.engines.decision import evaluate_change
from app.engines.recovery import SafeRecoveryEngine
from app.policies.parser import DEMO_POLICY_YAML, PolicyValidationError, parse_policy_yaml
from tests.helpers import context, snapshot


def test_modbus_pdu_becomes_canonical_change():
    adapter = ModbusTCPAdapter()
    # FC6 write register 0 (TankLevel_SP) value 60
    pdu = bytes([6, 0, 0, 0, 60])
    change = adapter.to_change_request(pdu)
    assert change.parameter == "TankLevel_SP"
    assert change.plc_id == "tank-plc-01"
    assert change.requested_value == 60
    assert change.protocol == "modbus_tcp"


def test_policy_must_validate_before_use():
    doc, digest = parse_policy_yaml(DEMO_POLICY_YAML)
    assert doc.policy.name == "heating-safety"
    assert len(digest) == 64
    try:
        parse_policy_yaml("not: valid: policy")
        raise AssertionError("should have failed")
    except PolicyValidationError:
        pass


def test_recovery_does_not_treat_out_of_envelope_previous_as_safe():
    engine = SafeRecoveryEngine(DEFAULT_CATALOG)
    ctx = context(
        parameter="TankLevel_SP",
        previous_value=95,
        requested_value=96,
        current_process_state="IDLE",
        already_applied=True,
        snapshot=snapshot(parameters={"TankLevel_SP": 96}),
    )
    rec = engine.evaluate(ctx)
    assert rec.automatic_allowed is False
    assert rec.requires_operator is True
    assert "not a safe rollback target" in " ".join(rec.rationale)
    assert rec.action != "restore_previous_if_confirmed" or 95 not in rec.target_values.values()


def test_logic_change_fails_provenance():
    from app.domain.enums import ChangeClass

    result = evaluate_change(
        context(
            parameter="__logic__",
            requested_value="online_edit",
            change_class=ChangeClass.LOGIC_CHANGE,
            change_ticket=None,
            approvals=[],
        ),
        DEFAULT_CATALOG,
    )
    assert result.decision == Decision.BLOCK
    assert any("Logic changes" in r for r in result.reasons)


def test_out_of_range_static_baseline_detects():
    from app.engines.baselines import compare_all

    ctx = context(requested_value=250, change_ticket=None, approvals=[])
    algos = compare_all(ctx, DEFAULT_CATALOG)
    assert algos["static_range"] == Decision.BLOCK
    assert algos["full_framework"] == Decision.BLOCK
