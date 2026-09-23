# Related Work Positioning

This is a positioning document, not a complete literature review. It states what existing work already covers and where this framework sits.

## Existing approaches that already solve part of the problem

### Access control and engineering software

Vendor IDEs, factory talk / TIA Portal style workflows, and plant change-management systems restrict *who* may download or write. They do not jointly evaluate whether a write is physically appropriate *now*, nor do they compare layers experimentally.

### PLC interlocks and SIS

Control programs and safety instrumented systems enforce some unsafe combinations and trips. They live *inside* the same controllers an attacker may reprogram (Scenario I) and are not a plant-wide, explainable, pre-write gateway across identity, intent, and cross-PLC state.

### Network IDS / ICS anomaly detection

Protocol parsers, allowlists, and unsupervised models can flag unusual destinations, function codes, or value jumps. They struggle with:

- valid credentials and valid function codes
- in-range slow ramps
- state-conditioned legality
- approved maintenance that looks anomalous
- explainable hard-constraint decisions

### Digital twins and what-if simulators

Twins can predict trajectories. They are rarely an inline change-assurance PEP with provenance, RBAC, and comparable baselines.

### Formal methods / model checking of PLC logic

Useful for verifying a program, not for authorizing a live write from a compromised workstation.

## What this framework does differently

It treats a PLC write as a **cyber-physical change request** and evaluates it through independent, swappable engines before (or, in passive mode, immediately after) the write. Results are stored per algorithm so a paper can report:

```
static_range: ALLOW
fsm: ALLOW
temporal: BLOCK
full_framework: BLOCK
```

on the same request.

## Mapping to research questions

| Existing class | Typically answers | Does not answer |
| --- | --- | --- |
| Range / allowlist | Is the value globally typical? | Is it legal in this state, at this rate, with these peers? |
| Network IDS | Is the packet unusual? | Is the process consequence safe? |
| Ticket system | Was a change requested? | Was *this* value, PLC, host, and moment approved? |
| Interlock | Is the current I/O combination permitted? | Was the write authorized and non-replayed? |
| Twin | What might happen? | Should we allow it given identity and policy? |

## Honest limitation

If a plant has no state model, no dependency knowledge, and no approved-change process, the framework degrades toward the static baseline. RQ9 exists to measure that engineering cost instead of hiding it.
