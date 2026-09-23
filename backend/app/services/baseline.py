"""Learning mode. Observed behavior is never auto-promoted to enforceable policy."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.orm import BaselineWindowRow, ObservationRow


class BaselineService:
    def record(self, db: Session, kind: str, payload: dict, trusted_window: bool = False) -> None:
        db.add(ObservationRow(kind=kind, payload=payload, trusted_window=trusted_window, approved_for_policy=False))

    def can_enforce_learned(self, db: Session) -> bool:
        windows = db.scalars(select(BaselineWindowRow)).all()
        return any(window.trusted and window.approved for window in windows)
