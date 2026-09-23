"""Comparable detectors. Each algorithm sees the same ChangeRequest and no labels."""

from __future__ import annotations

from app.catalog import PlantCatalog
from app.domain.enums import AlgorithmName, CheckStatus, Decision
from app.domain.models import EvaluationContext
from app.engines import checks as C
from app.engines.decision import fuse_decision, score_risk
from app.engines.interfaces import SafetyAlgorithm
from app.domain.models import CheckResult


def _decision_from(
    selected: list[CheckResult],
    context: EvaluationContext,
    catalog: PlantCatalog,
    extras: list[CheckResult] | None = None,
) -> Decision:
    extras = extras or []
    # Neutral PASS fillers so scoring keys exist when used internally.
    by_name = {item.name: item for item in extras + selected}
    # Only fuse the selected checks for the algorithm's published decision.
    dummy_risk = score_risk(
        {
            "authentication": by_name.get(
                "authentication", CheckResult(name="authentication", status=CheckStatus.PASS)
            ),
            "authorization": by_name.get(
                "authorization", CheckResult(name="authorization", status=CheckStatus.PASS)
            ),
            "change_provenance": by_name.get(
                "change_provenance", CheckResult(name="change_provenance", status=CheckStatus.PASS)
            ),
            "value_validity": by_name.get(
                "value_validity", CheckResult(name="value_validity", status=CheckStatus.PASS)
            ),
            "state_validation": by_name.get(
                "state_validation", CheckResult(name="state_validation", status=CheckStatus.PASS)
            ),
            "transition_validation": by_name.get(
                "transition_validation", CheckResult(name="transition_validation", status=CheckStatus.PASS)
            ),
            "temporal_validation": by_name.get(
                "temporal_validation", CheckResult(name="temporal_validation", status=CheckStatus.PASS)
            ),
            "dependency_validation": by_name.get(
                "dependency_validation", CheckResult(name="dependency_validation", status=CheckStatus.PASS)
            ),
            "cross_plc": by_name.get("cross_plc", CheckResult(name="cross_plc", status=CheckStatus.PASS)),
            "physical_safety": by_name.get(
                "physical_safety", CheckResult(name="physical_safety", status=CheckStatus.PASS)
            ),
        },
        catalog,
        context,
        "balanced",
    )
    decision, _, _ = fuse_decision(selected, dummy_risk, context, "balanced")
    return decision


class StaticRangeChecker(SafetyAlgorithm):
    name = AlgorithmName.STATIC_RANGE.value

    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> CheckResult:
        result = C.check_value_range(context, self.catalog)
        return result


class GlobalInvariantChecker(SafetyAlgorithm):
    name = AlgorithmName.GLOBAL_INVARIANT.value

    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> CheckResult:
        range_r = C.check_value_range(context, self.catalog)
        safety = C.check_physical_safety(context, self.catalog)
        if range_r.status == CheckStatus.FAIL:
            return range_r
        return safety


class FSMChecker(SafetyAlgorithm):
    name = AlgorithmName.FSM.value

    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> CheckResult:
        range_r = C.check_value_range(context, self.catalog)
        state_r = C.check_state(context, self.catalog)
        trans_r = C.check_transition(context, self.catalog)
        for item in (range_r, state_r, trans_r):
            if item.status == CheckStatus.FAIL:
                return item
        return state_r


class FSMTemporalChecker(SafetyAlgorithm):
    name = AlgorithmName.FSM_TEMPORAL.value

    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> CheckResult:
        fsm = FSMChecker(self.catalog).evaluate(context)
        if fsm.status == CheckStatus.FAIL:
            return fsm
        return C.check_temporal(context, self.catalog)


class FSMTemporalDependencyChecker(SafetyAlgorithm):
    name = AlgorithmName.FSM_TEMPORAL_DEPENDENCY.value

    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> CheckResult:
        prior = FSMTemporalChecker(self.catalog).evaluate(context)
        if prior.status == CheckStatus.FAIL:
            return prior
        return C.check_dependencies(context, self.catalog)


class FullAssuranceAlgorithm(SafetyAlgorithm):
    name = AlgorithmName.FULL_FRAMEWORK.value

    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> CheckResult:
        from app.engines.decision import evaluate_change

        result = evaluate_change(context, self.catalog)
        status = CheckStatus.PASS if result.decision in {Decision.ALLOW, Decision.ALLOW_WITH_ALERT} else CheckStatus.FAIL
        return CheckResult(
            name=self.name,
            status=status,
            hard=result.hard_violation,
            message="; ".join(result.reasons) or result.decision.value,
            details={"decision": result.decision.value},
        )


def compare_all(context: EvaluationContext, catalog: PlantCatalog) -> dict[str, Decision]:
    """Independent decisions for the research matrix. Labels are not available here."""
    from app.engines.decision import evaluate_change

    mapping: dict[str, Decision] = {}
    checkers: list[SafetyAlgorithm] = [
        StaticRangeChecker(catalog),
        GlobalInvariantChecker(catalog),
        FSMChecker(catalog),
        FSMTemporalChecker(catalog),
        FSMTemporalDependencyChecker(catalog),
    ]
    for checker in checkers:
        result = checker.evaluate(context)
        mapping[checker.name] = (
            Decision.ALLOW if result.status != CheckStatus.FAIL else Decision.BLOCK
        )
    mapping[AlgorithmName.FULL_FRAMEWORK.value] = evaluate_change(context, catalog).decision
    return mapping
