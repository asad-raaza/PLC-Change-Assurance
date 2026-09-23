# Experiment Plan

## Objective

Produce reproducible, labeled evidence for RQ1–RQ7 and H1–H5 using the water-tank testbed. RQ8–RQ10 are scoped as design/limitation studies in the first prototype (interfaces exist; additional vendors are not claimed).

## Environment

- Local Docker Compose or in-process simulator
- OpenPLC-compatible Modbus/TCP semantics
- Deterministic physics seed
- Detectors isolated from ground-truth labels

## Methods compared

1. Static allowlist / range checker
2. Global invariant checker
3. FSM / state-aware checker
4. FSM + temporal rules
5. FSM + temporal + dependency rules
6. Full intent-aware cyber-physical change assurance

## Factors

`Method × Attack type × Process state × PLC × Protocol × Noise × Attack speed × Attacker privilege`

Initial protocol factor is `modbus_tcp` only. Additional protocols are interface-ready, not evaluated.

## Scenario families

- Normal: authorized setpoint, normal transition, approved maintenance, operator adjustment
- Unauthorized: unknown host, unknown identity, expired approval, wrong PLC, wrong parameter
- Safety: out of range, wrong state, unsafe combination, unsafe rate, invalid transition
- Stealth: slow ramp, in-range values, time-shifted write, replay, sequence manipulation
- Multi-variable: pump + valve; temperature + pressure; alarm threshold + process write
- Multi-PLC: PLC-A vs PLC-B conflict; coordinated writes
- Compromised trusted host: valid workstation, valid user, invalid operation

## Metrics

Detection: TP, FP, TN, FN, precision, recall, F1, FPR

Operational: detection latency, decision latency, unsafe changes prevented, safe changes allowed, legitimate changes incorrectly blocked, max physical deviation before detection, time to recovery, CPU, memory, network overhead

OT usability constraint: a high-FPR detector is treated as a failed operational result even if recall is high.

## Procedure

1. Seed plant, policies, users, approvals (`python -m scripts.seed`).
2. Start simulator at a known state.
3. Run `python -m experiments.runner`.
4. Export CSV/JSON with predictions **and** labels in separate columns.
5. Generate report (`python -m experiments.report`).

## Reproducibility

- Fixed random seed in experiment configuration
- Policy, state-model, safety-model, and framework versions recorded on every decision
- No detector reads `label` or `attack_type` from the evaluation context
