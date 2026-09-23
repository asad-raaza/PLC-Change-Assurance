"""SQLAlchemy 2.0 schema. History rows are append-oriented."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.models import utcnow


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlantRow(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class AreaRow(Base):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"))
    name: Mapped[str] = mapped_column(String(120))


class PlcRow(Base):
    __tablename__ = "plcs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plc_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"), nullable=True)
    vendor: Mapped[str] = mapped_column(String(80), default="openplc")
    model: Mapped[str] = mapped_column(String(80), default="soft-plc")
    firmware: Mapped[str] = mapped_column(String(80), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    protocol: Mapped[str] = mapped_column(String(32), default="modbus_tcp")
    program_version: Mapped[str] = mapped_column(String(80), default="1.0.0")
    operating_mode: Mapped[str] = mapped_column(String(32), default="RUN")
    safety_classification: Mapped[str] = mapped_column(String(32), default="BPCS")
    criticality: Mapped[int] = mapped_column(Integer, default=3)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    parameters: Mapped[list[ParameterRow]] = relationship(back_populates="plc")


class ParameterRow(Base):
    __tablename__ = "parameters"
    __table_args__ = (UniqueConstraint("plc_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plc_id: Mapped[str] = mapped_column(ForeignKey("plcs.plc_id"))
    name: Mapped[str] = mapped_column(String(120))
    parameter_type: Mapped[str] = mapped_column(String(40), default="setpoint")
    unit: Mapped[str] = mapped_column(String(32), default="")
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    plc: Mapped[PlcRow] = relationship(back_populates="parameters")


class SensorRow(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(32), default="")
    associated_plc: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ActuatorRow(Base):
    __tablename__ = "actuators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actuator_id: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    controlled_by_plc: Mapped[str | None] = mapped_column(String(80), nullable=True)
    affects_process: Mapped[str] = mapped_column(String(80), default="water-tank")


class StateModelRow(Base):
    __tablename__ = "state_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PolicyRow(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    yaml_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="active")
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)


class ModelVersionRow(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(32))
    checksum: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")


class ApprovedChangeRow(Base):
    __tablename__ = "approved_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approval_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    change_ticket: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed_by_request: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChangeRequestRow(Base):
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DecisionResultRow(Base):
    __tablename__ = "decision_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(40), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    hard_violation: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlgorithmResultRow(Base):
    __tablename__ = "algorithm_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    algorithm: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(40))
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(80), default="")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IncidentRow(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20), default="high")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecoveryActionRow(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_id: Mapped[str] = mapped_column(String(64), unique=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ObservationRow(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    trusted_window: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_for_policy: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BaselineWindowRow(Base):
    __tablename__ = "baseline_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExperimentRunRow(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True)
    config: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExperimentEventRow(Base):
    __tablename__ = "experiment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    request_id: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(40))
    attack_type: Mapped[str] = mapped_column(String(80), default="")
    predictions: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrossPlcEdgeRow(Base):
    __tablename__ = "cross_plc_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_node: Mapped[str] = mapped_column(String(80))
    edge_type: Mapped[str] = mapped_column(String(40))
    to_node: Mapped[str] = mapped_column(String(80))
    constraint: Mapped[dict] = mapped_column(JSON, default=dict)
