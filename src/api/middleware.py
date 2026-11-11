import logging
import time
import uuid
from functools import wraps

from flask import g, request

from dependency_container import container
from domain.exceptions import UnauthorizedException

logger = logging.getLogger("scentstation.request")


def setup_middleware(app):
    """Request id + access log for every request."""

    @app.before_request
    def _start():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        g.started = time.time()

    @app.after_request
    def _finish(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        logger.info("%s %s -> %s (%.0f ms)", request.method, request.path, response.status_code,
                    (time.time() - getattr(g, "started", time.time())) * 1000)
        return response


def login_required(fn):
    """Staff endpoints: `Authorization: Bearer <JWT>`. Sets g.ctx (AuthContext: user, tenant, roles, permissions)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise UnauthorizedException("Missing bearer token")
        g.ctx = container.auth_service().authenticate(header[7:].strip())
        return fn(*args, **kwargs)
    wrapper.requires_auth = "bearer"
    return wrapper


def device_required(fn):
    """Kiosk / IoT endpoints: headers X-Device-Serial + X-Device-Secret. Sets g.device (the Machine)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.device = container.machine_service().authenticate_device(
            request.headers.get("X-Device-Serial", ""), request.headers.get("X-Device-Secret", ""))
        return fn(*args, **kwargs)
    wrapper.requires_auth = "device"
    return wrapper
