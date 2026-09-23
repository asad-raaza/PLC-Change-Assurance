# Testing

```powershell
$env:PYTHONPATH = "backend;."
pytest
```

Coverage includes:

- Section 38 decision cases with **reason** assertions
- Unauthorized host / identity
- Wrong-state vs static baseline
- Slow ramp vs FSM-only
- Unsafe combination and cross-PLC
- Replay and expired approval
- Recovery does not treat an out-of-envelope previous value as safe
- Fail-closed path
- Enforcement requires lab mode
- API login + evaluate
- Experiment harness isolation of labels

Do not weaken assertions to obtain a green run.
