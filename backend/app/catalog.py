"""Commissioned water-tank plant. Loaded from code/fixtures, stored in the database on seed.

Learned observations are NOT automatically trusted (see BaselineService).
"""

from __future__ import annotations

from dataclasses import dataclass, field

WATER_TANK_STATE_MODEL = {
    "name": "water-tank-v1",
    "version": "1.0.0",
    "states": {
        "OFF": {
            "min_duration_ms": 0,
            "max_duration_ms": None,
            "parameter_bounds": {
                "TankLevel_SP": [0, 20],
                "Temperature_SP": [0, 30],
                "PumpSpeed": [0, 0],
                "InletValve": [0, 0],
                "OutletValve": [0, 100],
            },
        },
        "STARTING": {
            "min_duration_ms": 500,
            "max_duration_ms": 10000,
            "parameter_bounds": {
                "TankLevel_SP": [0, 40],
                "PumpSpeed": [0, 20],
            },
        },
        "IDLE": {
            "min_duration_ms": 0,
            "max_duration_ms": None,
            "parameter_bounds": {
                "TankLevel_SP": [20, 80],
                "Temperature_SP": [15, 50],
                "PumpSpeed": [0, 40],
                "InletValve": [0, 40],
                "OutletValve": [0, 40],
                "Heater": [0, 0],
            },
        },
        "FILLING": {
            "min_duration_ms": 1000,
            "max_duration_ms": 300000,
            "parameter_bounds": {
                "TankLevel_SP": [20, 90],
                "PumpSpeed": [10, 80],
                "InletValve": [20, 100],
            },
        },
        "HEATING": {
            "min_duration_ms": 1000,
            "max_duration_ms": 600000,
            "parameter_bounds": {
                "TankLevel_SP": [40, 85],
                "Temperature_SP": [60, 85],
                "Pressure": [0, 70],
                "Heater": [1, 1],
                "PumpSpeed": [10, 70],
            },
            "entry": {"TankLevel": ">= 40"},
            "exit_guards": {"Temperature": ">= 80", "Pressure": "<= 60"},
        },
        "PROCESSING": {
            "min_duration_ms": 2000,
            "max_duration_ms": 600000,
            "parameter_bounds": {
                "TankLevel_SP": [40, 90],
                "Temperature_SP": [70, 90],
                "PumpSpeed": [20, 70],
            },
        },
        "DRAINING": {
            "min_duration_ms": 1000,
            "max_duration_ms": 300000,
            "parameter_bounds": {
                "OutletValve": [20, 100],
                "PumpSpeed": [0, 30],
            },
        },
        "COMPLETE": {
            "parameter_bounds": {"PumpSpeed": [0, 0], "Heater": [0, 0]},
        },
        "EMERGENCY": {
            "parameter_bounds": {
                "PumpSpeed": [0, 0],
                "Heater": [0, 0],
                "InletValve": [0, 0],
                "OutletValve": [0, 100],
            },
        },
        "MAINTENANCE": {
            "parameter_bounds": {
                "TankLevel_SP": [0, 100],
                "Temperature_SP": [0, 100],
                "PumpSpeed": [0, 100],
            },
        },
    },
    "transitions": [
        {"from": "OFF", "to": "STARTING", "guards": []},
        {"from": "STARTING", "to": "IDLE", "guards": []},
        {"from": "IDLE", "to": "FILLING", "guards": ["InletValve >= 20"]},
        {"from": "IDLE", "to": "MAINTENANCE", "guards": []},
        {"from": "MAINTENANCE", "to": "IDLE", "guards": []},
        {"from": "FILLING", "to": "HEATING", "guards": ["TankLevel >= 40"]},
        {"from": "HEATING", "to": "PROCESSING", "guards": ["Temperature >= 80", "Pressure <= 60"]},
        {"from": "PROCESSING", "to": "DRAINING", "guards": ["OutletValve >= 20"]},
        {"from": "DRAINING", "to": "COMPLETE", "guards": ["TankLevel <= 5"]},
        {"from": "COMPLETE", "to": "IDLE", "guards": []},
        {"from": "IDLE", "to": "EMERGENCY", "guards": []},
        {"from": "FILLING", "to": "EMERGENCY", "guards": []},
        {"from": "HEATING", "to": "EMERGENCY", "guards": []},
        {"from": "PROCESSING", "to": "EMERGENCY", "guards": []},
        {"from": "DRAINING", "to": "EMERGENCY", "guards": []},
    ],
}

GLOBAL_BOUNDS = {
    "TankLevel_SP": (0.0, 100.0),
    "Temperature_SP": (0.0, 120.0),
    "PumpSpeed": (0.0, 100.0),
    "InletValve": (0.0, 100.0),
    "OutletValve": (0.0, 100.0),
    "Heater": (0.0, 1.0),
    "Pressure": (0.0, 120.0),
    "AlarmHighLevel": (50.0, 100.0),
    "PID_Kp": (0.0, 10.0),
    "Timer_Fill_ms": (100.0, 600000.0),
}

# Relational constraints (local and cross-PLC).
DEPENDENCY_RULES = [
    {
        "id": "pump-valve-min-open",
        "if": {"PumpSpeed": "> 60"},
        "then": {"InletValve": "> 40"},
        "message": "If PumpSpeed > 60% then InletValve must be > 40%",
        "hard": True,
    },
    {
        "id": "heat-pressure",
        "if": {"Temperature_SP": "> 85"},
        "then": {"Pressure": "< 70"},
        "message": "If Temperature_SP > 85 then Pressure must be < 70",
        "hard": True,
    },
    {
        "id": "heating-cooling-mutex",
        "when_state": "HEATING",
        "if": {"Heater": "== 1"},
        "then": {"OutletValve": "!= 0"},
        "message": "In HEATING with Heater ON, cooling/outlet path must not be fully closed",
        "hard": False,
    },
]

