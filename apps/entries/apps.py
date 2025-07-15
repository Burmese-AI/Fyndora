from django.apps import AppConfig


class EntriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.entries"

    def ready(self):
        pass
