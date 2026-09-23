# Experiment report

Generated: 2026-09-21T00:53:34.633228+00:00
Seed: 42
Framework: 0.1.0

Hypotheses are not marked proven by this report; it records evidence only.

## Method metrics

| Method | TP | FP | TN | FN | Precision | Recall | F1 | FPR | Latency ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| static_range | 1 | 0 | 3 | 13 | 1.0 | 0.0714 | 0.1333 | 0.0 | 0.045 |
| global_invariant | 1 | 0 | 3 | 13 | 1.0 | 0.0714 | 0.1333 | 0.0 | 0.045 |
| fsm | 6 | 0 | 3 | 8 | 1.0 | 0.4286 | 0.6 | 0.0 | 0.045 |
| fsm_temporal | 7 | 0 | 3 | 7 | 1.0 | 0.5 | 0.6667 | 0.0 | 0.045 |
| fsm_temporal_dependency | 7 | 0 | 3 | 7 | 1.0 | 0.5 | 0.6667 | 0.0 | 0.045 |
| full_framework | 14 | 0 | 3 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.045 |
| full_framework_named | 14 | 0 | 3 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.045 |

## Scenario outcomes

| Scenario | Label | Full | Expected | Static | FSM | Temporal |
| --- | --- | --- | --- | --- | --- | --- |
| authorized_setpoint | benign | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| approved_maintenance | benign | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| operator_adjustment | benign | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| unknown_workstation | attack | BLOCK | BLOCK | ALLOW | ALLOW | ALLOW |
| unauthorized_identity | attack | BLOCK | BLOCK | ALLOW | ALLOW | ALLOW |
| expired_approval | attack | HOLD | HOLD | ALLOW | ALLOW | ALLOW |
| wrong_plc_approval | attack | REQUIRE_APPROVAL | REQUIRE_APPROVAL | ALLOW | ALLOW | ALLOW |
| wrong_parameter | attack | REQUIRE_APPROVAL | REQUIRE_APPROVAL | ALLOW | ALLOW | ALLOW |
| out_of_range | attack | BLOCK | BLOCK | BLOCK | BLOCK | BLOCK |
| wrong_state | attack | BLOCK | BLOCK | ALLOW | BLOCK | BLOCK |
| unsafe_combination | attack | BLOCK | BLOCK | ALLOW | BLOCK | BLOCK |
| slow_ramp | attack | BLOCK | BLOCK | ALLOW | ALLOW | BLOCK |
| invalid_transition | attack | BLOCK | BLOCK | ALLOW | BLOCK | BLOCK |
| replay | attack | BLOCK | BLOCK | ALLOW | ALLOW | ALLOW |
| cross_plc_conflict | attack | BLOCK | BLOCK | ALLOW | BLOCK | BLOCK |
| compromised_host_no_ticket | attack | REQUIRE_APPROVAL | REQUIRE_APPROVAL | ALLOW | ALLOW | ALLOW |
| temp_and_pressure | attack | BLOCK | BLOCK | ALLOW | BLOCK | BLOCK |
