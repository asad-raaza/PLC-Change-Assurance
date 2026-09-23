# Threat Model

This document is required before enforcement is enabled. Enforcement remains disabled unless `LAB_MODE=true` and the configured operating mode is `enforcement`.

## System under consideration

The assurance framework sits logically between engineering / HMI / SCADA / applications and PLC write paths.

```
Engineer / HMI / SCADA / Application
                |
                v
       Requested PLC Change
                |
                v
+------------------------------------+
| PLC Change Assurance Framework     |
+------------------------------------+
                |
       ALLOW / ALERT / HOLD / BLOCK
                |
                v
              PLC / process
```

The first testbed is a local water-tank process with OpenPLC-compatible Modbus/TCP semantics. No production ICS, no external OT scanning, and no undocumented proprietary PLC manipulation are in scope.

## Trust boundaries

| Element | Trust | Rationale |
| --- | --- | --- |
| Assurance framework process and its signed policy store | Trusted computing base, but itself a target | Compromise of the gateway is a complete bypass |
| Database | Partially trusted | Integrity must be checked; tampering is an attack |
| Policy files / model versions | Partially trusted | Must be authenticated, versioned, and audited |
| Engineering workstation | **Not trusted** | Can be compromised while presenting valid credentials |
| Engineering credentials | **Not trusted in isolation** | Stolen credentials are Scenario C |
| HMI / SCADA | Not trusted as a write source of truth | Same protocol path as an attacker |
| PLC runtime | Partially trusted | Executes what it is told; logic can be altered |
| Sensors | Partially trusted | Scenario L: spoofed sensors can make a dangerous write look safe |
| Digital twin / physics plugin | Partially trusted | Advisory evidence only until validated |
| Operator override | Trusted only with dual control + audit | Override is a privileged act, not a silent escape |
| Experiment ground-truth labels | Isolated | Detectors must never read labels during evaluation |

Unrealistic assumption explicitly rejected: “the engineering workstation is always trusted.”

## In scope

- Unauthorized, stolen-credential, and insider PLC parameter writes
- Replay, slow-ramp, combination, and cross-PLC coordinated writes
- State-invalid and transition-invalid operations
- Timer / PID / threshold / interlock / mode changes (as change classes)
- Logic-change events as a first-class type (simulated until reliable interception exists)
- Framework self-protection: authn/z, RBAC, audit integrity, policy versioning
- Fail-safe behavior when components are unavailable
- Local simulation, Docker testbed, and authorized lab hardware only

## Out of scope (initial prototype)

- Production plant deployment
- Scanning or interacting with external OT networks
- Weaponized exploits against proprietary PLC firmware
- Autonomous recovery that writes to a live process without advisory validation
- Claiming novelty for standard RBAC, range checks, or generic IDS techniques
- Mandatory machine-learning detectors

## Assumed trusted

- The researcher-operated lab host and Docker compose network, for experiment control
- Initial commissioning dataset after **manual approval**
- Cryptographic secrets held in environment / secret store, not in git

## Not trusted

- Any engineering workstation, jump host, or HMI
- Any Modbus client, including “authorized” clients
- Network path between client and PLC
- Learned baselines until a trusted window is approved
- Sensor values used as the sole safety predicate

## Partially trusted

- PLC program and current process state estimates
- Historian / past approvals (replay risk)
- Digital-twin predictions (confidence-bounded, never sole hard constraint unless configured)
- Operators issuing emergency bypass

## Attacker scenarios

### Scenario A — Unauthorized machine

An unknown host writes PLC registers directly over Modbus/TCP.

**Expected controls:** source identity/host allowlist, authorization, provenance, audit.

### Scenario B — Compromised engineering workstation

The attacker has the valid network path and client tools of `eng-ws-02`.

**Expected controls:** provenance (ticket, value, window, state), behavioral/temporal checks, approval consumption. Network allowlisting alone fails.

### Scenario C — Stolen credentials

The attacker authenticates as a legitimate engineer.

**Expected controls:** workstation binding, session context, approval match, dual-control for high-criticality writes. Authentication alone fails.

### Scenario D — Malicious insider

An authorized user intentionally writes an unsafe value.

**Expected controls:** state/dependency/safety engines. Intent cannot be inferred from identity.

### Scenario E — Accidental dangerous value

Same as D from the process point of view.

**Expected controls:** identical hard safety path; explainability must be operator-usable.

### Scenario F — Slow manipulation

`50 → 52 → 54 → 56 → 58 → 60` stays inside global bounds.

**Expected controls:** temporal / rate-of-change rules. Static range checking fails.

### Scenario G — Unsafe combination

Each parameter is individually legal; the joint state is not (pump high, valve closed).

**Expected controls:** dependency engine and cross-PLC graph.

### Scenario H — Replay

A historically legitimate approved write is replayed later.

**Expected controls:** single-use approvals, nonce/session binding, time window, already-consumed detection.

### Scenario I — Logic edit

Online edit or program download changes control logic.

**Expected controls:** `LogicChangeEvent` path. First version may be simulated; must not be claimed as implemented interception.

### Scenario J — Engineering configuration

Timers, counters, PID, alarm thresholds, interlocks.

**Expected controls:** change-class specific policies, not only process setpoints.

### Scenario K — Coordinated multi-PLC

Several controllers change in a locally valid, globally unsafe way.

**Expected controls:** plant dependency graph and cross-PLC validator.

### Scenario L — Sensor spoofing to justify a write

A dangerous setpoint is paired with a falsified measurement that satisfies a guard.

**Expected controls:** do not treat sensors as fully trusted; require redundant evidence or conservative fail-safe when sensor integrity is low.

## Framework self-threats

The gateway is itself an OT-adjacent control point.

| Threat | Mitigation |
| --- | --- |
| Policy modification | RBAC, versioned policies, hash recorded on every decision |
| Database tampering | Authenticated DB, append-only audit, no silent history mutation |
| Log deletion | Append-oriented audit, correlation IDs, export |
| Fake approvals | Approval schema, consumption, expiry, actor binding |
| API abuse | Authn required, RBAC, input validation, rate-aware logging |
| Credential theft | Password hashes only (bcrypt), no plaintext, demo secrets only in lab |
| Replay against the API | Request IDs, approval consumption, timestamps |
| MITM | TLS in non-lab deployments; lab HTTP documented as lab-only |
| Configuration rollback | Version table, audit of model activation |
| Plugin tampering | Explicit adapter registry, capability honesty |
| Model / baseline poisoning | Learned behavior is not enforceable until approved |

## Fail-safe posture

Operators configure `fail_open`, `fail_closed`, or `fail_to_advisory` per environment and asset criticality. There is no hard-coded universal answer. Default for the lab prototype is `fail_to_advisory` so research evaluation is not silently blocked by infrastructure faults, while hard safety failures still surface as HOLD/BLOCK recommendations.
