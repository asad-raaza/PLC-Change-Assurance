# Policy model

Policies are human-readable YAML validated before activation (`backend/app/policies/parser.py`).

```yaml
policy:
  name: heating-safety
  applies_to:
    plc: tank-plc-01
  when:
    process_state: HEATING
  rules:
    - Temperature_SP <= 85
    - if:
        PumpSpeed: "> 60"
      then:
        InletValve: "> 40"
  change_requirements:
    approval_required: true
```

Relational and temporal constraints used by the first prototype also live in `backend/app/catalog.py` so they are versioned with the commissioned plant rather than scattered as magic numbers.

Risk weights are catalogued in `RISK_WEIGHTS`. Policy modes: `conservative`, `balanced`, `monitor-only`, `custom`.
