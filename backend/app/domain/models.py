"""Pydantic domain objects used by engines, APIs, and experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.enums import ChangeClass, CheckStatus, Decision, ProcessStateName


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class ChangeRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: new_id("req"))
    timestamp: datetime = Field(default_factory=utcnow)
    source_identity: str = "unknown"
    source_host: str = "unknown"
    source_ip: str = ""
    protocol: str = "modbus_tcp"
    plc_id: str
    plc_vendor: str = "openplc"
    plc_model: str = "soft-plc"
    asset_id: str | None = None
    parameter: str
    parameter_type: str = "setpoint"
    previous_value: float | int | str | bool | None = None
    requested_value: float | int | str | bool | None = None
    current_process_state: str = ProcessStateName.IDLE.value
    requested_operation: str = "write_register"
    approved_change_id: str | None = None
    change_ticket: str | None = None
    session_id: str | None = None
    authentication_context: dict[str, Any] = Field(default_factory=dict)
    change_class: ChangeClass = ChangeClass.SETPOINT_CHANGE
    maintenance_window: bool = False
    already_applied: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Experiment harness may attach a label on the wrapper, never on the
    # object passed into detectors. Kept here only when explicitly allowed.
    label: str | None = None
    attack_type: str | None = None


class LogicChangeEvent(BaseModel):
    """First-class logic edit. Interception is simulated unless an adapter says otherwise."""

    event_id: str = Field(default_factory=lambda: new_id("logic"))
    timestamp: datetime = Field(default_factory=utcnow)
    plc_id: str
    source_identity: str = "unknown"
    source_host: str = "unknown"
    edit_kind: str = "online_edit"  # download | online_edit | fb | ladder | st
    capability_status: str = "simulated"
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CheckResult(BaseModel):
    name: str
    status: CheckStatus
    hard: bool = False
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0


class RiskBreakdown(BaseModel):
    score: float
    mode: str
    factors: dict[str, float] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)


class VersionStamp(BaseModel):
    framework_version: str = "0.1.0"
    policy_version: str = "0"
    state_model_version: str = "0"
    safety_model_version: str = "0"
    dependency_graph_version: str = "0"
    process_model_version: str = "0"
    experiment_config_version: str = "0"


class DecisionResult(BaseModel):
    decision_id: str = Field(default_factory=lambda: new_id("dec"))
    request_id: str
    decision: Decision
    risk_score: float
    hard_violation: bool
    reasons: list[str] = Field(default_factory=list)
    checks: dict[str, CheckStatus] = Field(default_factory=dict)
    check_details: list[CheckResult] = Field(default_factory=list)
    risk: RiskBreakdown
    versions: VersionStamp = Field(default_factory=VersionStamp)
    algorithm_results: dict[str, Decision] = Field(default_factory=dict)
    recommended_recovery: str | None = None
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=utcnow)


class ApprovedChange(BaseModel):
    approval_id: str = Field(default_factory=lambda: new_id("apr"))
    change_ticket: str
    requester: str
    approvers: list[str] = Field(default_factory=list)
    plc_id: str
    object: str
    allowed_old_value: float | int | str | bool | None = None
    allowed_new_value: float | int | str | bool | None = None
    valid_from: datetime
    valid_until: datetime
    allowed_process_states: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_identities: list[str] = Field(default_factory=list)
    reason: str = ""
    consumed: bool = False
    consumed_by_request: str | None = None


class ProcessSnapshot(BaseModel):
    plc_states: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    sensors: dict[str, float] = Field(default_factory=dict)
    actuators: dict[str, float | int | str | bool] = Field(default_factory=dict)
    last_trusted_parameters: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    last_trusted_at: datetime | None = None
    entered_state_at: dict[str, datetime] = Field(default_factory=dict)


class EvaluationContext(BaseModel):
    """Everything an engine may read. Must never include experiment labels."""

    request: ChangeRequest
    snapshot: ProcessSnapshot
    recent_changes: list[ChangeRequest] = Field(default_factory=list)
    approvals: list[ApprovedChange] = Field(default_factory=list)
    authorized_identities: set[str] = Field(default_factory=set)
    authorized_hosts: set[str] = Field(default_factory=set)
    authorized_roles: dict[str, str] = Field(default_factory=dict)
    global_bounds: dict[str, tuple[float, float]] = Field(default_factory=dict)
    authenticated: bool = False
    auth_confidence: float = 0.0
    asset_criticality: dict[str, int] = Field(default_factory=dict)
    versions: VersionStamp = Field(default_factory=VersionStamp)

    model_config = {"arbitrary_types_allowed": True}


class TwinPrediction(BaseModel):
    predicted_states: list[str] = Field(default_factory=list)
    predicted_variables: dict[str, list[float]] = Field(default_factory=dict)
    constraint_violations: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    simulation_time: float = 0.0
    horizon_s: float = 0.0


class RecoveryRecommendation(BaseModel):
    action: str
    target_values: dict[str, float | int | str | bool] = Field(default_factory=dict)
    rationale: list[str] = Field(default_factory=list)
    requires_operator: bool = True
    automatic_allowed: bool = False
