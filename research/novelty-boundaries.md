# Novelty Boundaries

Do not claim a feature is novel merely because it was implemented.

## Engineering contribution (necessary, not automatically novel)

- Modular gateway architecture with vendor/protocol adapters
- Canonical change-request model
- Versioned policies, models, and audit correlation
- Dockerized water-tank testbed and scenario runner
- Explainable decision records and researcher-facing comparison API
- RBAC, migrations, and fail-safe configuration

These are required to make the research measurable. They are not, by themselves, new science.

## Previously known techniques

- Static allowlists and analog range limits
- Role-based access control
- Industrial change-management tickets
- Finite-state machine process models
- Interlocks and permissives inside PLC logic
- Network IDS / protocol anomaly detection
- Digital twins used for operations and what-if analysis
- Temporal logic and rate-of-change alarms in process historians

## New combination under study

The research object is the **joint, pre-execution evaluation** of a PLC write against:

identity + authorization + approved intent + current process state + transition legality + temporal constraints + multi-variable dependencies + cross-PLC consistency + optional predicted physics + recovery feasibility

with hard constraints that cannot be overridden by a blended risk score, and with each layer comparable as an experimental baseline.

That combination — not “we wrote a range check” — is the claim to be evaluated.

## What we are not claiming as novel

- Detecting that a Modbus write occurred
- Hashing passwords
- Drawing an FSM
- Blocking values outside `[min, max]`
- Using Docker or FastAPI
- Any ML accuracy number (ML is not a required detector)

## Research contribution candidates (to be evidenced, not asserted)

1. Intent-aware change validation that still works when credentials and protocols are legitimate.
2. Quantified lift of state-aware and temporal/dependency layers over static baselines.
3. Cross-PLC conflict detection using an explicit plant graph.
4. Pre-execution physics prediction as an advisory layer that cannot silently override hard rules.
5. Recovery recommendations that do **not** assume `previous_value == safe_value`.
6. A reproducible experiment matrix (method × attack × state × privilege × speed).

## Documentation rule

Every research-facing component must state:

- the problem it solves
- the baseline it should be compared against
- the experiment that would validate it
