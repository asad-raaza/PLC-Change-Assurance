"""Independent evaluation dimensions. Each function returns a CheckResult."""

from __future__ import annotations

from datetime import datetime, timezone

from app.catalog import PlantCatalog
from app.domain.enums import ChangeClass, CheckStatus
from app.domain.models import CheckResult, EvaluationContext
from app.engines.predicates import compare, to_float, values_close


def _now(context: EvaluationContext) -> datetime:
    ts = context.request.timestamp
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def check_authentication(context: EvaluationContext) -> CheckResult:
    if context.authenticated or context.request.source_identity in context.authorized_identities:
        confidence = context.auth_confidence or (0.9 if context.authenticated else 0.6)
        return CheckResult(
            name="authentication",
            status=CheckStatus.PASS,
            message="Identity presented and recognized",
            details={"confidence": confidence, "identity": context.request.source_identity},
        )
    return CheckResult(
        name="authentication",
        status=CheckStatus.FAIL,
        hard=False,
        message=f"Unrecognized or unauthenticated identity '{context.request.source_identity}'",
        details={"identity": context.request.source_identity},
    )


def check_authorization(context: EvaluationContext) -> CheckResult:
    identity = context.request.source_identity
    host = context.request.source_host
    role = context.authorized_roles.get(identity)
    known = identity in context.authorized_identities
    host_ok = host in context.authorized_hosts
    if not known:
        return CheckResult(
            name="authorization",
            status=CheckStatus.FAIL,
            hard=True,
            message=f"Unauthorized identity '{identity}' is not permitted to write PLC parameters",
            details={"identity": identity, "host": host},
        )
    if not host_ok:
        return CheckResult(
            name="authorization",
            status=CheckStatus.FAIL,
            hard=True,
            message=f"Source host '{host}' is not an authorized engineering or HMI workstation",
            details={"identity": identity, "host": host},
        )
    if role == "auditor":
        return CheckResult(
            name="authorization",
            status=CheckStatus.FAIL,
            hard=True,
            message="Auditor role is read-only and cannot submit PLC changes",
        )
    return CheckResult(
        name="authorization",
        status=CheckStatus.PASS,
        message=f"Identity {identity} on {host} is authorized for write operations",
        details={"role": role or "engineer", "host": host},
    )


