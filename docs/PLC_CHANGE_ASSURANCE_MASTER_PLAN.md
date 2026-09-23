# PLC Change Assurance — Canonical Master Plan

This is the implementation plan for a research-grade **Cyber-Physical PLC Change Assurance Gateway**. It is written after inspecting the repository (empty git project at `D:\Dakota State University\PLC Research\PLC`) and resolving design questions that can be settled without waiting for further input.

---

## 1. Current repository assessment

**Inspection date:** 2026-09-20

| Finding | Detail |
| --- | --- |
| Git repository | Present |
| Application code | None |
| Docs / research artifacts | None prior to this plan |
| Docker / testbed | None |
| PLC vendor bindings | None |
| Implied existing architecture | None — greenfield |

Because there is no prior architecture to preserve, the structure in prompt §51 is adopted at the repository root (the workspace *is* the project).

Questions resolved from the repository itself:

- No existing language, framework, or schema to extend.
- No production credentials or plant models to migrate.
- No reason to support a legacy API.
- Safe to choose a research-friendly stack and SQLite-default persistence so `pytest` and a one-command demo do not require a local PostgreSQL install.

---

## 2. Proposed system architecture

### Stack justification

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Python 3.11, FastAPI, Pydantic v2 | Typed research APIs, fast iteration, pytest ecosystem |
| ORM / DB | SQLAlchemy 2 + Alembic | PostgreSQL-ready; SQLite default for local/repro tests |
| Policy | YAML + schema validation | Human-readable for OT engineers; not dozens of tiny files |
| Frontend | React + TypeScript + Vite | Required operator/researcher views without embedding logic in UI |
| Realtime | REST + 2 s polling (SSE-ready) | Simple, reliable in lab; WebSocket not required for prototype |
| Protocol | Modbus/TCP adapter + canonical events | OpenPLC-reproducible; no proprietary reverse engineering |
| PLC sim | Deterministic water-tank + pymodbus optional server | Works without owning hardware; OpenPLC optional in Compose |
| Auth | bcrypt + JWT + RBAC | No plaintext passwords; lab demo users only |
| ML | **Not a dependency** | Hard safety stays deterministic and explainable |

PostgreSQL is supported via `DATABASE_URL`. Default is SQLite (`data/assurance.db`) so a new researcher can run the suite without extra services.

### Module map

```
Engineer / HMI / attacker / experiment runner
                 |
                 v
        ProtocolAdapter  (Modbus/TCP → CanonicalChangeEvent)
                 |
                 v
           ChangeInterceptor
                 |
                 v
        Evaluation Pipeline (fast path)
        --------------------
        Authn → Authz → Provenance → Range/Invariant
        → State/Transition → Temporal → Dependency
        → Cross-PLC → Hard safety
                 |
                 +--> DecisionEngine (hard constraints override score)
                 |
                 +--> AuditLogger (append-oriented)
                 |
        Deep path (does not block fast decision)
        ---------------------------------------
        DigitalTwinAdapter.simulate()
        Historical / baseline features
                 |
                 v
        RecoveryEngine (advisory / simulation only)
```

### Operating modes

| Mode | Default | Behavior |
| --- | --- | --- |
| `passive` | **default** | Analyze, alert, log; never prevent PLC communication |
| `advisory` | optional | ALLOW / WARN / HOLD / BLOCK-RECOMMENDED; writes still applied |
| `enforcement` | **disabled** | Inline PEP. Requires `LAB_MODE=true` **and** explicit mode |

Enforcement outcomes: `ALLOW`, `ALLOW_WITH_ALERT`, `REQUIRE_APPROVAL`, `HOLD`, `BLOCK`, `SAFE_SUBSTITUTE`, `INITIATE_RECOVERY` (recovery initiation is still advisory-only in Phase 9).

### Fast path vs deep path

Deterministic engines target millisecond latency. Twin simulation and historical analysis run as deep-path jobs and cannot delay a hard BLOCK/ALLOW that is already decided.

---

## 3. Threat model

Canonical threat model: [`research/threat-model.md`](../research/threat-model.md) and [`docs/threat-model.md`](threat-model.md).

Scenarios A–L are in scope for design. Engineering workstations and credentials are **not** trusted. Sensors are partially trusted (Scenario L).

---

## 4. Domain / data model

Incomplete asset fields are allowed. Missing data yields `SKIP` on the dependent check, never a fabricated PASS.

### Asset hierarchy

```
Plant
 └── Area
      ├── PLC
      ├── HMI
      ├── Sensors
      ├── Actuators
      └── Process units
```

PLC fields: `plc_id`, vendor, model, firmware, IP, protocol, program version, operating mode, tags, parameters, timers, counters, I/O and internal variables, associated sensors/actuators, parent process, peers, safety classification, criticality.

