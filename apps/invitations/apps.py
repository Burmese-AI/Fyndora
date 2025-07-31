from django.apps import AppConfig


class InvitationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.invitations"

    def ready(self):
        import apps.invitations.signals  # noqa: F401
