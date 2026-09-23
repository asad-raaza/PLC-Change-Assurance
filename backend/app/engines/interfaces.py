"""Stable plugin interfaces. New algorithms subclass SafetyAlgorithm."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from app.domain.models import (
    ChangeRequest,
    CheckResult,
    EvaluationContext,
    RecoveryRecommendation,
    TwinPrediction,
)


class SafetyAlgorithm(ABC):
    """Research comparison hook. Must not read experiment labels."""

    name: str = "unnamed"

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> CheckResult:
        raise NotImplementedError


class ProtocolAdapter(Protocol):
    def to_change_request(self, raw: bytes | dict) -> ChangeRequest: ...


class DigitalTwinAdapter(Protocol):
    def simulate(
        self,
        current_state: dict,
        proposed_change: ChangeRequest,
        horizon: float,
    ) -> TwinPrediction: ...


class StateExtractor(Protocol):
    """Future automatic state extraction from IEC 61131-3 / historian / events."""

    def extract(self, source: dict) -> dict: ...


class RecoveryEngine(Protocol):
    def evaluate(self, context: EvaluationContext) -> RecoveryRecommendation: ...
