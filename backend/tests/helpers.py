from __future__ import annotations

from datetime import timedelta

from app.catalog import DEFAULT_CATALOG
from app.domain.models import ApprovedChange, ChangeRequest, EvaluationContext, ProcessSnapshot, utcnow


def approval(**kwargs) -> ApprovedChange:
    now = utcnow()
    defaults = dict(
        change_ticket="CHG-1234",
        requester="engineer-a",
        approvers=["supervisor-b"],
        plc_id="tank-plc-01",
        object="TankLevel_SP",
        allowed_old_value=50,
        allowed_new_value=60,
        valid_from=now - timedelta(hours=1),
        valid_until=now + timedelta(days=1),
        allowed_process_states=["IDLE", "MAINTENANCE"],
        allowed_hosts=["eng-ws-02"],
        allowed_identities=["engineer-a"],
        reason="production recipe update",
    )
    defaults.update(kwargs)
    return ApprovedChange(**defaults)


def snapshot(**kwargs) -> ProcessSnapshot:
    params = {
        "TankLevel_SP": 50,
        "Temperature_SP": 40,
        "PumpSpeed": 20,
        "InletValve": 50,
        "OutletValve": 10,
        "Heater": 0,
        "Pressure": 25,
        "pump-plc-01.PumpSpeed": 20,
        "valve-plc-01.InletValve": 50,
        "AlarmHighLevel": 90,
    }
    params.update(kwargs.get("parameters", {}))
    return ProcessSnapshot(
        plc_states={"tank-plc-01": kwargs.get("state", "IDLE"), "pump-plc-01": "IDLE", "valve-plc-01": "IDLE"},
        parameters=params,
        sensors={"TankLevel": 50.0, "Temperature": 35.0, "Pressure": 25.0, "Flow": 0.0},
        actuators={"Pump-1": params["PumpSpeed"], "Valve-1": params["InletValve"]},
        last_trusted_parameters=dict(params),
        last_trusted_at=utcnow(),
    )


def context(**kwargs) -> EvaluationContext:
    req_kwargs = {
        "plc_id": kwargs.pop("plc_id", "tank-plc-01"),
        "parameter": kwargs.pop("parameter", "TankLevel_SP"),
        "previous_value": kwargs.pop("previous_value", 50),
        "requested_value": kwargs.pop("requested_value", 60),
        "source_identity": kwargs.pop("source_identity", "engineer-a"),
        "source_host": kwargs.pop("source_host", "eng-ws-02"),
        "current_process_state": kwargs.pop("current_process_state", "IDLE"),
        "change_ticket": kwargs.pop("change_ticket", "CHG-1234"),
        "change_class": kwargs.pop("change_class", "setpoint_change"),
        "already_applied": kwargs.pop("already_applied", False),
    }
    request = ChangeRequest(**req_kwargs)
    approvals = kwargs.pop("approvals", [approval()])
    recent = kwargs.pop("recent_changes", [])
    return EvaluationContext(
        request=request,
        snapshot=kwargs.pop("snapshot", snapshot()),
        recent_changes=recent,
        approvals=approvals,
        authorized_identities=set(DEFAULT_CATALOG.authorized_identities),
        authorized_hosts=set(DEFAULT_CATALOG.authorized_hosts),
        authorized_roles=dict(DEFAULT_CATALOG.authorized_identities),
        authenticated=kwargs.pop("authenticated", True),
        auth_confidence=0.95,
        asset_criticality={"tank-plc-01": 5, "pump-plc-01": 4, "valve-plc-01": 4},
    )
