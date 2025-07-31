from django.apps import AppConfig


class RemittanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.remittance"

    def ready(self):
        pass
