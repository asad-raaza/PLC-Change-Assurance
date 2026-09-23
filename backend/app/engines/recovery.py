"""Advisory recovery. Never assumes previous_value == safe_value."""

from __future__ import annotations

from app.catalog import PlantCatalog
from app.domain.models import EvaluationContext, RecoveryRecommendation
from app.engines.predicates import to_float


class SafeRecoveryEngine:
    def __init__(self, catalog: PlantCatalog):
        self.catalog = catalog

    def evaluate(self, context: EvaluationContext) -> RecoveryRecommendation:
        req = context.request
        reasons: list[str] = []
        current = to_float(context.snapshot.sensors.get("TankLevel"))
        previous = to_float(req.previous_value)
        last_trusted = to_float(context.snapshot.last_trusted_parameters.get(req.parameter))
        state = req.current_process_state
        bounds = (
            self.catalog.state_model.get("states", {}).get(state, {}).get("parameter_bounds", {}).get(req.parameter)
        )

        if previous is not None and bounds and not (bounds[0] <= previous <= bounds[1]):
            reasons.append(
                f"Previous value {previous} is outside the current {state} envelope {bounds}; "
                "it is not a safe rollback target"
            )
            previous = None

        if last_trusted is not None and bounds and bounds[0] <= last_trusted <= bounds[1]:
            reasons.append(
                f"Last trusted value {last_trusted} remains inside the current operating envelope"
            )
            return RecoveryRecommendation(
                action="restore_last_trusted",
                target_values={req.parameter: last_trusted},
                rationale=reasons,
                requires_operator=True,
                automatic_allowed=False,
            )

        if previous is not None:
            reasons.append(
                "Previous value is still inside the current envelope but must be operator-confirmed"
            )
            return RecoveryRecommendation(
                action="restore_previous_if_confirmed",
                target_values={req.parameter: previous},
                rationale=reasons,
                requires_operator=True,
                automatic_allowed=False,
            )

        if bounds:
            safe = (bounds[0] + bounds[1]) / 2.0
            reasons.append(
                f"No trusted rollback target; recommending midpoint {safe} of {state} bounds {bounds}"
            )
            if current is not None and current > 90:
                reasons.append("Tank level is high; recommend transitioning toward EMERGENCY if pressure rises")
                return RecoveryRecommendation(
                    action="transition_to_safe_state",
                    target_values={"OperatingMode": "EMERGENCY", req.parameter: bounds[0]},
                    rationale=reasons,
                    requires_operator=True,
                    automatic_allowed=False,
                )
            return RecoveryRecommendation(
                action="move_to_known_safe_value",
                target_values={req.parameter: safe},
                rationale=reasons,
                requires_operator=True,
                automatic_allowed=False,
            )

        reasons.append("Insufficient model data; freeze the proposed change and request operator approval")
        return RecoveryRecommendation(
            action="freeze_and_request_approval",
            target_values={},
            rationale=reasons,
            requires_operator=True,
            automatic_allowed=False,
        )
