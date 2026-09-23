"""Change interceptor, audit, seed, metrics, and in-memory process coupling."""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import DEFAULT_CATALOG, PlantCatalog
from app.config import Settings, get_settings
from app.domain.enums import Decision
from app.domain.models import (
    ApprovedChange,
    ChangeRequest,
    DecisionResult,
    EvaluationContext,
    ProcessSnapshot,
    VersionStamp,
    new_id,
    utcnow,
)
from app.engines.baselines import compare_all
from app.engines.decision import evaluate_change
from app.engines.recovery import SafeRecoveryEngine
from app.persistence.orm import (
    AlgorithmResultRow,
    ApprovedChangeRow,
    AreaRow,
    AuditEventRow,
    BaselineWindowRow,
    ChangeRequestRow,
    DecisionResultRow,
    IncidentRow,
    ModelVersionRow,
    ParameterRow,
    PlantRow,
    PlcRow,
    PolicyRow,
    RecoveryActionRow,
    StateModelRow,
)
from app.policies.parser import DEMO_POLICY_YAML, parse_policy_yaml
from app.security.auth import hash_password
from app.persistence.orm import UserRow

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.water_tank import WaterTankPlant  # noqa: E402


class Metrics:
    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)
        self.latencies: dict[str, list[float]] = defaultdict(list)

    def inc(self, name: str, n: int = 1) -> None:
        self.counters[name] += n

    def observe(self, name: str, value: float) -> None:
        self.latencies[name].append(value)

    def snapshot(self) -> dict[str, Any]:
        stats: dict[str, Any] = dict(self.counters)
        for key, values in self.latencies.items():
            if values:
                stats[f"{key}_ms_avg"] = round(sum(values) / len(values), 3)
                stats[f"{key}_ms_max"] = round(max(values), 3)
        return stats


