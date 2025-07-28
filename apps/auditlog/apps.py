from django.apps import AppConfig


class AuditlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditlog"

    def ready(self):
        """Initialize signal handlers when the app is ready."""
        # Import signal handlers to ensure they are registered
        from . import auth_signals  # noqa: F401
        from .signal_handlers import initialize_audit_signals

        # Initialize the audit signal handlers
        initialize_audit_signals()
