# Limitations

- First protocol is Modbus/TCP semantics. Siemens, CIP, OPC UA, DNP3, IEC-104 are interfaces only.
- OpenPLC hardware is optional; the in-process tank is the reproducible default.
- Logic-change interception is **simulated**.
- Digital twin is a deterministic mock, not a validated high-fidelity model.
- Recovery is advisory and never autonomous on a live process.
- Automatic state extraction from PLC source is not implemented.
- A plant without a state model and approvals degrades toward the static baseline (RQ9).
- Sensor integrity is only partially modeled (Scenario L is not fully solved).
- No claim that hypotheses are proven until independent runs are reviewed.
