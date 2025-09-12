from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, IntegrityError
from requests.exceptions import RequestException


class BaseServiceError(Exception):
    """Base exception for all service errors with automatic type detection."""

    default_detail = "An error occurred"

    def __init__(self, detail=None, context=None, original_exception=None):
        self.context = context or {}
        self.original_exception = original_exception

        # Build the detail message automatically if not provided
        if detail:
            self.detail = detail
        else:
            self.detail = self.build_detail_message()

        super().__init__(self.detail)

        # Add original exception info to context
        if original_exception:
            self.context.update({
                "original_error_type": type(original_exception).__name__,
                "original_error_msg": str(original_exception),
            })

    def build_detail_message(self):
        parts = [self.default_detail]

        if self.original_exception:
            exc_type = type(self.original_exception).__name__
            exc_msg = str(self.original_exception)
            parts.append(f"Cause: {exc_type} - {exc_msg}")

        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {ctx_str}")

        return " | ".join(parts)

    @classmethod
    def from_exception(cls, exception, context=None):
        context = context or {}
        for builtin_exc, custom_exc_class in cls.EXCEPTION_MAP.items():
            if isinstance(exception, builtin_exc):
                return custom_exc_class(
                    original_exception=exception,
                    context=context
                )
        return cls(original_exception=exception, context=context)

    def __str__(self):
        return self.detail

class ValidationServiceError(BaseServiceError):
    default_detail = "Validation failed"


class BulkOperationError(BaseServiceError):
    default_detail = "A bulk operation failed"


class ExternalServiceError(BaseServiceError):
    default_detail = "External service request failed"


# --- Exception mapping ---
BaseServiceError.EXCEPTION_MAP = {
    DatabaseError: BulkOperationError,
    IntegrityError: BulkOperationError,
    DjangoValidationError: ValidationServiceError,
    RequestException: ExternalServiceError,
    ValueError: ValidationServiceError,
    TypeError: ValidationServiceError,
}