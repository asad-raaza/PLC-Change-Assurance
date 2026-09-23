# PLC Change Assurance Framework

Research platform for a **Cyber-Physical PLC Change Assurance Gateway**.

The system does not ask “did a PLC value change?” It asks:

> Should this PLC change be allowed at this particular moment?

A requested write is evaluated for identity, authorization, approved intent, process state, transition legality, temporal behavior, parameter dependencies, cross-PLC consistency, and predicted physical safety. Hard safety violations cannot be overridden by a low risk score.

This repository is a **local / laboratory** testbed. Do not run it against production ICS or any OT network you do not own.

## What you get

- Explainable decision engine with comparable research baselines
- Water-tank process simulator (OpenPLC-compatible Modbus semantics)
- YAML policies, approved-change manifests, FSM, temporal and relational rules
- Advisory recovery that does **not** assume `previous_value` is safe
- React operator/researcher UI
- Automated scenario runner and experiment export

Enforcement mode is **disabled** unless `LAB_MODE=true` and `OPERATING_MODE=enforcement`.

## Quick start (local)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "backend;."
python -m scripts.seed
python -m uvicorn app.main:app --app-dir backend --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Lab UI: `http://localhost:5173`

Demo identities (local lab only):

| User | Password | Role |
| --- | --- | --- |
| engineer-a | lab-engineer-change-me | engineer |
| admin | lab-admin-change-me | admin |
| researcher | lab-researcher-change-me | researcher |

## One-command Docker lab

```powershell
docker compose up --build
```

API: `http://localhost:8000` · UI: `http://localhost:8080`

## Demonstrate the prototype (section 53)

```powershell
$env:PYTHONPATH = "backend;."
python scripts/run_demo.py
python scripts/run_experiments.py
pytest
```

Expected story:

1. Process in `IDLE`
2. Engineer `TankLevel_SP` 50 → 60 with `CHG-1234` → **ALLOW**
3. Attacker 60 → 95 (globally in range, illegal in `IDLE`) → **BLOCK** with reasons
4. Slow ramp 60, 63, 66, 69, 72 → **BLOCK** (temporal rate)
5. Pump high while inlet valve low → **BLOCK** (dependency / cross-PLC)

## Documentation

Start at [docs/PLC_CHANGE_ASSURANCE_MASTER_PLAN.md](docs/PLC_CHANGE_ASSURANCE_MASTER_PLAN.md).

Also see `research/` for the problem statement, threat model, questions, and novelty boundaries.

## Safety restrictions

- No production equipment
- No external OT scanning
- No undocumented proprietary PLC attacks
- Automatic recovery is advisory / simulation only
- Machine learning is not a required detector and cannot override hard constraints
