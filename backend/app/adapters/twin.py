"""Digital-twin adapter. Physics live here, not in the decision engine."""

from __future__ import annotations

from app.domain.models import ChangeRequest, TwinPrediction
from app.engines.predicates import to_float
from simulator.water_tank import WaterTankPlant


class WaterTankTwinAdapter:
    """Lightweight deterministic twin used for deep-path evaluation."""

    def simulate(self, current_state: dict, proposed_change: ChangeRequest, horizon: float) -> TwinPrediction:
        plant = WaterTankPlant.from_dict(current_state)
        key = proposed_change.parameter
        value = proposed_change.requested_value
        plant.apply_write(proposed_change.plc_id, key, value)
        times: list[float] = []
        pressures: list[float] = []
        levels: list[float] = []
        temps: list[float] = []
        states: list[str] = []
        dt = 0.2
        t = 0.0
        violations: list[str] = []
        while t <= horizon:
            plant.step(dt)
            times.append(round(t, 3))
            snap = plant.snapshot()
            pressures.append(snap["sensors"]["Pressure"])
            levels.append(snap["sensors"]["TankLevel"])
            temps.append(snap["sensors"]["Temperature"])
            states.append(snap["state"])
            if snap["sensors"]["Pressure"] > 95:
                violations.append(f"Pressure reaches unsafe value after {t:.1f} seconds")
                break
            if snap["sensors"]["TankLevel"] >= 99:
                violations.append(f"Tank overflow predicted after {t:.1f} seconds")
                break
            t += dt
        confidence = 0.75 if not current_state.get("sensor_integrity_low") else 0.25
        return TwinPrediction(
            predicted_states=states[-8:],
            predicted_variables={
                "time": times,
                "Pressure": pressures,
                "TankLevel": levels,
                "Temperature": temps,
            },
            constraint_violations=violations,
            confidence=confidence,
            simulation_time=t,
            horizon_s=horizon,
        )


def predicted_pressure(pump: float, valve: float, level: float) -> float:
    return 0.4 * level + 0.35 * pump * (1.0 - valve / 100.0)


def as_float(change: ChangeRequest) -> float | None:
    return to_float(change.requested_value)
