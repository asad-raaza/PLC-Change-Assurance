"""Detection and operational metrics. FPR is a first-class OT usability result."""

from __future__ import annotations

from dataclasses import dataclass, field


POSITIVE = {"BLOCK", "HOLD", "REQUIRE_APPROVAL", "RECOVERY_REQUIRED", "SAFE_SUBSTITUTE"}


@dataclass
class Confusion:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    latencies: list[float] = field(default_factory=list)

    def add(self, label: str, decision: str, latency_ms: float = 0.0) -> None:
        predicted_attack = decision in POSITIVE
        actual_attack = label == "attack"
        if predicted_attack and actual_attack:
            self.tp += 1
        elif predicted_attack and not actual_attack:
            self.fp += 1
        elif not predicted_attack and not actual_attack:
            self.tn += 1
        else:
            self.fn += 1
        self.latencies.append(latency_ms)

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        denom = self.fp + self.tn
        return self.fp / denom if denom else 0.0

    def as_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "tn": self.tn,
            "fn": self.fn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "false_positive_rate": round(self.fpr, 4),
            "decision_latency_ms_avg": round(sum(self.latencies) / len(self.latencies), 3) if self.latencies else 0.0,
        }
