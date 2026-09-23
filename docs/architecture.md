# Architecture

See the canonical plan: [PLC_CHANGE_ASSURANCE_MASTER_PLAN.md](PLC_CHANGE_ASSURANCE_MASTER_PLAN.md).

## Module responsibilities

| Module | Path | Responsibility |
| --- | --- | --- |
| Domain | `backend/app/domain` | Canonical change, decision, approval types |
| Catalog | `backend/app/catalog.py` | Commissioned plant, FSM, rules, risk weights |
| Engines | `backend/app/engines` | Independent checks + fusion + baselines |
| Adapters | `backend/app/adapters` | Modbus decode, digital twin |
| Persistence | `backend/app/persistence` | SQLAlchemy models, sessions |
| API | `backend/app/api` | REST for operators and researchers |
| Runtime | `backend/app/services/runtime.py` | Interceptor, seed, audit, metrics |
| Simulator | `simulator/water_tank.py` | Deterministic physics + FSM |
| Experiments | `experiments/` | Labeled harness, never inside detectors |
| UI | `frontend/` | OT-facing views; no policy logic |

## Data flow

```
Raw Modbus / REST write
    → ProtocolAdapter
    → ChangeRequest
    → EvaluationContext (no experiment labels)
    → Fast-path engines
    → DecisionEngine
    → Audit + optional apply (mode-dependent)
    → Deep path: DigitalTwinAdapter.simulate()
```

## Decision pipeline

Authentication → Authorization → Provenance → Value → State → Transition → Temporal → Dependency → Cross-PLC → Physical safety → Risk score → Fused decision.

`hard_violation=true` never becomes `ALLOW` because the blended score is low.
