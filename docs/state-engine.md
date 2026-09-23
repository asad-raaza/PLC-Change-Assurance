# State engine

The water-tank FSM is loaded from `WATER_TANK_STATE_MODEL` (database copy: `state_models.definition`).

States: `OFF`, `STARTING`, `IDLE`, `FILLING`, `HEATING`, `PROCESSING`, `DRAINING`, `COMPLETE`, `EMERGENCY`, `MAINTENANCE`.

Each state may define parameter bounds, min/max duration, and entry/exit conditions. Transitions have optional guards, e.g. `HEATING → PROCESSING` only if `Temperature >= 80` and `Pressure <= 60`.

`StateExtractor` is a planned interface for deriving states from IEC 61131-3, historian data, or sensor patterns. It is **not** implemented and must not be claimed as implemented.
