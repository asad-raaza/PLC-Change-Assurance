# Experiments

```powershell
python scripts/run_experiments.py
```

Outputs:

- `experiments/results/latest.json`
- `experiments/results/latest.csv`
- `experiments/results/REPORT.md`

Methods compared: static range, global invariant, FSM, FSM+temporal, FSM+temporal+dependency, full framework.

Labels are joined only in the harness after decisions are stored. Detectors never receive `label` or `attack_type`.
