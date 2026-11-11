import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from domain.exceptions import ValidationException


def parse_datetime(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    """ISO string -> naive UTC datetime. Used for device timestamps."""
    if value in (None, ""):
        return default
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise ValidationException(f"Invalid datetime: {value}")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def to_decimal(value: Any, field: str, minimum: Optional[Decimal] = None) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationException(f"{field} must be a number")
    if minimum is not None and number < minimum:
        raise ValidationException(f"{field} must be >= {minimum}")
    return number


def new_code(prefix: str, length: int = 12) -> str:
    return f"{prefix}{uuid.uuid4().hex[:length].upper()}"
