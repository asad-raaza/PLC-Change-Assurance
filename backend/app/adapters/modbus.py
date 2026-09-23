"""Modbus/TCP write decoding → canonical ChangeRequest.

Packet decoding is intentionally isolated from decision logic.
"""

from __future__ import annotations

from app.domain.enums import ChangeClass
from app.domain.models import ChangeRequest

# OpenPLC-style holding-register map used by the water-tank lab.
REGISTER_MAP = {
    0: ("TankLevel_SP", "tank-plc-01", ChangeClass.SETPOINT_CHANGE),
    1: ("Temperature_SP", "tank-plc-01", ChangeClass.SETPOINT_CHANGE),
    2: ("Heater", "tank-plc-01", ChangeClass.PARAMETER_WRITE),
    3: ("Pressure", "tank-plc-01", ChangeClass.PARAMETER_WRITE),
    4: ("AlarmHighLevel", "tank-plc-01", ChangeClass.THRESHOLD_MODIFICATION),
    5: ("PID_Kp", "tank-plc-01", ChangeClass.PID_MODIFICATION),
    6: ("Timer_Fill_ms", "tank-plc-01", ChangeClass.TIMER_MODIFICATION),
    10: ("PumpSpeed", "pump-plc-01", ChangeClass.SETPOINT_CHANGE),
    20: ("InletValve", "valve-plc-01", ChangeClass.PARAMETER_WRITE),
    21: ("OutletValve", "valve-plc-01", ChangeClass.PARAMETER_WRITE),
}

FUNCTION_CODES = {
    5: "write_single_coil",
    6: "write_single_register",
    15: "write_multiple_coils",
    16: "write_multiple_registers",
}


class ModbusTCPAdapter:
    """Converts function-code writes into ChangeRequest objects."""

    def to_change_request(self, raw: bytes | dict) -> ChangeRequest:
        if isinstance(raw, dict):
            return self._from_dict(raw)
        return self._from_pdu(raw)

    def _from_dict(self, raw: dict) -> ChangeRequest:
        address = int(raw.get("address", raw.get("register", 0)))
        name, plc_id, change_class = REGISTER_MAP.get(
            address, (raw.get("parameter", f"HR{address}"), raw.get("plc_id", "tank-plc-01"), ChangeClass.PARAMETER_WRITE)
        )
        return ChangeRequest(
            source_identity=raw.get("source_identity", "unknown"),
            source_host=raw.get("source_host", "unknown"),
            source_ip=raw.get("source_ip", ""),
            protocol="modbus_tcp",
            plc_id=raw.get("plc_id", plc_id),
            parameter=raw.get("parameter", name),
            parameter_type=raw.get("parameter_type", "holding_register"),
            previous_value=raw.get("previous_value"),
            requested_value=raw.get("requested_value", raw.get("value")),
            current_process_state=raw.get("current_process_state", "IDLE"),
            requested_operation=FUNCTION_CODES.get(int(raw.get("function_code", 6)), "write_register"),
            change_class=change_class,
            change_ticket=raw.get("change_ticket"),
            approved_change_id=raw.get("approved_change_id"),
            session_id=raw.get("session_id"),
            metadata={"address": address, "function_code": raw.get("function_code", 6)},
        )

    def _from_pdu(self, pdu: bytes) -> ChangeRequest:
        if len(pdu) < 5:
            raise ValueError("Modbus PDU too short")
        function_code = pdu[0]
        address = int.from_bytes(pdu[1:3], "big")
        if function_code in {6, 5}:
            value = int.from_bytes(pdu[3:5], "big")
        elif function_code == 16 and len(pdu) >= 7:
            value = int.from_bytes(pdu[6:8], "big")
        else:
            value = 0
        name, plc_id, change_class = REGISTER_MAP.get(
            address, (f"HR{address}", "tank-plc-01", ChangeClass.PARAMETER_WRITE)
        )
        return ChangeRequest(
            protocol="modbus_tcp",
            plc_id=plc_id,
            parameter=name,
            requested_value=value,
            requested_operation=FUNCTION_CODES.get(function_code, f"fc_{function_code}"),
            change_class=change_class,
            metadata={"address": address, "function_code": function_code, "raw_hex": pdu.hex()},
        )
