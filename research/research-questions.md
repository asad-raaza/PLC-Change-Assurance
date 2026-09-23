# Research Questions and Hypotheses

These questions guide implementation and experiments. Hypotheses are **not** claimed as proven until the experiment suite produces supporting evidence.

## Research questions

**RQ1.** Can PLC modification security distinguish legitimate engineering changes from malicious changes performed using valid credentials and legitimate industrial protocols?

**RQ2.** How much does state-aware validation improve detection over static global thresholds?

**RQ3.** Can relational and temporal constraints detect attacks where individual parameters remain within normal limits?

**RQ4.** Can cross-PLC reasoning detect unsafe conditions invisible to individual PLC monitors?

**RQ5.** Can proposed PLC changes be evaluated against predicted physical consequences before execution?

**RQ6.** Can safe recovery be determined automatically after malicious PLC modification?

**RQ7.** What runtime overhead does multi-layer change assurance introduce?

**RQ8.** How portable is the approach across different PLCs and industrial protocols?

**RQ9.** How much manual engineering information is required to deploy the framework?

**RQ10.** What failure modes occur when state information or sensor readings are incomplete or malicious?

## Hypotheses (measurable, not proven)

**H1.** State-aware validation detects more stealthy PLC modifications than global value-range checking.

**H2.** Temporal and dependency constraints detect attacks that remain within individual parameter bounds.

**H3.** Change-intent validation reduces false positives for legitimate maintenance activities.

**H4.** Cross-PLC reasoning detects unsafe coordinated changes missed by single-controller analysis.

**H5.** A modular assurance gateway can evaluate deterministic safety policies with acceptable latency for practical OT deployment (fast-path deterministic checks in milliseconds).

## How each hypothesis is tested

| Hypothesis | Baseline | Treatment | Primary metrics |
| --- | --- | --- | --- |
| H1 | Static range checker | FSM / state-aware checker | Recall on state-invalid attacks; FPR on legitimate changes |
| H2 | Range + FSM | FSM + temporal + dependency | Detection of slow-ramp and combination attacks |
| H3 | No provenance | Provenance + approvals | FPR during approved maintenance |
| H4 | Single-PLC engines | Cross-PLC validator | Detection of coordinated PLC-A / PLC-B conflicts |
| H5 | N/A (performance) | Fast path vs deep analysis | Decision latency, CPU, memory |

Detectors never receive experiment ground-truth labels at evaluation time. Labels are joined only in the experiment harness after decisions are recorded.