def check_provenance(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    req = context.request
    required = req.parameter in catalog.approval_required and not req.maintenance_window
    if req.change_class == ChangeClass.LOGIC_CHANGE:
        return CheckResult(
            name="change_provenance",
            status=CheckStatus.FAIL,
            hard=True,
            message="Logic changes require an explicit approved logic-change manifest",
        )
    if not required and not req.change_ticket and not req.approved_change_id:
        return CheckResult(
            name="change_provenance",
            status=CheckStatus.PASS,
            message="No approval required for this parameter class",
        )

    matches = []
    for approval in context.approvals:
        if req.change_ticket and approval.change_ticket == req.change_ticket:
            matches.append(approval)
        elif req.approved_change_id and approval.approval_id == req.approved_change_id:
            matches.append(approval)
        elif (
            approval.plc_id == req.plc_id
            and approval.object == req.parameter
            and values_close(approval.allowed_new_value, req.requested_value)
        ):
            matches.append(approval)

    if not matches:
        return CheckResult(
            name="change_provenance",
            status=CheckStatus.FAIL,
            hard=False,
            message="No approved change manifest matches this request",
            details={"ticket": req.change_ticket, "parameter": req.parameter},
        )

    reasons: list[str] = []
    usable = None
    ts = _now(context)
    for approval in matches:
        if approval.consumed:
            reasons.append("Approval already consumed (replay or reuse)")
            continue
        if ts < approval.valid_from:
            reasons.append("Approval is not yet valid")
            continue
        if ts > approval.valid_until:
            reasons.append("Approval has expired")
            continue
        if approval.plc_id != req.plc_id:
            reasons.append("Approval is for a different PLC")
            continue
        if approval.object != req.parameter:
            reasons.append("Approval is for a different variable")
            continue
        if approval.allowed_old_value is not None and not values_close(
            approval.allowed_old_value, req.previous_value
        ):
            reasons.append("Current value does not match allowed_old_value")
            continue
        if approval.allowed_new_value is not None and not values_close(
            approval.allowed_new_value, req.requested_value
        ):
            reasons.append("Requested value does not match allowed_new_value")
            continue
        if approval.allowed_identities and req.source_identity not in approval.allowed_identities:
            reasons.append("Requesting user is not the approved requester")
            continue
        if approval.allowed_hosts and req.source_host not in approval.allowed_hosts:
            reasons.append("Requesting workstation is not the approved host")
            continue
        if (
            approval.allowed_process_states
            and req.current_process_state not in approval.allowed_process_states
        ):
            reasons.append(
                f"Process state {req.current_process_state} is not in allowed states {approval.allowed_process_states}"
            )
            continue
        usable = approval
        break

    if usable is None:
        hard = any("consumed" in r.lower() or "replay" in r.lower() for r in reasons)
        return CheckResult(
            name="change_provenance",
            status=CheckStatus.FAIL,
            hard=hard,
            message=reasons[0] if reasons else "Approved change cannot be applied",
            details={"mismatches": reasons},
        )
    return CheckResult(
        name="change_provenance",
        status=CheckStatus.PASS,
        message=f"Change matches approval {usable.change_ticket}",
        details={"approval_id": usable.approval_id, "ticket": usable.change_ticket},
    )


def check_value_range(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    req = context.request
    bounds = catalog.global_bounds.get(req.parameter)
    value = to_float(req.requested_value)
    if bounds is None or value is None:
        return CheckResult(
            name="value_validity",
            status=CheckStatus.SKIP,
            message="No global numeric bounds for this parameter or value is non-numeric",
        )
    lo, hi = bounds
    if lo <= value <= hi:
        return CheckResult(
            name="value_validity",
            status=CheckStatus.PASS,
            message=f"{req.parameter}={value} is inside global bounds [{lo}, {hi}]",
            details={"min": lo, "max": hi, "value": value},
        )
    return CheckResult(
        name="value_validity",
        status=CheckStatus.FAIL,
        hard=True,
        message=f"{req.parameter}={value} is outside global bounds [{lo}, {hi}]",
        details={"min": lo, "max": hi, "value": value},
    )


def check_state(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    req = context.request
    state_name = req.current_process_state
    states = catalog.state_model.get("states", {})
    spec = states.get(state_name)
    if spec is None:
        return CheckResult(
            name="state_validation",
            status=CheckStatus.SKIP,
            message=f"No state definition for {state_name}",
        )
    bounds = spec.get("parameter_bounds", {})
    if req.parameter not in bounds:
        return CheckResult(
            name="state_validation",
            status=CheckStatus.PASS,
            message=f"{req.parameter} has no state-specific bound in {state_name}",
        )
    lo, hi = bounds[req.parameter]
    value = to_float(req.requested_value)
    if value is None:
        return CheckResult(
            name="state_validation",
            status=CheckStatus.SKIP,
            message="Non-numeric value; state bound not applied",
        )
    if lo <= value <= hi:
        return CheckResult(
            name="state_validation",
            status=CheckStatus.PASS,
            message=f"{req.parameter}={value} is permitted in {state_name} (limit {lo}-{hi})",
            details={"state": state_name, "min": lo, "max": hi},
        )
    return CheckResult(
        name="state_validation",
        status=CheckStatus.FAIL,
        hard=True,
        message=(
            f"{req.parameter} change to {value} is not permitted in {state_name} "
            f"(state limit {lo}-{hi})"
        ),
        details={"state": state_name, "min": lo, "max": hi, "value": value},
    )


def check_transition(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    req = context.request
    if req.parameter != "OperatingMode" and req.change_class != ChangeClass.MODE_CHANGE:
        return CheckResult(
            name="transition_validation",
            status=CheckStatus.PASS,
            message="Not a mode-transition request",
        )
    target = str(req.requested_value)
    current = req.current_process_state
    legal = {
        (row["from"], row["to"]) for row in catalog.state_model.get("transitions", [])
    }
    if (current, target) in legal:
        guards = []
        for row in catalog.state_model.get("transitions", []):
            if row["from"] == current and row["to"] == target:
                guards = row.get("guards", [])
        failed = []
        merged = {**context.snapshot.parameters, **context.snapshot.sensors}
        for guard in guards:
            parts = guard.split()
            if len(parts) >= 3:
                name, op, rhs = parts[0], parts[1], " ".join(parts[2:])
                if not compare(merged.get(name), f"{op} {rhs}"):
                    failed.append(guard)
        if failed:
            return CheckResult(
                name="transition_validation",
                status=CheckStatus.FAIL,
                hard=True,
                message=f"Transition {current} → {target} failed guards: {failed}",
            )
        return CheckResult(
            name="transition_validation",
            status=CheckStatus.PASS,
            message=f"Transition {current} → {target} is legal",
        )
    return CheckResult(
        name="transition_validation",
        status=CheckStatus.FAIL,
        hard=True,
        message=f"Invalid process transition {current} → {target}",
    )


def check_temporal(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    req = context.request
    ts = _now(context)
    new_v = to_float(req.requested_value)
    for rule in catalog.temporal_rules:
        if rule.get("parameter") != req.parameter:
            continue
        window = float(rule.get("window_s", 30.0))
        if "max_increase" in rule and new_v is not None:
            start_v = to_float(req.previous_value)
            earliest = None
            for prior in context.recent_changes:
                if prior.parameter != req.parameter:
                    continue
                age = (ts - prior.timestamp).total_seconds()
                if 0 <= age <= window:
                    pv = to_float(prior.previous_value)
                    if pv is not None and (earliest is None or prior.timestamp < earliest[0]):
                        earliest = (prior.timestamp, pv)
            baseline = earliest[1] if earliest else start_v
            if baseline is not None:
                delta = new_v - baseline
                if delta > float(rule["max_increase"]):
                    return CheckResult(
                        name="temporal_validation",
                        status=CheckStatus.FAIL,
                        hard=bool(rule.get("hard", True)),
                        message=(
                            f"{rule['message']} (observed +{delta:.1f} from {baseline} to {new_v} "
                            f"within {window:.0f}s)"
                        ),
                        details={"rule": rule["id"], "delta": delta, "window_s": window},
                    )
        if "rising_edge_above" in rule and new_v is not None:
            threshold = float(rule["rising_edge_above"])
            prev = to_float(req.previous_value) or 0.0
            edges = 1 if new_v > threshold >= prev else 0
            for prior in context.recent_changes:
                if prior.parameter != req.parameter:
                    continue
                age = (ts - prior.timestamp).total_seconds()
                if 0 <= age <= float(rule.get("window_s", 60.0)):
                    pv = to_float(prior.previous_value) or 0.0
                    nv = to_float(prior.requested_value) or 0.0
                    if nv > threshold >= pv:
                        edges += 1
            if edges > int(rule.get("max_events", 3)):
                return CheckResult(
                    name="temporal_validation",
                    status=CheckStatus.FAIL,
                    hard=True,
                    message=f"{rule['message']} ({edges} events)",
                    details={"rule": rule["id"], "events": edges},
                )
    return CheckResult(
        name="temporal_validation",
        status=CheckStatus.PASS,
        message="No temporal constraint violated",
    )


def _projected_values(context: EvaluationContext) -> dict:
    values: dict = dict(context.snapshot.parameters)
    values.update(context.snapshot.sensors)
    values.update(context.snapshot.actuators)
    values[context.request.parameter] = context.request.requested_value
    # Also expose plc.param keys for cross-PLC rules.
    values[f"{context.request.plc_id}.{context.request.parameter}"] = context.request.requested_value
    return values


def _rule_applies(rule: dict, context: EvaluationContext, values: dict) -> bool:
    when_state = rule.get("when_state")
    if when_state and context.request.current_process_state != when_state:
        return False
    if_clause = rule.get("if") or {}
    return all(compare(values.get(key), expr) for key, expr in if_clause.items())


def check_dependencies(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    values = _projected_values(context)
    violations = []
    for rule in catalog.dependency_rules:
        if not _rule_applies(rule, context, values):
            continue
        then_clause = rule.get("then") or {}
        for key, expr in then_clause.items():
            if not compare(values.get(key), expr):
                violations.append(rule)
                break
    if not violations:
        return CheckResult(
            name="dependency_validation",
            status=CheckStatus.PASS,
            message="Parameter combination satisfies relational constraints",
        )
    hard = any(v.get("hard") for v in violations)
    messages = [v["message"] for v in violations]
    return CheckResult(
        name="dependency_validation",
        status=CheckStatus.FAIL,
        hard=hard,
        message=messages[0],
        details={"violations": messages},
    )


def check_cross_plc(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    values = _projected_values(context)
    # Flatten snapshot keys that may already be qualified.
    for key, val in list(context.snapshot.parameters.items()):
        values.setdefault(key, val)
    violations = []
    for rule in catalog.cross_plc_rules:
        when = rule.get("when") or {}
        if when and all(compare(values.get(key), expr) for key, expr in when.items()):
            violations.append(rule["message"])
    if violations:
        return CheckResult(
            name="cross_plc",
            status=CheckStatus.FAIL,
            hard=True,
            message=violations[0],
            details={"violations": violations},
        )
    return CheckResult(
        name="cross_plc",
        status=CheckStatus.PASS,
        message="No cross-PLC conflict detected for the projected plant state",
    )


def check_physical_safety(context: EvaluationContext, catalog: PlantCatalog) -> CheckResult:
    """Deterministic envelope — physics equations live in the safety plugin, not here."""
    values = _projected_values(context)
    pump = to_float(values.get("PumpSpeed") or values.get("pump-plc-01.PumpSpeed")) or 0.0
    valve = to_float(values.get("InletValve") or values.get("valve-plc-01.InletValve")) or 0.0
    level = to_float(values.get("TankLevel")) or 50.0
    # Predicted pressure used as a hard envelope when confidence is implicit (deterministic).
    predicted_pressure = 0.4 * level + 0.35 * pump * (1.0 - valve / 100.0)
    if predicted_pressure > 95:
        return CheckResult(
            name="physical_safety",
            status=CheckStatus.FAIL,
            hard=True,
            message=(
                f"Predicted pressure {predicted_pressure:.1f} exceeds safety envelope 95 "
                f"(level={level}, pump={pump}, inlet={valve})"
            ),
            details={"predicted_pressure": predicted_pressure},
        )
    temp_sp = to_float(context.request.requested_value) if context.request.parameter == "Temperature_SP" else to_float(
        values.get("Temperature_SP")
    )
    pressure = to_float(values.get("Pressure")) or predicted_pressure
    if temp_sp is not None and temp_sp > 85 and pressure > 70:
        return CheckResult(
            name="physical_safety",
            status=CheckStatus.FAIL,
            hard=True,
            message=(
                f"Safety policy prohibits temperature above 85°C when pressure > 70 PSI "
                f"(requested {temp_sp}, pressure {pressure:.1f})"
            ),
        )
    return CheckResult(
        name="physical_safety",
        status=CheckStatus.PASS,
        message="Deterministic safety envelope holds for the projected state",
        details={"predicted_pressure": predicted_pressure},
    )
