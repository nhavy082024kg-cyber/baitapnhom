from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal

# Every entity is a keyword-only dataclass: Order(order_code="A", ...)
entity = dataclass(kw_only=True)


def to_jsonable(value):
    """Convert Decimal / datetime / dataclass into JSON-safe values (used for audit before/after)."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_jsonable(getattr(value, f.name)) for f in fields(value)}
    return value


def snapshot(obj, names):
    """Small dict with only the requested attributes, JSON-safe."""
    return {n: to_jsonable(getattr(obj, n, None)) for n in names}
