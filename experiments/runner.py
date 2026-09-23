"""Run the scenario suite. Detectors never receive label or attack_type."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog import DEFAULT_CATALOG  # noqa: E402
from app.engines.baselines import compare_all  # noqa: E402
from app.engines.decision import evaluate_change  # noqa: E402
from experiments.metrics import Confusion  # noqa: E402
from experiments.scenarios import SCENARIOS  # noqa: E402

RESULTS = ROOT / "experiments" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def run_suite(seed: int = 42) -> dict:
    rows = []
    by_method: dict[str, Confusion] = defaultdict(Confusion)
    for scenario in SCENARIOS:
        ctx = scenario.build()
        # Explicit isolation: do not copy label onto the request.
        ctx.request.label = None
        ctx.request.attack_type = None
        full = evaluate_change(ctx, DEFAULT_CATALOG)
        algos = compare_all(ctx, DEFAULT_CATALOG)
        record = {
            "scenario": scenario.name,
            "family": scenario.family,
            "label": scenario.label,
            "attack_type": scenario.attack_type,
            "privilege": scenario.privilege,
            "speed": scenario.speed,
            "process_state": ctx.request.current_process_state,
            "plc": ctx.request.plc_id,
            "parameter": ctx.request.parameter,
            "old_value": ctx.request.previous_value,
            "new_value": ctx.request.requested_value,
            "full_decision": full.decision.value,
            "full_reasons": full.reasons,
            "hard_violation": full.hard_violation,
            "risk_score": full.risk_score,
            "latency_ms": full.latency_ms,
            "algorithms": {k: v.value for k, v in algos.items()},
            "expected_full": scenario.expected_full,
            "seed": seed,
        }
        rows.append(record)
        for method, decision in algos.items():
            by_method[method].add(scenario.label, decision.value, full.latency_ms)
        by_method["full_framework_named"].add(scenario.label, full.decision.value, full.latency_ms)

    summary = {name: conf.as_dict() for name, conf in by_method.items()}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "framework_version": "0.1.0",
        "rows": rows,
        "metrics": summary,
    }
    json_path = RESULTS / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    csv_path = RESULTS / "latest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "family",
                "label",
                "attack_type",
                "full_decision",
                "expected_full",
                "static_range",
                "fsm",
                "fsm_temporal",
                "full_framework",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "scenario": row["scenario"],
                    "family": row["family"],
                    "label": row["label"],
                    "attack_type": row["attack_type"],
                    "full_decision": row["full_decision"],
                    "expected_full": row["expected_full"],
                    "static_range": row["algorithms"].get("static_range"),
                    "fsm": row["algorithms"].get("fsm"),
                    "fsm_temporal": row["algorithms"].get("fsm_temporal"),
                    "full_framework": row["algorithms"].get("full_framework"),
                }
            )
    return payload


if __name__ == "__main__":
    result = run_suite()
    print(json.dumps(result["metrics"], indent=2))
    print(f"Wrote {RESULTS / 'latest.json'}")