class AssuranceRuntime:
    def __init__(self, settings: Settings | None = None, catalog: PlantCatalog | None = None):
        self.settings = (settings or get_settings()).model_copy()
        self.catalog = catalog or DEFAULT_CATALOG
        self.plant = WaterTankPlant()
        self.metrics = Metrics()
        self.recovery = SafeRecoveryEngine(self.catalog)
        self.last_trusted: dict[str, Any] = dict(self.plant.parameters())
        self.last_trusted_at = utcnow()

    def snapshot(self) -> ProcessSnapshot:
        raw = self.plant.snapshot()
        return ProcessSnapshot(
            plc_states=raw["plc_states"],
            parameters=raw["parameters"],
            sensors=raw["sensors"],
            actuators=raw["actuators"],
            last_trusted_parameters=dict(self.last_trusted),
            last_trusted_at=self.last_trusted_at,
            entered_state_at={"tank-plc-01": self.plant.entered_state_at},
        )

    def load_approvals(self, db: Session) -> list[ApprovedChange]:
        rows = db.scalars(select(ApprovedChangeRow)).all()
        out: list[ApprovedChange] = []
        for row in rows:
            payload = dict(row.payload)
            payload["consumed"] = row.consumed
            payload["consumed_by_request"] = row.consumed_by_request
            payload["approval_id"] = row.approval_id
            out.append(ApprovedChange.model_validate(payload))
        return out

    def load_recent(self, db: Session, limit: int = 50) -> list[ChangeRequest]:
        rows = db.scalars(select(ChangeRequestRow).order_by(ChangeRequestRow.id.desc()).limit(limit)).all()
        return [ChangeRequest.model_validate(row.payload) for row in reversed(rows)]

    def build_context(self, db: Session, request: ChangeRequest, authenticated: bool) -> EvaluationContext:
        snap = self.snapshot()
        if not request.current_process_state:
            request.current_process_state = self.plant.state
        if request.previous_value is None:
            request.previous_value = snap.parameters.get(request.parameter)
        versions = VersionStamp(**self.catalog.versions)
        return EvaluationContext(
            request=request,
            snapshot=snap,
            recent_changes=self.load_recent(db),
            approvals=self.load_approvals(db),
            authorized_identities=set(self.catalog.authorized_identities),
            authorized_hosts=set(self.catalog.authorized_hosts),
            authorized_roles=dict(self.catalog.authorized_identities),
            global_bounds=dict(self.catalog.global_bounds),
            authenticated=authenticated,
            auth_confidence=0.95 if authenticated else 0.0,
            asset_criticality={plc["plc_id"]: plc["criticality"] for plc in self.catalog.plcs},
            versions=versions,
        )

    def _write_audit(self, db: Session, event_type: str, correlation_id: str, actor: str, payload: dict) -> None:
        db.add(
            AuditEventRow(
                event_id=new_id("aud"),
                correlation_id=correlation_id,
                event_type=event_type,
                actor=actor,
                payload=payload,
            )
        )

    def _consume_approval(self, db: Session, result: DecisionResult, request: ChangeRequest) -> None:
        if result.decision not in {Decision.ALLOW, Decision.ALLOW_WITH_ALERT}:
            return
        details = next((c for c in result.check_details if c.name == "change_provenance"), None)
        approval_id = (details.details or {}).get("approval_id") if details else None
        if not approval_id:
            return
        row = db.scalar(select(ApprovedChangeRow).where(ApprovedChangeRow.approval_id == approval_id))
        if row and not row.consumed:
            row.consumed = True
            row.consumed_by_request = request.request_id

    def _maybe_apply(self, request: ChangeRequest, result: DecisionResult) -> bool:
        mode = self.settings.operating_mode.lower()
        enforcement = self.settings.enforcement_enabled
        if mode == "passive":
            self.plant.apply_write(request.plc_id, request.parameter, request.requested_value)
            return True
        if mode == "advisory":
            self.plant.apply_write(request.plc_id, request.parameter, request.requested_value)
            return True
        if enforcement:
            if result.decision in {Decision.ALLOW, Decision.ALLOW_WITH_ALERT}:
                self.plant.apply_write(request.plc_id, request.parameter, request.requested_value)
                return True
            return False
        # enforcement requested without lab mode: refuse to block, stay advisory
        self.plant.apply_write(request.plc_id, request.parameter, request.requested_value)
        return True

    def evaluate(
        self,
        db: Session,
        request: ChangeRequest,
        authenticated: bool,
        persist: bool = True,
        compare_algorithms: bool = True,
    ) -> DecisionResult:
        started = time.perf_counter()
        self.metrics.inc("changes_seen_total")
        try:
            context = self.build_context(db, request, authenticated)
            result = evaluate_change(context, self.catalog, self.settings.risk_policy_mode)
            if compare_algorithms:
                result.algorithm_results = compare_all(context, self.catalog)
            applied = self._maybe_apply(request, result)
            if result.decision in {Decision.ALLOW, Decision.ALLOW_WITH_ALERT}:
                self.last_trusted = dict(self.plant.parameters())
                self.last_trusted_at = utcnow()
                self.metrics.inc("changes_allowed_total")
            elif result.decision == Decision.HOLD:
                self.metrics.inc("changes_held_total")
            elif result.decision == Decision.BLOCK:
                self.metrics.inc("changes_blocked_total")
            if persist:
                db.add(ChangeRequestRow(request_id=request.request_id, payload=request.model_dump(mode="json")))
                db.add(
                    DecisionResultRow(
                        decision_id=result.decision_id,
                        request_id=request.request_id,
                        decision=result.decision.value,
                        risk_score=result.risk_score,
                        hard_violation=result.hard_violation,
                        payload=result.model_dump(mode="json"),
                    )
                )
                for algo, decision in result.algorithm_results.items():
                    db.add(
                        AlgorithmResultRow(
                            request_id=request.request_id,
                            algorithm=algo,
                            decision=decision.value,
                            reasons=result.reasons if algo == "full_framework" else [],
                        )
                    )
                self._consume_approval(db, result, request)
                self._write_audit(
                    db,
                    "change.evaluated",
                    request.request_id,
                    request.source_identity,
                    {
                        "request": request.model_dump(mode="json"),
                        "decision": result.model_dump(mode="json"),
                        "applied": applied,
                        "operating_mode": self.settings.operating_mode,
                    },
                )
                if result.decision in {Decision.BLOCK, Decision.HOLD, Decision.RECOVERY_REQUIRED}:
                    db.add(
                        IncidentRow(
                            incident_id=new_id("inc"),
                            request_id=request.request_id,
                            title=f"{result.decision.value}: {request.parameter} on {request.plc_id}",
                            severity="high" if result.hard_violation else "medium",
                            payload={
                                "reasons": result.reasons,
                                "decision": result.decision.value,
                                "sensors": context.snapshot.sensors,
                            },
                        )
                    )
                db.flush()
            elapsed = (time.perf_counter() - started) * 1000.0
            result.latency_ms = elapsed
            self.metrics.observe("policy_evaluation_latency", elapsed)
            self.metrics.observe("decision_latency", elapsed)
            return result
        except Exception as exc:
            return self._fail_safe(db, request, str(exc))

    def _fail_safe(self, db: Session, request: ChangeRequest, error: str) -> DecisionResult:
        mode = self.settings.fail_safe_mode
        self.metrics.inc("fail_safe_total")
        if mode == "fail_closed":
            decision = Decision.BLOCK
        elif mode == "fail_open":
            decision = Decision.ALLOW
            self.plant.apply_write(request.plc_id, request.parameter, request.requested_value)
        else:
            decision = Decision.HOLD
            self.plant.apply_write(request.plc_id, request.parameter, request.requested_value)
        from app.domain.enums import CheckStatus
        from app.domain.models import CheckResult, RiskBreakdown

        result = DecisionResult(
            request_id=request.request_id,
            decision=decision,
            risk_score=100.0 if decision == Decision.BLOCK else 40.0,
            hard_violation=mode == "fail_closed",
            reasons=[f"Framework fail-safe ({mode}): {error}"],
            checks={"fail_safe": CheckStatus.ERROR},
            check_details=[CheckResult(name="fail_safe", status=CheckStatus.ERROR, message=error)],
            risk=RiskBreakdown(score=100.0 if decision == Decision.BLOCK else 40.0, mode=mode),
        )
        self._write_audit(db, "fail_safe", request.request_id, "system", result.model_dump(mode="json"))
        return result

    def seed(self, db: Session) -> None:
        if db.scalar(select(UserRow).limit(1)):
            return
        demo_users = {
            "admin": ("lab-admin-change-me", "admin"),
            "engineer-a": ("lab-engineer-change-me", "engineer"),
            "operator-1": ("lab-operator-change-me", "operator"),
            "supervisor-b": ("lab-supervisor-change-me", "engineer"),
            "analyst": ("lab-analyst-change-me", "analyst"),
            "auditor": ("lab-auditor-change-me", "auditor"),
            "researcher": ("lab-researcher-change-me", "researcher"),
        }
        for username, (password, role) in demo_users.items():
            db.add(UserRow(username=username, password_hash=hash_password(password), role=role, display_name=username))
        plant = PlantRow(name="Research Water Cell", description="Deterministic tank testbed")
        db.add(plant)
        db.flush()
        area = AreaRow(plant_id=plant.id, name="Bay-1")
        db.add(area)
        db.flush()
        for plc in self.catalog.plcs:
            db.add(
                PlcRow(
                    plc_id=plc["plc_id"],
                    area_id=area.id,
                    vendor=plc["vendor"],
                    model=plc["model"],
                    ip=plc["ip"],
                    criticality=plc["criticality"],
                )
            )
            for name in plc["parameters"]:
                raw = self.plant.parameters().get(name)
                try:
                    numeric = float(raw) if raw is not None and not isinstance(raw, str) else None
                    if isinstance(raw, str):
                        numeric = float(raw) if raw.replace(".", "", 1).isdigit() else None
                except (TypeError, ValueError):
                    numeric = None
                db.add(
                    ParameterRow(
                        plc_id=plc["plc_id"],
                        name=name,
                        current_value=numeric,
                    )
                )
        db.add(StateModelRow(name="water-tank-v1", version="1.0.0", definition=self.catalog.state_model))
        parsed, digest = parse_policy_yaml(DEMO_POLICY_YAML)
        db.add(
            PolicyRow(
                name=parsed.policy.name,
                version=parsed.policy.version,
                yaml_text=DEMO_POLICY_YAML,
                content_hash=digest,
                parsed=parsed.model_dump(),
            )
        )
        now = utcnow()
        approval = ApprovedChange(
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
        db.add(
            ApprovedChangeRow(
                approval_id=approval.approval_id,
                change_ticket=approval.change_ticket,
                payload=approval.model_dump(mode="json"),
            )
        )
        db.add(BaselineWindowRow(name="commissioning-v1", trusted=True, approved=True, notes="Seeded commissioning set"))
        for kind, version in self.catalog.versions.items():
            db.add(ModelVersionRow(kind=kind, version=version))
        db.flush()


_runtime: AssuranceRuntime | None = None


def get_runtime() -> AssuranceRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AssuranceRuntime()
    return _runtime


def reset_runtime() -> None:
    global _runtime
    _runtime = None
