# Deployment

This software is a **laboratory research testbed**.

## Local

See the root README. Default database is SQLite under `data/assurance.db`.

## Docker Compose

`docker compose up --build` starts the API (embedded simulator) and the nginx UI.

PostgreSQL can be substituted by setting `DATABASE_URL=postgresql+psycopg2://...`.

## Modes

| Variable | Meaning |
| --- | --- |
| `OPERATING_MODE=passive` | Default. Observe, never prevent. |
| `OPERATING_MODE=advisory` | Recommend BLOCK/HOLD but still apply writes. |
| `OPERATING_MODE=enforcement` + `LAB_MODE=true` | Inline PEP in a controlled lab only. |

`FAIL_SAFE_MODE` is `fail_open`, `fail_closed`, or `fail_to_advisory`.
