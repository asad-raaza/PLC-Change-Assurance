# Research Gap Mapping

Every capability is mapped to an existing approach, remaining limitation, proposed approach, implementation status, and required experiment.

Status vocabulary: `implemented` | `partially implemented` | `simulated` | `planned` | `unsupported`

| Capability | Existing approach | Remaining limitation | Proposed approach | Status | Experiment |
| --- | --- | --- | --- | --- | --- |
| Static range / allowlist | Historian limits, DCS interlocks | Misses in-range stealth and state-conditioned hazards | Baseline 1 | implemented | Attack 1 vs legitimate writes |
| Global invariants | Alarm limits | No identity/intent | Baseline 2 | implemented | Combination vs global-only |
| Authentication / RBAC | IDE logins, AD | Stolen creds succeed | Identity + host + role checks | implemented | Scenarios A–C |
| Change provenance / tickets | CMMS after the fact | Replay, wrong value/state | Approved change manifest, single-use | implemented | Replay, expired, wrong object |
| FSM / state-aware policy | Procedure docs, batch recipes | Rarely inline on PLC writes | Configurable state model + guards | implemented | Attack 2 (wrong state) |
| Temporal / rate rules | Historian rate alarms | Not fused with intent | TemporalRuleEngine interface | implemented | Attack 3 (slow ramp) |
| Relational dependencies | PLC interlocks | Bypass if logic edited | External dependency engine | implemented | Attack 4 (pump + valve) |
| Cross-PLC consistency | Operator knowledge | Local monitors miss global hazard | Plant graph + CrossPLCValidator | implemented | Attack 6 |
| Physics / twin prediction | Offline twins | Not a PEP; can be wrong | SafetyModel + DigitalTwinAdapter | implemented (mock twin) | Attack 7 |
| Recovery recommendation | Manual SOP | `prev == safe` is false | SafeRecoveryEngine, advisory only | implemented (advisory) | Attack 8 |
| Logic-change detection | Vendor logs | Hard to intercept reliably | LogicChangeEvent abstraction | simulated | Documented as simulated |
| Siemens / CIP / OPC UA / DNP3 / IEC-104 | Vendor tools | Out of first prototype | ProtocolAdapter interface | planned | RQ8 later |
| Auto state extraction from IEC 61131-3 | Research prototypes | Unvalidated here | StateExtractor interface | planned | Future work |
| ML anomaly scoring | ICS IDS papers | Poisoning, opacity | Optional later; cannot override hard safety | unsupported (by design) | N/A |
| Inline enforcement | Firewalls / data diodes | Dangerous if untested | Lab-mode PEP only | implemented, disabled by default | Never against production |
| Baseline learning | Anomaly IDS | Attacker during learning | Trusted window + manual approval | implemented | Poisoning negative test |
| Explainable decisions | Black-box scores | Unusable in OT | Structured reasons + per-check status | implemented | Qualitative operator review |
| Fast vs deep path | N/A | Simulation delay | Deterministic fast path, async deep analysis | implemented | H5 latency |
| Framework self-security | AppSec baselines | Gateway is high value | Authn/z, hashed secrets, audit | implemented | Abuse cases in tests |
