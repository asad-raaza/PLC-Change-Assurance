# Problem Statement

## The question this framework exists to answer

When somebody or something attempts to change a PLC parameter, setpoint, timer, configuration value, control variable, operating mode, or PLC logic, can we determine whether that change is authentic, authorized, expected, valid for the current process state, physically safe, consistent with other PLCs, and safe to execute?

The research problem is not:

> Did a PLC parameter change?

It is:

> Should this PLC change be allowed at this particular moment?

## Why existing approaches are insufficient

Industrial control systems already have pieces of this problem:

- HMIs and SCADA enforce some operator permissions.
- PLC programs contain interlocks and permissives.
- Safety instrumented systems (SIS) protect a subset of hazards.
- IDS / anomaly detectors look for unusual traffic or unusual values.
- Change-management systems record tickets after the fact.

None of those layers jointly answers the question above at the moment a write is attempted.

A value can be inside a global range and still be unsafe in the current process state. A write can come from a valid engineering workstation and still be a replay, a slow ramp, or a locally valid but globally unsafe coordinated change. A previously approved command can become unsafe after the physical process has moved.

## Distinctions the framework must make

| Situation | Typical detector outcome | Required outcome |
| --- | --- | --- |
| Legitimate engineer, approved value, approved window | Allow | Allow, with audit |
| Legitimate engineer, dangerous value | Often allow if in range | Block / hold, explain why |
| Compromised engineering workstation, valid credentials | Allow | Detect missing or mismatched intent |
| Unauthorized workstation, otherwise valid parameter | Sometimes miss | Hold / block |
| Valid parameter, invalid operating state | Miss if range-only | Block |
| Individually valid parameters, unsafe combination | Miss | Block |
| Slow manipulation inside normal ranges | Miss | Hold / block via temporal rules |
| Replay of a previously approved change | Miss | Block |
| Unexpected logic edit | Often out of scope | Detect as logic-change event |
| Unsafe PLC mode transition | Partial | Block |
| Cross-PLC conflicting changes | Miss | Block |
| Authorized change with unsafe physical consequences | Miss without prediction | Block / hold after simulation |

## What this is not

This is not another generic network IDS, not a simple PLC value-range checker, and not an unsupervised anomaly dashboard. Machine learning is optional and must never silently override hard safety constraints.

## Desired operating concept

The system is a **Cyber-Physical PLC Change Assurance Gateway**. A requested change is evaluated along independent dimensions — identity, authorization, provenance, value, state, transition, time, parameter dependency, cross-PLC consistency, and physical safety — then fused by an explainable decision engine.

Hard safety violations cannot be overridden by a low numerical risk score.

## Success criterion for the first prototype

The prototype is successful only if it can demonstrate, with recorded reasons and metrics, that:

1. A legitimate approved setpoint change is allowed.
2. A globally plausible but state-invalid change is blocked.
3. A slow in-range ramp is held or blocked.
4. An unsafe multi-variable combination is blocked.

If those four outcomes cannot be shown cleanly, later vendor coverage and ML features are out of scope.
