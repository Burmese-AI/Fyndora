"""
Audit logging configuration settings.
"""

from .constants import AuditActionType, is_critical_action


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

    # Retention settings (simple MVP version)
    DEFAULT_RETENTION_DAYS = 90  # Default retention period
    AUTHENTICATION_RETENTION_DAYS = 30  # Shorter retention for auth logs
    CRITICAL_RETENTION_DAYS = 365  # Longer retention for critical actions
    
    # Cleanup settings
    CLEANUP_BATCH_SIZE = 1000  # Number of records to delete in each batch
    CLEANUP_DRY_RUN = False  # Set to True to see what would be deleted without actually deleting

    @classmethod
    def is_sensitive_field(cls, field_name):
        """Check if a field contains sensitive data"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in cls.SENSITIVE_FIELDS)
    
    @classmethod
    def get_retention_days_for_action(cls, action_type):
        """Get retention period for a specific action type"""
        # Authentication events have shorter retention
        auth_actions = [
            AuditActionType.LOGIN_SUCCESS,
            AuditActionType.LOGIN_FAILED,
            AuditActionType.LOGOUT,
        ]
        
        if action_type in auth_actions:
            return cls.AUTHENTICATION_RETENTION_DAYS
        elif is_critical_action(action_type):
            return cls.CRITICAL_RETENTION_DAYS
        else:
            return cls.DEFAULT_RETENTION_DAYS
