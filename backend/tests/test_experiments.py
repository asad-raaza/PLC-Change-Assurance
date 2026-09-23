from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.runner import run_suite


def test_experiment_suite_separates_labels_and_records_all_methods():
    payload = run_suite(seed=7)
    assert payload["rows"]
    for row in payload["rows"]:
        assert "static_range" in row["algorithms"]
        assert "full_framework" in row["algorithms"]
        # Detector outputs exist independently of the harness label.
        assert row["label"] in {"benign", "attack"}
    assert "full_framework" in payload["metrics"]
    # Legitimate approved change must remain allowed by the full framework.
    allowed = next(r for r in payload["rows"] if r["scenario"] == "authorized_setpoint")
    assert allowed["full_decision"] == "ALLOW"
    wrong_state = next(r for r in payload["rows"] if r["scenario"] == "wrong_state")
    assert wrong_state["algorithms"]["static_range"] == "ALLOW"
    assert wrong_state["full_decision"] == "BLOCK"
