"""
Audit logging configuration settings.
"""


class AuditConfig:
    """Configuration settings for audit logging"""

    # Performance settings
    ENABLE_AUTOMATIC_LOGGING = True
    ENABLE_MANUAL_LOGGING = True
    MAX_METADATA_SIZE = 10000  # Maximum size of metadata in characters
    MAX_USER_AGENT_LENGTH = 200

    # Logging levels
    LOG_FIELD_CHANGES = True
    LOG_AUTHENTICATION_EVENTS = True
    LOG_PERMISSION_CHANGES = True

    # Bulk operation settings
    BULK_OPERATION_THRESHOLD = (
        50  # Log individual IDs only for operations under this threshold
    )
    BULK_SAMPLE_SIZE = 10  # Number of sample IDs to log for large bulk operations

    # Security settings
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "secret",
        "key",
        "hash",
        "salt",
        "credit_card",
        "ssn",
        "social_security",
        "bank_account",
    }

    @classmethod
    def is_sensitive_field(cls, field_name):
        """Check if a field contains sensitive data"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in cls.SENSITIVE_FIELDS)
