"""Closed-form water-tank physics and process-state machine.

Deterministic by default. Noise is applied only when an experiment sets noise_level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WaterTankPlant:
    state: str = "IDLE"
    tank_level: float = 50.0
    temperature: float = 35.0
    pressure: float = 22.0
    flow: float = 0.0
    tank_level_sp: float = 50.0
    temperature_sp: float = 40.0
    pump_speed: float = 0.0
    inlet_valve: float = 0.0
    outlet_valve: float = 0.0
    heater: float = 0.0
    alarm_high_level: float = 90.0
    pid_kp: float = 1.2
    timer_fill_ms: float = 30000.0
    maintenance_override: float = 0.0
    noise_level: float = 0.0
    entered_state_at: datetime = field(default_factory=utcnow)
    time_s: float = 0.0

    def apply_write(self, plc_id: str, parameter: str, value) -> None:
        table = {
            "TankLevel_SP": "tank_level_sp",
            "Temperature_SP": "temperature_sp",
            "PumpSpeed": "pump_speed",
            "InletValve": "inlet_valve",
            "OutletValve": "outlet_valve",
            "Heater": "heater",
            "AlarmHighLevel": "alarm_high_level",
            "PID_Kp": "pid_kp",
            "Timer_Fill_ms": "timer_fill_ms",
            "MaintenanceOverride": "maintenance_override",
            "OperatingMode": "state",
        }
        attr = table.get(parameter)
        if attr == "state":
            self.transition(str(value), force=True)
            return
        if attr:
            setattr(self, attr, float(value))

    def transition(self, new_state: str, force: bool = False) -> None:
        if new_state != self.state:
            self.state = new_state
            self.entered_state_at = utcnow()

    def step(self, dt: float = 0.2) -> None:
        inlet = (self.pump_speed / 100.0) * (self.inlet_valve / 100.0) * 8.0
        outlet = (self.outlet_valve / 100.0) * max(self.tank_level / 100.0, 0.02) * 6.0
        self.flow = inlet - outlet
        self.tank_level = min(100.0, max(0.0, self.tank_level + self.flow * dt))
        heat = 1.8 * self.heater * dt * (1.0 if self.tank_level > 5 else 0.0)
        cool = 0.15 * max(outlet, 0.0) * dt + 0.02 * dt
        self.temperature = min(150.0, max(10.0, self.temperature + heat - cool))
        self.pressure = 0.4 * self.tank_level + 0.35 * self.pump_speed * (1.0 - self.inlet_valve / 100.0)
        self.time_s += dt
        self._auto_state()

    def _auto_state(self) -> None:
        if self.state == "OFF":
            return
        if self.state == "STARTING" and self.time_s > 1.0:
            self.transition("IDLE")
        elif self.state == "IDLE" and self.inlet_valve >= 20:
            self.transition("FILLING")
        elif self.state == "FILLING" and self.tank_level >= 40:
            self.transition("HEATING")
        elif self.state == "HEATING" and self.temperature >= 80 and self.pressure <= 60:
            self.transition("PROCESSING")
        elif self.state == "PROCESSING" and self.outlet_valve >= 20:
            self.transition("DRAINING")
        elif self.state == "DRAINING" and self.tank_level <= 5:
            self.transition("COMPLETE")

    def parameters(self) -> dict:
        return {
            "tank-plc-01.TankLevel_SP": self.tank_level_sp,
            "tank-plc-01.Temperature_SP": self.temperature_sp,
            "tank-plc-01.Heater": self.heater,
            "tank-plc-01.Pressure": self.pressure,
            "tank-plc-01.AlarmHighLevel": self.alarm_high_level,
            "tank-plc-01.PID_Kp": self.pid_kp,
            "tank-plc-01.Timer_Fill_ms": self.timer_fill_ms,
            "tank-plc-01.MaintenanceOverride": self.maintenance_override,
            "pump-plc-01.PumpSpeed": self.pump_speed,
            "valve-plc-01.InletValve": self.inlet_valve,
            "valve-plc-01.OutletValve": self.outlet_valve,
            "TankLevel_SP": self.tank_level_sp,
            "Temperature_SP": self.temperature_sp,
            "Heater": self.heater,
            "Pressure": self.pressure,
            "AlarmHighLevel": self.alarm_high_level,
            "PID_Kp": self.pid_kp,
            "Timer_Fill_ms": self.timer_fill_ms,
            "MaintenanceOverride": self.maintenance_override,
            "PumpSpeed": self.pump_speed,
            "InletValve": self.inlet_valve,
            "OutletValve": self.outlet_valve,
            "OperatingMode": self.state,
        }

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "plc_states": {
                "tank-plc-01": self.state,
                "pump-plc-01": self.state,
                "valve-plc-01": self.state,
            },
            "parameters": self.parameters(),
            "sensors": {
                "TankLevel": round(self.tank_level, 3),
                "Temperature": round(self.temperature, 3),
                "Pressure": round(self.pressure, 3),
                "Flow": round(self.flow, 3),
            },
            "actuators": {
                "Pump-1": self.pump_speed,
                "Valve-1": self.inlet_valve,
                "Outlet-1": self.outlet_valve,
                "Heater-1": self.heater,
            },
        }

    def to_dict(self) -> dict:
        data = self.snapshot()
        data.update(
            {
                "tank_level": self.tank_level,
                "temperature": self.temperature,
                "pump_speed": self.pump_speed,
                "inlet_valve": self.inlet_valve,
                "outlet_valve": self.outlet_valve,
                "heater": self.heater,
                "tank_level_sp": self.tank_level_sp,
                "temperature_sp": self.temperature_sp,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "WaterTankPlant":
        plant = cls()
        for key in (
            "state",
            "tank_level",
            "temperature",
            "pressure",
            "pump_speed",
            "inlet_valve",
            "outlet_valve",
            "heater",
            "tank_level_sp",
            "temperature_sp",
        ):
            if key in data:
                setattr(plant, key, data[key] if key == "state" else float(data[key]))
        sensors = data.get("sensors") or {}
        if "TankLevel" in sensors:
            plant.tank_level = float(sensors["TankLevel"])
        if "Temperature" in sensors:
            plant.temperature = float(sensors["Temperature"])
        params = data.get("parameters") or {}
        if "PumpSpeed" in params:
            plant.pump_speed = float(params["PumpSpeed"])
        if "InletValve" in params:
            plant.inlet_valve = float(params["InletValve"])
        return plant
