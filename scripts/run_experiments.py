from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from experiments.report import main as report  # noqa: E402
from experiments.runner import run_suite  # noqa: E402


if __name__ == "__main__":
    run_suite()
    report()
