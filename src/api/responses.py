from flask import jsonify

from domain.models.base import to_jsonable

# Never leave the server, whatever entity is serialised
SENSITIVE_KEYS = {"password_hash", "device_secret_hash", "password_reset_token", "password_reset_expires_at"}


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def serialize(obj):
    """Entity / list / dict -> JSON-safe structure (Decimal -> str, datetime -> ISO-8601, secrets removed)."""
    return _strip(to_jsonable(obj))


def ok(data=None, status: int = 200):
    """Success envelope: {"status": "success", "data": ...}"""
    return jsonify({"status": "success", "data": serialize(data)}), status


def error(message: str, code: str, status: int):
    """Error envelope: {"status": "error", "error": {"code": ..., "message": ...}}"""
    return jsonify({"status": "error", "error": {"code": code, "message": message}}), status