### Change request (canonical)

See API contract below. Change classes: parameter write, setpoint, timer, counter, PID, threshold, alarm, mode, logic, firmware/config, safety/interlock, network config.

### Decision result

Explainable: `decision`, `risk_score`, `hard_violation`, `reasons[]`, `checks{}`, contributing factors, model versions.

---

## 5. Component interfaces

All engines implement small protocols so algorithms are swappable.

| Interface | Responsibility |
| --- | --- |
| `PLCAdapter` | Read/write PLC-normalized values |
| `ProtocolAdapter` | Bytes/function-codes → `ChangeRequest` |
| `StateEstimator` / `StateEngine` | Current state, legal transitions, state-specific bounds |
| `StateExtractor` | Future auto-derivation from logic/historian (planned) |
| `ChangeInterceptor` | Ingress + mode-aware apply/deny |
| `AuthorizationProvider` | Identity, host, role, operation |
| `PolicyEngine` | Parsed, versioned YAML policies |
| `InvariantEngine` | Global invariants |
| `TemporalRuleEngine` | Rate, windows, sequences, expiry |
| `DependencyEngine` | Relational / mutex / required combinations |
| `CrossPLCValidator` | Plant graph conflicts |
| `SafetyModel` / `PhysicsModel` | Deterministic safety predicates |
| `DigitalTwinAdapter` | `simulate(current_state, proposed_change, horizon)` |
| `DecisionEngine` | Fuse checks; hard override of scores |
| `RecoveryEngine` | Advisory safe targets; never assumes previous==safe |
| `AuditLogger` | Append-only correlation chain |
| `SafetyAlgorithm` | Research plugin: `evaluate(context)` |

Baseline algorithms implement `SafetyAlgorithm` so the same request is scored by all methods independently.

---

## 6. Database model

Operational truth lives in SQL tables. YAML/JSON are fixtures and policy source, then validated and stored.

**Entities:** plants, areas, assets, plcs, sensors, actuators, process_units, parameters, state_models, states, state_transitions, safety_constraints, temporal_constraints, parameter_dependencies, cross_plc_dependencies, approved_changes, change_requests, decision_results, algorithm_results, observations, process_measurements, incidents, recovery_actions, users, roles, policies, model_versions, audit_events, experiment_runs, experiment_events, baseline_windows.

Approvals and audit rows are not updated in place to rewrite history. Approvals are consumed by inserting a consumption record.

Schema version is explicit (`alembic_version` + `model_versions`).

---

## 7. API design

All mutating routes require authentication. RBAC is enforced per route.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/login` | JWT |
| POST | `/api/change-requests/evaluate` | Evaluate without requiring apply |
| POST | `/api/change-requests` | Ingest + evaluate (+ apply per mode) |
| GET | `/api/change-requests` | Live change list |
| GET | `/api/change-requests/{id}` | Detail + reasons |
| GET | `/api/plcs` | Asset list |
| GET | `/api/plcs/{id}` | PLC detail |
| GET | `/api/plcs/{id}/state` | Current FSM state |
| GET | `/api/plcs/{id}/parameters` | Parameters |
| GET | `/api/state-models` | List |
| POST | `/api/state-models` | Create (admin) |
| PUT | `/api/state-models/{id}` | New version |
| GET | `/api/policies` | List |
| POST | `/api/policies` | Validate + store |
| GET | `/api/change-approvals` | Manifests |
| POST | `/api/change-approvals` | Create |
| GET | `/api/incidents` | Incidents |
| POST | `/api/simulations/evaluate-change` | Deep-path twin |
| POST | `/api/recovery/evaluate` | Advisory recovery |
| GET | `/api/overview` | Dashboard aggregates |
| GET | `/api/research/compare` | Per-algorithm decisions |
| GET | `/api/metrics` | Counters + latencies |
| GET | `/api/audit` | Audit query (auditor+) |

---

## 8. Testbed architecture

```
+------------------+     +----------------------+     +------------------+
| engineering      |     | assurance API        |     | water-tank       |
| + attack clients | --> | + Modbus adapter     | --> | physics + FSM    |
+------------------+     +----------------------+     +------------------+
         |                          |                          |
         |                          v                          v
         |                   PostgreSQL/SQLite              pymodbus
         |                          |                       (optional)
         v                          v
   experiment runner          React UI
