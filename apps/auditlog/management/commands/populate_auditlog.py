import random
from django.core.management.base import BaseCommand
from faker import Faker
from apps.auditlog.models import AuditTrail
from apps.auditlog.constants import (
    AUDIT_ACTION_TYPE_CHOICES,
    AUDIT_TARGET_ENTITY_TYPE_CHOICES,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Populates the audit log with demo data"

    def handle(self, *args, **options):
        self.stdout.write("Deleting existing audit log data...")
        AuditTrail.objects.all().delete()

        self.stdout.write("Populating audit log with new demo data...")
        faker = Faker()

        # Get all users, or create one if none exist
        users = list(User.objects.all())
        if not users:
            users.append(
                User.objects.create_user(username="demo_user", password="password")
            )

        action_types = [choice[0] for choice in AUDIT_ACTION_TYPE_CHOICES]

        for _ in range(100):
            action_type = random.choice(action_types)
            metadata = {}

            if action_type == "user_log_in" or action_type == "user_log_out":
                metadata = {"ip_address": faker.ipv4()}
            elif action_type == "user_password_reset":
                metadata = {"method": random.choice(["email", "sms"])}
            elif action_type == "user_profile_updated":
                metadata = {
                    "fields_changed": random.sample(
                        ["email", "first_name", "last_name", "avatar"],
                        k=random.randint(1, 2),
                    )
                }
            elif action_type == "status_changed":
                statuses = ["Open", "In Progress", "Resolved", "Closed"]
                old_status, new_status = random.sample(statuses, k=2)
                metadata = {"old_status": old_status, "new_status": new_status}
            elif "workspace" in action_type:
                metadata = {"workspace_name": faker.company()}
            elif "document" in action_type:
                metadata = {"document_title": faker.bs().title()}

            AuditTrail.objects.create(
                user=random.choice(users),
                action_type=action_type,
                target_entity_type=random.choice(
                    [choice[0] for choice in AUDIT_TARGET_ENTITY_TYPE_CHOICES]
                ),
                target_entity=faker.uuid4(),
                metadata=metadata,
            )

        self.stdout.write(
            self.style.SUCCESS("Successfully populated audit log with 100 entries.")
        )
