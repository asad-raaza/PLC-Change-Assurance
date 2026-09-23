# Data model

Operational truth is stored in SQL (SQLite default, PostgreSQL via `DATABASE_URL`). YAML/JSON are fixtures and policy source text.

## Principal tables

`users`, `plants`, `areas`, `plcs`, `parameters`, `sensors`, `actuators`, `state_models`, `policies`, `model_versions`, `approved_changes`, `change_requests`, `decision_results`, `algorithm_results`, `audit_events`, `incidents`, `recovery_actions`, `observations`, `baseline_windows`, `experiment_runs`, `experiment_events`, `cross_plc_dependencies`.

## Integrity rules

- Approvals are consumed by setting `consumed` and recording `consumed_by_request`; history is not rewritten to hide reuse.
- Audit events are insert-only.
- Every decision stores policy / state / safety / graph / framework versions.
- Experiment labels live in `experiment_events`, not in `change_requests` consumed by engines.

Incomplete asset fields are nullable. Engines return `SKIP` when required data is missing.
