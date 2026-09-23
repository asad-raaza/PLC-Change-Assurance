"""Generate a markdown experiment report from the latest run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "experiments" / "results" / "latest.json"
OUT = ROOT / "experiments" / "results" / "REPORT.md"


def main() -> None:
    if not RESULTS.exists():
        from experiments.runner import run_suite

        run_suite()
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    lines = [
        "# Experiment report",
        "",
        f"Generated: {data['generated_at']}",
        f"Seed: {data['seed']}",
        f"Framework: {data['framework_version']}",
        "",
        "Hypotheses are not marked proven by this report; it records evidence only.",
        "",
        "## Method metrics",
        "",
        "| Method | TP | FP | TN | FN | Precision | Recall | F1 | FPR | Latency ms |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, metrics in data["metrics"].items():
        lines.append(
            f"| {name} | {metrics['tp']} | {metrics['fp']} | {metrics['tn']} | {metrics['fn']} | "
            f"{metrics['precision']} | {metrics['recall']} | {metrics['f1']} | "
            f"{metrics['false_positive_rate']} | {metrics['decision_latency_ms_avg']} |"
        )
    lines += ["", "## Scenario outcomes", "", "| Scenario | Label | Full | Expected | Static | FSM | Temporal |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in data["rows"]:
        alg = row["algorithms"]
        lines.append(
            f"| {row['scenario']} | {row['label']} | {row['full_decision']} | {row['expected_full']} | "
            f"{alg.get('static_range')} | {alg.get('fsm')} | {alg.get('fsm_temporal')} |"
        )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
