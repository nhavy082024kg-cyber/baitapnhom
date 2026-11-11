from functools import wraps

from flask import g, request
from marshmallow import EXCLUDE, ValidationError

from domain.exceptions import ValidationException


def validate_json(schema_cls, partial: bool = False):
    """
    Validate the JSON body with a Marshmallow schema; the clean dict is available as `g.json`.
    The schema is also used by api/swagger.py to document the request body.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                raise ValidationException("Request body must be a JSON object")
            try:
                g.json = schema_cls(unknown=EXCLUDE, partial=partial).load(payload)
            except ValidationError as exc:
                raise ValidationException(f"Invalid request: {exc.messages}")
            return fn(*args, **kwargs)
        wrapper.request_schema = schema_cls
        return wrapper
    return decorator


def int_arg(name: str, default=None):
    """Read an integer query-string parameter (?limit=20)."""
    value = request.args.get(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        raise ValidationException(f"{name} must be an integer")
