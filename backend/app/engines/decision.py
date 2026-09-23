"""Explainable decision fusion. Hard violations override numerical risk."""

from __future__ import annotations

import time

from app.catalog import PlantCatalog
from app.domain.enums import CheckStatus, Decision, RiskPolicyMode
from app.domain.models import (
    CheckResult,
    DecisionResult,
    EvaluationContext,
    RiskBreakdown,
    VersionStamp,
)
from app.engines import checks as C


def _factor(status: CheckStatus, hard: bool) -> float:
    if status == CheckStatus.FAIL:
        return 1.0 if hard else 0.7
    if status == CheckStatus.WARN:
        return 0.35
    if status == CheckStatus.ERROR:
        return 0.5
    return 0.0


def score_risk(
    check_map: dict[str, CheckResult],
    catalog: PlantCatalog,
    context: EvaluationContext,
    mode: str,
) -> RiskBreakdown:
    weights = dict(catalog.risk_weights)
    factors = {
        "identity": _factor(check_map["authentication"].status, check_map["authentication"].hard),
        "authorization": _factor(check_map["authorization"].status, check_map["authorization"].hard),
        "provenance": _factor(check_map["change_provenance"].status, check_map["change_provenance"].hard),
        "value_deviation": _factor(check_map["value_validity"].status, check_map["value_validity"].hard),
        "state": _factor(check_map["state_validation"].status, check_map["state_validation"].hard),
        "transition": _factor(check_map["transition_validation"].status, check_map["transition_validation"].hard),
        "rate": _factor(check_map["temporal_validation"].status, check_map["temporal_validation"].hard),
        "dependency": _factor(check_map["dependency_validation"].status, check_map["dependency_validation"].hard),
        "cross_plc": _factor(check_map["cross_plc"].status, check_map["cross_plc"].hard),
        "physical_safety": _factor(check_map["physical_safety"].status, check_map["physical_safety"].hard),
        "historical": 0.0,
        "replay": 1.0 if "replay" in (check_map["change_provenance"].message or "").lower() else 0.0,
        "criticality": min(1.0, context.asset_criticality.get(context.request.plc_id, 3) / 5.0)
        if any(c.status == CheckStatus.FAIL for c in check_map.values())
        else 0.0,
    }
    raw = sum(weights[k] * factors[k] for k in weights)
    max_possible = sum(weights.values()) or 1.0
    score = round(100.0 * raw / max_possible, 2)
    return RiskBreakdown(score=score, mode=mode, factors=factors, weights=weights)


def fuse_decision(
    results: list[CheckResult],
    risk: RiskBreakdown,
    context: EvaluationContext,
    mode: str,
) -> tuple[Decision, bool, list[str]]:
    hard = any(r.status == CheckStatus.FAIL and r.hard for r in results)
    reasons = [r.message for r in results if r.status in {CheckStatus.FAIL, CheckStatus.WARN} and r.message]
    by_name = {r.name: r for r in results}

    if hard:
        if context.request.already_applied:
            return Decision.RECOVERY_REQUIRED, True, reasons
        return Decision.BLOCK, True, reasons

    authz = by_name["authorization"]
    provenance = by_name["change_provenance"]
    if authz.status == CheckStatus.FAIL:
        return Decision.BLOCK, False, reasons
    if provenance.status == CheckStatus.FAIL:
        if "expired" in provenance.message.lower():
            return Decision.HOLD, False, reasons
        return Decision.REQUIRE_APPROVAL, False, reasons

    if any(r.status == CheckStatus.FAIL for r in results):
        return Decision.HOLD, False, reasons

    if mode == RiskPolicyMode.MONITOR_ONLY.value:
        if any(r.status == CheckStatus.WARN for r in results):
            return Decision.ALLOW_WITH_ALERT, False, reasons
        return Decision.ALLOW, False, reasons

    hold_cut = 55.0 if mode == RiskPolicyMode.CONSERVATIVE.value else 80.0
    if risk.score >= hold_cut and mode == RiskPolicyMode.CONSERVATIVE.value:
        return Decision.HOLD, False, reasons or ["Conservative policy holds elevated-risk changes"]

    if any(r.status == CheckStatus.WARN for r in results):
        return Decision.ALLOW_WITH_ALERT, False, reasons
    return Decision.ALLOW, False, reasons


def run_fast_path(context: EvaluationContext, catalog: PlantCatalog) -> dict[str, CheckResult]:
    ordered = [
        C.check_authentication(context),
        C.check_authorization(context),
        C.check_provenance(context, catalog),
        C.check_value_range(context, catalog),
        C.check_state(context, catalog),
        C.check_transition(context, catalog),
        C.check_temporal(context, catalog),
        C.check_dependencies(context, catalog),
        C.check_cross_plc(context, catalog),
        C.check_physical_safety(context, catalog),
    ]
    return {item.name: item for item in ordered}


def evaluate_change(
    context: EvaluationContext,
    catalog: PlantCatalog,
    risk_mode: str = "balanced",
) -> DecisionResult:
    started = time.perf_counter()
    checks = run_fast_path(context, catalog)
    risk = score_risk(checks, catalog, context, risk_mode)
    decision, hard, reasons = fuse_decision(list(checks.values()), risk, context, risk_mode)
    versions = context.versions or VersionStamp()
    if catalog.versions:
        versions = VersionStamp(
            framework_version=catalog.versions.get("framework_version", versions.framework_version),
            policy_version=catalog.versions.get("policy_version", versions.policy_version),
            state_model_version=catalog.versions.get("state_model_version", versions.state_model_version),
            safety_model_version=catalog.versions.get("safety_model_version", versions.safety_model_version),
            dependency_graph_version=catalog.versions.get(
                "dependency_graph_version", versions.dependency_graph_version
            ),
            process_model_version=catalog.versions.get("process_model_version", versions.process_model_version),
            experiment_config_version=catalog.versions.get(
                "experiment_config_version", versions.experiment_config_version
            ),
        )
    return DecisionResult(
        request_id=context.request.request_id,
        decision=decision,
        risk_score=risk.score,
        hard_violation=hard,
        reasons=reasons,
        checks={name: item.status for name, item in checks.items()},
        check_details=list(checks.values()),
        risk=risk,
        versions=versions,
        latency_ms=(time.perf_counter() - started) * 1000.0,
    )