CROSS_PLC_RULES = [
    {
        "id": "pump-vs-valve-plc",
        "when": {
            "pump-plc-01.PumpSpeed": "> 80",
            "valve-plc-01.InletValve": "<= 5",
        },
        "message": "PLC-A pump high while PLC-B inlet valve is closed is a globally unsafe combination",
        "hard": True,
    }
]

TEMPORAL_RULES = [
    {
        "id": "level-sp-rate",
        "parameter": "TankLevel_SP",
        "max_increase": 10.0,
        "window_s": 30.0,
        "message": "TankLevel_SP must not increase more than 10 units in 30 seconds",
        "hard": True,
    },
    {
        "id": "pump-start-burst",
        "parameter": "PumpSpeed",
        "rising_edge_above": 5.0,
        "max_events": 3,
        "window_s": 60.0,
        "message": "Pump start must not occur more than 3 times in 60 seconds",
        "hard": True,
    },
    {
        "id": "maintenance-override-ttl",
        "parameter": "MaintenanceOverride",
        "max_true_duration_s": 1200.0,
        "message": "Maintenance override must expire after 20 minutes",
        "hard": True,
    },
]

# Risk weights live here — not scattered as magic numbers in engines.
RISK_WEIGHTS = {
    "identity": 10.0,
    "authorization": 12.0,
    "provenance": 12.0,
    "value_deviation": 8.0,
    "state": 12.0,
    "transition": 10.0,
    "rate": 8.0,
    "dependency": 10.0,
    "cross_plc": 8.0,
    "physical_safety": 15.0,
    "historical": 5.0,
    "replay": 10.0,
    "criticality": 5.0,
}

APPROVAL_REQUIRED_PARAMETERS = {
    "TankLevel_SP",
    "Temperature_SP",
    "PumpSpeed",
    "PID_Kp",
    "AlarmHighLevel",
    "Timer_Fill_ms",
}

AUTHORIZED_IDENTITIES = {
    "engineer-a": "engineer",
    "operator-1": "operator",
    "supervisor-b": "engineer",
    "admin": "admin",
    "analyst": "analyst",
    "auditor": "auditor",
    "researcher": "researcher",
}

AUTHORIZED_HOSTS = {"eng-ws-02", "hmi-01", "operator-panel-1"}

PLCS = [
    {
        "plc_id": "tank-plc-01",
        "vendor": "openplc",
        "model": "soft-plc",
        "ip": "10.0.20.10",
        "criticality": 5,
        "parameters": [
            "TankLevel_SP",
            "Temperature_SP",
            "Heater",
            "Pressure",
            "AlarmHighLevel",
            "PID_Kp",
            "Timer_Fill_ms",
            "MaintenanceOverride",
            "OperatingMode",
        ],
    },
    {
        "plc_id": "pump-plc-01",
        "vendor": "openplc",
        "model": "soft-plc",
        "ip": "10.0.20.11",
        "criticality": 4,
        "parameters": ["PumpSpeed"],
    },
    {
        "plc_id": "valve-plc-01",
        "vendor": "openplc",
        "model": "soft-plc",
        "ip": "10.0.20.12",
        "criticality": 4,
        "parameters": ["InletValve", "OutletValve"],
    },
]

GRAPH_EDGES = [
    ("pump-plc-01", "controls", "Pump-1"),
    ("Pump-1", "affects", "water-tank"),
    ("valve-plc-01", "controls", "Valve-1"),
    ("Valve-1", "affects", "water-tank"),
    ("water-tank", "measured_by", "LevelSensor"),
    ("LevelSensor", "consumed_by", "tank-plc-01"),
    ("water-tank", "measured_by", "TempSensor"),
    ("TempSensor", "consumed_by", "tank-plc-01"),
]


@dataclass
class PlantCatalog:
    state_model: dict = field(default_factory=lambda: WATER_TANK_STATE_MODEL)
    global_bounds: dict = field(default_factory=lambda: dict(GLOBAL_BOUNDS))
    dependency_rules: list = field(default_factory=lambda: list(DEPENDENCY_RULES))
    cross_plc_rules: list = field(default_factory=lambda: list(CROSS_PLC_RULES))
    temporal_rules: list = field(default_factory=lambda: list(TEMPORAL_RULES))
    risk_weights: dict = field(default_factory=lambda: dict(RISK_WEIGHTS))
    approval_required: set[str] = field(default_factory=lambda: set(APPROVAL_REQUIRED_PARAMETERS))
    authorized_identities: dict[str, str] = field(default_factory=lambda: dict(AUTHORIZED_IDENTITIES))
    authorized_hosts: set[str] = field(default_factory=lambda: set(AUTHORIZED_HOSTS))
    plcs: list = field(default_factory=lambda: list(PLCS))
    graph_edges: list = field(default_factory=lambda: list(GRAPH_EDGES))
    versions: dict[str, str] = field(
        default_factory=lambda: {
            "policy_version": "1.0.0",
            "state_model_version": "1.0.0",
            "safety_model_version": "1.0.0",
            "dependency_graph_version": "1.0.0",
            "process_model_version": "1.0.0",
            "experiment_config_version": "1.0.0",
            "framework_version": "0.1.0",
        }
    )


DEFAULT_CATALOG = PlantCatalog()
