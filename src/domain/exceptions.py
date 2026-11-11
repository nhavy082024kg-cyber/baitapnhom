# Business exceptions. error_handler.py maps `status_code` to the HTTP response.

class CustomException(Exception):
    """Base class for all custom exceptions in the application."""
    status_code = 400
    error_code = "ERROR"

    def __init__(self, message="An error occurred"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(CustomException):
    """Exception raised when a resource is not found."""
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message="Resource not found"):
        super().__init__(message)


class ValidationException(CustomException):
    """Exception raised for validation errors."""
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message="Validation error"):
        super().__init__(message)


class UnauthorizedException(CustomException):
    """Exception raised when the caller is not authenticated."""
    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(self, message="Unauthorized access"):
        super().__init__(message)


class ForbiddenException(CustomException):
    """Authenticated, but not allowed (missing permission, wrong tenant, step-up needed)."""
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message="Forbidden", error_code="FORBIDDEN"):
        self.error_code = error_code
        super().__init__(message)


class ConflictException(CustomException):
    """Exception raised for conflicts in the application (duplicates...)."""
    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, message="Conflict occurred"):
        super().__init__(message)


class BusinessRuleException(CustomException):
    """A business rule from the proposal (section 17) prevents the action."""
    status_code = 422
    error_code = "BUSINESS_RULE"

    def __init__(self, message="Business rule violated", error_code="BUSINESS_RULE"):
        self.error_code = error_code
        super().__init__(message)


class InvalidStateTransition(CustomException):
    """Order / command state machine does not allow this transition."""
    status_code = 409
    error_code = "INVALID_STATE_TRANSITION"

    def __init__(self, message="Invalid state transition"):
        super().__init__(message)