```

Simulated process: tank level, pump, inlet/outlet valves, pressure, flow, temperature.

States: `OFF`, `STARTING`, `IDLE`, `FILLING`, `HEATING`, `PROCESSING`, `DRAINING`, `COMPLETE`, `EMERGENCY`.

Physics are deterministic closed-form updates (no hidden stochasticity unless an experiment sets `noise_level`).

---

## 9. Experiment architecture

`experiments/` owns scenarios, runner, metrics, and export. Ground-truth labels live only in the harness.

Comparison matrix writes one row per `(method, scenario, seed)`.

---

## 10. Phased implementation plan and gates

| Phase | Gate to mark COMPLETE |
| --- | --- |
| 0 Research foundation | Problem, threat, RQ, novelty, experiment plan exist |
| 1 Domain + DB | Models, migrations/create, unit tests |
| 2 Simulator | Deterministic tank + seed + startup docs |
| 3 Observation | Modbus → canonical change, audit, passive |
| 4 Policy | Range, authz, approvals, explainable decisions |
| 5 FSM | Configurable states/guards, invalid transitions |
| 6 Temporal + relational | Rate, windows, dependencies |
| 7 Multi-PLC | Graph + conflict tests |
| 8 Safety sim | SafetyModel + mock twin |
| 9 Recovery | Advisory only; previous≠safe |
| 10 Enforcement | Lab-mode flag; fail-safe; default off |
| 11 Experiments | Scenario runner, metrics, export |

A phase is not complete because files exist. It is complete when tests for that phase pass and the acceptance block is written.

---

## 11. Major technical risks

- Modbus interception vs. clients that bypass the gateway (mitigate: lab topology + honest capability status).
- SQLite concurrency under Compose load (mitigate: WAL; Postgres optional).
- Twin error treated as truth (mitigate: confidence + never override hard rules).
- Policy language ambiguity (mitigate: schema validation before activation).

---

## 12. Research risks

- Over-claiming novelty for composition of known parts.
- Baseline poisoning if learning is auto-enforced (it is not).
- High FPR making the system operationally unusable.
- Incomplete engineering knowledge (RQ9) silently assumed away.

---

## 13. Security risks

- Gateway compromise is a plant-wide bypass.
- Demo passwords leaking into a non-lab deploy (documented; `.env` gitignored).
- Fake approvals and audit deletion.
- Enforcement accidentally enabled outside lab.

---

## 14. Safety risks

- Fail-open on a safety-critical write.
- Automatic recovery to a no-longer-safe previous value.
- Sensor spoofing (Scenario L) satisfying a guard.

Mitigations: configurable fail mode; recovery is advisory; sensors are partial trust; enforcement off by default.

---

## 15. Assumptions

- First process is a single water-tank cell plus a second peer PLC for cross-PLC demos.
- Researchers will not point this software at production ICS.
- Demo identities (`engineer-a`, `eng-ws-02`) are lab fixtures.
- OpenPLC hardware is optional; in-process simulation is sufficient for Phase 2–11 gates.

---

## 16. Questions resolved from the repository

All language, persistence, UI, and protocol questions were open. Resolved in §2.

---

## 17. Items that truly require a later design decision

These are **not** blockers for the prototype:

1. Whether a specific plant uses fail-open vs fail-closed on gateway crash.
2. Which real vendor adapter to implement after OpenPLC (interface only now).
3. Whether a validated twin may be promoted from advisory to hard constraint.
4. Dual-control policy for emergency bypass in a real control room.

---

## Decision pipeline

```
ChangeRequest
    → AuthenticationResult
    → AuthorizationResult
    → ProvenanceResult
    → StateResult
    → TransitionResult
    → DependencyResult
    → TemporalResult
    → PhysicalSafetyResult
    → CrossPLCResult
    → RiskScore (factors, never overrides hard_violation)
    → Decision + reasons[] + version stamps
```

Hard safety / invalid transition / replay / consumed approval → cannot become ALLOW because the blended score is low.

---

## Testing strategy

- Unit tests per engine, including reasons (not only decision codes).
- Integration tests through the API.
- Negative, boundary, and failure tests (DB down → configured fail mode).
- Property test: `hard_violation=True` never yields `ALLOW`.
- Section 38 cases as named tests.
- Experiment harness uses the same engines; labels stay outside.

---

## Experiment strategy

See [`research/experiment-plan.md`](../research/experiment-plan.md). Demonstration sequence is prompt §53–§54 (Attacks 1–8).

---

## Acceptance criteria (global prototype)

The first meaningful end-to-end path must show:

1. Simulated process starts; PLC in `IDLE`.
2. Engineer `TankLevel_SP` 50 → 60 with valid identity/approval → **ALLOW**.
3. Change is auditable.
4. Attacker 60 → 95 (globally plausible, state-invalid) → **BLOCK** with reasons.
5. Slow ramp 60, 63, 66, … → **HOLD/BLOCK** via temporal rule.
6. Pump high + valve low → **BLOCK** via dependency.
7. Metrics exported for the run.

Until that path is clean, no ML and no extra vendors.
