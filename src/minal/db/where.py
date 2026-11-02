"""Backend-neutral filter helpers."""
from __future__ import annotations

from typing import Any

from .ports import Where

_OPS = {
    "$eq": lambda v, a: v == a,
    "$ne": lambda v, a: v != a,
    "$gt": lambda v, a: v > a,
    "$gte": lambda v, a: v >= a,
    "$lt": lambda v, a: v < a,
    "$lte": lambda v, a: v <= a,
    "$in": lambda v, a: v in a,
}


def matches(metadata: dict[str, Any], where: Where) -> bool:
    """Evaluate a Where against a metadata dict (used by the in-memory backend)."""
    for field, cond in where.items():
        value = metadata.get(field)
        ops = cond if isinstance(cond, dict) else {"$eq": cond}
        for op, arg in ops.items():
            if op not in _OPS:
                raise ValueError(f"unsupported operator {op!r}")
            if value is None:
                if op == "$ne":
                    continue
                return False
            if not _OPS[op](value, arg):
                return False
    return True


def to_chroma(where: Where | None) -> dict[str, Any] | None:
    """Chroma allows one operator per field clause, so expand and AND them."""
    if not where:
        return None
    clauses: list[dict[str, Any]] = []
    for field, cond in where.items():
        if isinstance(cond, dict):
            clauses.extend({field: {op: arg}} for op, arg in cond.items())
        else:
            clauses.append({field: cond})
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}
