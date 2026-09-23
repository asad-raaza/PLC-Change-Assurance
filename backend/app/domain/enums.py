"""Shared enumerations. Values are stable for audit and experiment export."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover
        return self.value


class OperatingMode(StrEnum):
    PASSIVE = "passive"
    ADVISORY = "advisory"
    ENFORCEMENT = "enforcement"


class FailSafeMode(StrEnum):
    FAIL_OPEN = "fail_open"
    FAIL_CLOSED = "fail_closed"
    FAIL_TO_ADVISORY = "fail_to_advisory"


class RiskPolicyMode(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    MONITOR_ONLY = "monitor-only"
    CUSTOM = "custom"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    ALLOW_WITH_ALERT = "ALLOW_WITH_ALERT"
    HOLD = "HOLD"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"
    SAFE_SUBSTITUTE = "SAFE_SUBSTITUTE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class CheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"


class ChangeClass(StrEnum):
    PARAMETER_WRITE = "parameter_write"
    SETPOINT_CHANGE = "setpoint_change"
    TIMER_MODIFICATION = "timer_modification"
    COUNTER_MODIFICATION = "counter_modification"
    PID_MODIFICATION = "pid_modification"
    THRESHOLD_MODIFICATION = "threshold_modification"
    ALARM_CONFIGURATION = "alarm_configuration"
    MODE_CHANGE = "mode_change"
    LOGIC_CHANGE = "logic_change"
    FIRMWARE_CONFIGURATION = "firmware_configuration"
    SAFETY_INTERLOCK = "safety_interlock"
    NETWORK_CONFIGURATION = "network_configuration"


class ProcessStateName(StrEnum):
    OFF = "OFF"
    STARTING = "STARTING"
    IDLE = "IDLE"
    FILLING = "FILLING"
    HEATING = "HEATING"
    PROCESSING = "PROCESSING"
    DRAINING = "DRAINING"
    COMPLETE = "COMPLETE"
    EMERGENCY = "EMERGENCY"
    MAINTENANCE = "MAINTENANCE"


class UserRole(StrEnum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    OPERATOR = "operator"
    ANALYST = "analyst"
    AUDITOR = "auditor"
    RESEARCHER = "researcher"


class CapabilityStatus(StrEnum):
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    SIMULATED = "simulated"
    PLANNED = "planned"
    UNSUPPORTED = "unsupported"


class AlgorithmName(StrEnum):
    STATIC_RANGE = "static_range"
    GLOBAL_INVARIANT = "global_invariant"
    FSM = "fsm"
    FSM_TEMPORAL = "fsm_temporal"
    FSM_TEMPORAL_DEPENDENCY = "fsm_temporal_dependency"
    FULL_FRAMEWORK = "full_framework"
