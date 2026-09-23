"""REST surface for operators, auditors, and researchers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.modbus import ModbusTCPAdapter
from app.adapters.twin import WaterTankTwinAdapter
from app.api.deps import current_user, db_session, require, runtime_dep
from app.domain.enums import CapabilityStatus, ChangeClass
from app.domain.models import ApprovedChange, ChangeRequest, LogicChangeEvent, new_id, utcnow
from app.persistence.orm import (
    ApprovedChangeRow,
    AuditEventRow,
    ChangeRequestRow,
    DecisionResultRow,
    IncidentRow,
    PlcRow,
    PolicyRow,
    RecoveryActionRow,
    StateModelRow,
    UserRow,
)
from app.policies.parser import PolicyValidationError, parse_policy_yaml
from app.security.auth import create_token, verify_password
from app.services.runtime import AssuranceRuntime

router = APIRouter()
modbus = ModbusTCPAdapter()
twin = WaterTankTwinAdapter()


class ChangeIn(BaseModel):
    plc_id: str
    parameter: str
    requested_value: float | int | str | bool
    previous_value: float | int | str | bool | None = None
    source_identity: str | None = None
    source_host: str = "eng-ws-02"
    source_ip: str = "10.0.10.20"
    protocol: str = "modbus_tcp"
    change_ticket: str | None = None
    approved_change_id: str | None = None
    session_id: str | None = None
    current_process_state: str | None = None
    requested_operation: str = "write_register"
    change_class: ChangeClass = ChangeClass.SETPOINT_CHANGE
    maintenance_window: bool = False
    already_applied: bool = False
    metadata: dict = Field(default_factory=dict)


class ApprovalIn(BaseModel):
    change_ticket: str
    requester: str
    approvers: list[str] = Field(default_factory=list)
    plc_id: str
    object: str
    allowed_old_value: float | int | str | bool | None = None
    allowed_new_value: float | int | str | bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    allowed_process_states: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_identities: list[str] = Field(default_factory=list)
    reason: str = ""


class PolicyIn(BaseModel):
    yaml_text: str


class StateModelIn(BaseModel):
    name: str
    version: str = "1.0.0"
    definition: dict


class SimulateIn(BaseModel):
    plc_id: str
    parameter: str
    requested_value: float
    horizon: float = 8.0


class RecoveryIn(BaseModel):
    request_id: str | None = None
    plc_id: str
    parameter: str
    requested_value: float | int | str | bool | None = None
    previous_value: float | int | str | bool | None = None
    already_applied: bool = True


class ModbusWriteIn(BaseModel):
    function_code: int = 6
    address: int
    value: float | int
    source_identity: str = "unknown"
    source_host: str = "unknown"
    source_ip: str = ""
    change_ticket: str | None = None


def _to_request(body: ChangeIn, user: dict, runtime: AssuranceRuntime) -> ChangeRequest:
    return ChangeRequest(
        plc_id=body.plc_id,
        parameter=body.parameter,
        requested_value=body.requested_value,
        previous_value=body.previous_value,
        source_identity=body.source_identity or user["username"],
        source_host=body.source_host,
        source_ip=body.source_ip,
        protocol=body.protocol,
        change_ticket=body.change_ticket,
        approved_change_id=body.approved_change_id,
        session_id=body.session_id,
        current_process_state=body.current_process_state or runtime.plant.state,
        requested_operation=body.requested_operation,
        change_class=body.change_class,
        maintenance_window=body.maintenance_window,
        already_applied=body.already_applied,
        metadata=body.metadata,
        authentication_context={"username": user["username"], "role": user["role"]},
    )


@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(db_session)):
    user = db.scalar(select(UserRow).where(UserRow.username == form.username))
    if not user or user.disabled or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.username, user.role)
    return {"access_token": token, "token_type": "bearer", "username": user.username, "role": user.role}


@router.get("/overview")
def overview(
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    _user: dict = Depends(require("change:read")),
):
    snap = runtime.snapshot()
    decisions = db.execute(
        select(DecisionResultRow.decision, func.count()).group_by(DecisionResultRow.decision)
    ).all()
    counts = {row[0]: row[1] for row in decisions}
    incidents = db.scalar(select(func.count()).select_from(IncidentRow)) or 0
    plc_count = db.scalar(select(func.count()).select_from(PlcRow)) or 0
    recent = db.scalars(select(DecisionResultRow).order_by(DecisionResultRow.id.desc()).limit(8)).all()
    return {
        "plc_count": plc_count,
        "active_process_states": snap.plc_states,
        "sensors": snap.sensors,
        "parameters": {
            k: v
            for k, v in snap.parameters.items()
            if "." not in k
        },
        "blocked_changes": counts.get("BLOCK", 0),
        "held_changes": counts.get("HOLD", 0),
        "allowed_changes": counts.get("ALLOW", 0) + counts.get("ALLOW_WITH_ALERT", 0),
        "active_incidents": incidents,
        "policy_status": "active",
        "operating_mode": runtime.settings.operating_mode,
        "lab_mode": runtime.settings.lab_mode,
        "enforcement_enabled": runtime.settings.enforcement_enabled,
        "recent_changes": [row.payload for row in recent],
        "high_risk_assets": [
            {"plc_id": plc["plc_id"], "criticality": plc["criticality"]}
            for plc in runtime.catalog.plcs
            if plc["criticality"] >= 4
        ],
    }


@router.post("/change-requests/evaluate")
def evaluate_only(
    body: ChangeIn,
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    user: dict = Depends(require("change:write")),
):
    request = _to_request(body, user, runtime)
    # Evaluate without applying: temporarily force a dry run via persist and skip apply
    # by using evaluate() then we still apply per mode — for evaluate-only we persist
    # the request but callers that want a dry run set metadata.dry_run.
    if body.metadata.get("dry_run"):
        context = runtime.build_context(db, request, authenticated=True)
        from app.engines.decision import evaluate_change
        from app.engines.baselines import compare_all

        result = evaluate_change(context, runtime.catalog, runtime.settings.risk_policy_mode)
        result.algorithm_results = compare_all(context, runtime.catalog)
        return result.model_dump(mode="json")
    result = runtime.evaluate(db, request, authenticated=True)
    return result.model_dump(mode="json")


@router.post("/change-requests")
def submit_change(
    body: ChangeIn,
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    user: dict = Depends(require("change:write")),
):
    result = runtime.evaluate(db, _to_request(body, user, runtime), authenticated=True)
    return result.model_dump(mode="json")


@router.get("/change-requests")
def list_changes(
    db: Session = Depends(db_session),
    _user: dict = Depends(require("change:read")),
):
    rows = db.scalars(select(DecisionResultRow).order_by(DecisionResultRow.id.desc()).limit(200)).all()
    return [row.payload for row in rows]


@router.get("/change-requests/{request_id}")
def get_change(
    request_id: str,
    db: Session = Depends(db_session),
    _user: dict = Depends(require("change:read")),
):
    dec = db.scalar(select(DecisionResultRow).where(DecisionResultRow.request_id == request_id))
    req = db.scalar(select(ChangeRequestRow).where(ChangeRequestRow.request_id == request_id))
    if not dec or not req:
        raise HTTPException(status_code=404, detail="Unknown change request")
    return {"request": req.payload, "decision": dec.payload}


@router.post("/protocol/modbus/write")
def modbus_write(
    body: ModbusWriteIn,
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    user: dict = Depends(require("change:write")),
):
    request = modbus.to_change_request(body.model_dump())
    request.source_identity = body.source_identity or user["username"]
    request.current_process_state = runtime.plant.state
    request.previous_value = runtime.snapshot().parameters.get(request.parameter)
    request.change_ticket = body.change_ticket
    result = runtime.evaluate(db, request, authenticated=True)
    return {"request": request.model_dump(mode="json"), "decision": result.model_dump(mode="json")}


@router.get("/plcs")
def list_plcs(
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    _user: dict = Depends(require("change:read")),
):
    rows = db.scalars(select(PlcRow)).all()
    snap = runtime.snapshot()
    return [
        {
            "plc_id": row.plc_id,
            "vendor": row.vendor,
            "model": row.model,
            "ip": row.ip,
            "protocol": row.protocol,
            "criticality": row.criticality,
            "state": snap.plc_states.get(row.plc_id),
        }
        for row in rows
    ]


@router.get("/plcs/{plc_id}")
def get_plc(
    plc_id: str,
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    _user: dict = Depends(require("change:read")),
):
    row = db.scalar(select(PlcRow).where(PlcRow.plc_id == plc_id))
    if not row:
        raise HTTPException(status_code=404, detail="Unknown PLC")
    snap = runtime.snapshot()
    recent = db.scalars(select(DecisionResultRow).order_by(DecisionResultRow.id.desc()).limit(20)).all()
    return {
        "plc_id": row.plc_id,
        "vendor": row.vendor,
        "model": row.model,
        "firmware": row.firmware,
        "ip": row.ip,
        "protocol": row.protocol,
        "program_version": row.program_version,
        "operating_mode": row.operating_mode,
        "safety_classification": row.safety_classification,
        "criticality": row.criticality,
        "state": snap.plc_states.get(plc_id),
        "parameters": {k: v for k, v in snap.parameters.items() if k.startswith(plc_id) or "." not in k},
        "sensors": snap.sensors,
        "dependencies": [list(edge) for edge in runtime.catalog.graph_edges if plc_id in edge],
        "recent_changes": [r.payload for r in recent if r.payload.get("request_id")],
        "policy_coverage": True,
    }


@router.get("/plcs/{plc_id}/state")
def plc_state(plc_id: str, runtime: AssuranceRuntime = Depends(runtime_dep), _=Depends(require("change:read"))):
    return {
        "plc_id": plc_id,
        "state": runtime.plant.state,
        "plc_states": runtime.snapshot().plc_states,
        "model": runtime.catalog.state_model,
    }


@router.get("/plcs/{plc_id}/parameters")
def plc_parameters(plc_id: str, runtime: AssuranceRuntime = Depends(runtime_dep), _=Depends(require("change:read"))):
    snap = runtime.snapshot()
    return {k: v for k, v in snap.parameters.items() if k.startswith(plc_id) or "." not in k}


@router.get("/state-models")
def list_state_models(db: Session = Depends(db_session), _=Depends(require("policy:read"))):
    return [
        {"id": row.id, "name": row.name, "version": row.version, "definition": row.definition, "active": row.active}
        for row in db.scalars(select(StateModelRow)).all()
    ]


@router.post("/state-models")
def create_state_model(body: StateModelIn, db: Session = Depends(db_session), _=Depends(require("policy:write"))):
    row = StateModelRow(name=body.name, version=body.version, definition=body.definition)
    db.add(row)
    db.flush()
    return {"id": row.id, "name": row.name, "version": row.version}


@router.put("/state-models/{model_id}")
def update_state_model(
    model_id: int, body: StateModelIn, db: Session = Depends(db_session), _=Depends(require("policy:write"))
):
    row = db.get(StateModelRow, model_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown state model")
    row.name = body.name
    row.version = body.version
    row.definition = body.definition
    return {"id": row.id, "version": row.version}


@router.get("/policies")
def list_policies(db: Session = Depends(db_session), _=Depends(require("policy:read"))):
    return [
        {"id": row.id, "name": row.name, "version": row.version, "status": row.status, "hash": row.content_hash}
        for row in db.scalars(select(PolicyRow)).all()
    ]


@router.post("/policies")
def create_policy(body: PolicyIn, db: Session = Depends(db_session), _=Depends(require("policy:write"))):
    try:
        parsed, digest = parse_policy_yaml(body.yaml_text)
    except PolicyValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = PolicyRow(
        name=parsed.policy.name,
        version=parsed.policy.version,
        yaml_text=body.yaml_text,
        content_hash=digest,
        parsed=parsed.model_dump(),
    )
    db.add(row)
    db.flush()
    return {"id": row.id, "name": row.name, "hash": digest, "status": row.status}


@router.get("/change-approvals")
def list_approvals(db: Session = Depends(db_session), _=Depends(require("approval:read"))):
    rows = db.scalars(select(ApprovedChangeRow).order_by(ApprovedChangeRow.id.desc())).all()
    out = []
    for row in rows:
        item = dict(row.payload)
        item["consumed"] = row.consumed
        item["status"] = "consumed" if row.consumed else "active"
        until = item.get("valid_until")
        if until:
            ts = datetime.fromisoformat(until.replace("Z", "+00:00")) if isinstance(until, str) else until
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < utcnow() and not row.consumed:
                item["status"] = "expired"
        out.append(item)
    return out


@router.post("/change-approvals")
def create_approval(body: ApprovalIn, db: Session = Depends(db_session), _=Depends(require("approval:write"))):
    now = utcnow()
    approval = ApprovedChange(
        change_ticket=body.change_ticket,
        requester=body.requester,
        approvers=body.approvers,
        plc_id=body.plc_id,
        object=body.object,
        allowed_old_value=body.allowed_old_value,
        allowed_new_value=body.allowed_new_value,
        valid_from=body.valid_from or now,
        valid_until=body.valid_until or now + timedelta(hours=8),
        allowed_process_states=body.allowed_process_states,
        allowed_hosts=body.allowed_hosts,
        allowed_identities=body.allowed_identities or [body.requester],
        reason=body.reason,
    )
    db.add(
        ApprovedChangeRow(
            approval_id=approval.approval_id,
            change_ticket=approval.change_ticket,
            payload=approval.model_dump(mode="json"),
        )
    )
    db.flush()
    return approval.model_dump(mode="json")


@router.get("/incidents")
def list_incidents(db: Session = Depends(db_session), _=Depends(require("change:read"))):
    rows = db.scalars(select(IncidentRow).order_by(IncidentRow.id.desc()).limit(200)).all()
    return [
        {
            "incident_id": row.incident_id,
            "request_id": row.request_id,
            "title": row.title,
            "severity": row.severity,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/simulations/evaluate-change")
def simulate_change(
    body: SimulateIn,
    runtime: AssuranceRuntime = Depends(runtime_dep),
    _=Depends(require("research")),
):
    request = ChangeRequest(
        plc_id=body.plc_id,
        parameter=body.parameter,
        requested_value=body.requested_value,
        current_process_state=runtime.plant.state,
    )
    prediction = twin.simulate(runtime.plant.to_dict(), request, body.horizon)
    return prediction.model_dump(mode="json")


@router.post("/recovery/evaluate")
def evaluate_recovery(
    body: RecoveryIn,
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    user: dict = Depends(require("recovery")),
):
    request = ChangeRequest(
        request_id=body.request_id or new_id("req"),
        plc_id=body.plc_id,
        parameter=body.parameter,
        requested_value=body.requested_value,
        previous_value=body.previous_value,
        already_applied=body.already_applied,
        current_process_state=runtime.plant.state,
        source_identity=user["username"],
    )
    context = runtime.build_context(db, request, authenticated=True)
    rec = runtime.recovery.evaluate(context)
    db.add(RecoveryActionRow(action_id=new_id("rec"), request_id=request.request_id, payload=rec.model_dump(mode="json")))
    return rec.model_dump(mode="json")


@router.get("/research/compare")
def research_compare(
    db: Session = Depends(db_session),
    _=Depends(require("research")),
):
    rows = db.scalars(select(DecisionResultRow).order_by(DecisionResultRow.id.desc()).limit(100)).all()
    return [
        {
            "request_id": row.request_id,
            "full_framework": row.decision,
            "algorithms": row.payload.get("algorithm_results", {}),
            "reasons": row.payload.get("reasons", []),
        }
        for row in rows
    ]


@router.get("/metrics")
def metrics(runtime: AssuranceRuntime = Depends(runtime_dep), _=Depends(require("research"))):
    return runtime.metrics.snapshot()


@router.get("/audit")
def audit(db: Session = Depends(db_session), _=Depends(require("audit:read"))):
    rows = db.scalars(select(AuditEventRow).order_by(AuditEventRow.id.desc()).limit(300)).all()
    return [
        {
            "event_id": row.event_id,
            "correlation_id": row.correlation_id,
            "event_type": row.event_type,
            "actor": row.actor,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/capabilities")
def capabilities(_=Depends(current_user)):
    return {
        "modbus_tcp_observation": CapabilityStatus.IMPLEMENTED,
        "parameter_write_evaluation": CapabilityStatus.IMPLEMENTED,
        "fsm_engine": CapabilityStatus.IMPLEMENTED,
        "temporal_rules": CapabilityStatus.IMPLEMENTED,
        "dependency_engine": CapabilityStatus.IMPLEMENTED,
        "cross_plc": CapabilityStatus.IMPLEMENTED,
        "mock_digital_twin": CapabilityStatus.IMPLEMENTED,
        "recovery_advisory": CapabilityStatus.IMPLEMENTED,
        "enforcement": CapabilityStatus.PARTIALLY_IMPLEMENTED,
        "logic_change_interception": CapabilityStatus.SIMULATED,
        "openplc_runtime": CapabilityStatus.PARTIALLY_IMPLEMENTED,
        "siemens_s7": CapabilityStatus.PLANNED,
        "ethernet_ip_cip": CapabilityStatus.PLANNED,
        "opc_ua": CapabilityStatus.PLANNED,
        "dnp3": CapabilityStatus.PLANNED,
        "iec_60870_5_104": CapabilityStatus.PLANNED,
        "auto_state_extraction": CapabilityStatus.PLANNED,
        "machine_learning_detector": CapabilityStatus.UNSUPPORTED,
        "production_ics": CapabilityStatus.UNSUPPORTED,
    }


@router.post("/logic-changes/simulate")
def simulate_logic_change(
    plc_id: str = "tank-plc-01",
    db: Session = Depends(db_session),
    runtime: AssuranceRuntime = Depends(runtime_dep),
    user: dict = Depends(require("change:write")),
):
    event = LogicChangeEvent(
        plc_id=plc_id,
        source_identity=user["username"],
        source_host="eng-ws-02",
        summary="Simulated online edit — interception is not claimed as implemented",
        capability_status="simulated",
    )
    request = ChangeRequest(
        plc_id=plc_id,
        parameter="__logic__",
        requested_value="online_edit",
        change_class=ChangeClass.LOGIC_CHANGE,
        source_identity=user["username"],
        source_host="eng-ws-02",
        current_process_state=runtime.plant.state,
    )
    result = runtime.evaluate(db, request, authenticated=True)
    return {"event": event.model_dump(mode="json"), "decision": result.model_dump(mode="json")}


@router.post("/simulator/start")
def start_process(runtime: AssuranceRuntime = Depends(runtime_dep), _=Depends(require("change:write"))):
    runtime.plant.transition("IDLE")
    return runtime.plant.snapshot()


@router.get("/simulator/snapshot")
def simulator_snapshot(runtime: AssuranceRuntime = Depends(runtime_dep), _=Depends(require("change:read"))):
    runtime.plant.step(0.2)
    return runtime.plant.snapshot()


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
