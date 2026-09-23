"""Shared comparison helpers used by policy, temporal, and dependency engines."""

from __future__ import annotations

from typing import Any


def to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return float(value) if isinstance(value, bool) else None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def compare(left: Any, expr: str) -> bool:
    """Evaluate expressions like '>= 80', '== 1', '!= 0', '> 60'."""
    expr = expr.strip()
    for op in (">=", "<=", "!=", "==", ">", "<"):
        if expr.startswith(op):
            rhs = expr[len(op) :].strip()
            lv = to_float(left)
            rv = to_float(rhs)
            if lv is None or rv is None:
                if op == "==":
                    return str(left) == rhs
                if op == "!=":
                    return str(left) != rhs
                return False
            if op == ">=":
                return lv >= rv
            if op == "<=":
                return lv <= rv
            if op == ">":
                return lv > rv
            if op == "<":
                return lv < rv
            if op == "==":
                return lv == rv
            if op == "!=":
                return lv != rv
    # Bare numeric "85" treated as equality
    rv = to_float(expr)
    lv = to_float(left)
    if lv is not None and rv is not None:
        return lv == rv
    return str(left) == expr


def values_close(a: Any, b: Any, tol: float = 1e-6) -> bool:
    fa, fb = to_float(a), to_float(b)
    if fa is not None and fb is not None:
        return abs(fa - fb) <= tol
    return a == b
