import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from api.responses import error
from domain.exceptions import CustomException

logger = logging.getLogger("scentstation.error")


def register_error_handlers(app):
    """Domain exceptions -> HTTP status (see domain/exceptions.py)."""

    @app.errorhandler(CustomException)
    def handle_custom(exc: CustomException):
        return error(exc.message, exc.error_code, exc.status_code)

    @app.errorhandler(HTTPException)
    def handle_http(exc: HTTPException):
        return error(exc.description, exc.name.upper().replace(" ", "_"), exc.code)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("Unhandled error")
        return error("Internal server error", "INTERNAL_ERROR", 500)
