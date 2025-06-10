import random
from django.core.management.base import BaseCommand
from faker import Faker
from apps.auditlog.models import AuditTrail
from apps.auditlog.constants import AUDIT_ACTION_TYPE_CHOICES, AUDIT_TARGET_ENTITY_TYPE_CHOICES
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the audit log with demo data'

    def handle(self, *args, **options):
        self.stdout.write('Populating audit log with demo data...')
        faker = Faker()

        # Get all users, or create one if none exist
        users = list(User.objects.all())
        if not users:
            users.append(User.objects.create_user(username='demo_user', password='password'))

        for _ in range(100):
            AuditTrail.objects.create(
                user=random.choice(users),
                action_type=random.choice([choice[0] for choice in AUDIT_ACTION_TYPE_CHOICES]),
                target_entity_type=random.choice([choice[0] for choice in AUDIT_TARGET_ENTITY_TYPE_CHOICES]),
                target_entity=faker.uuid4(),
                metadata=faker.json()
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated audit log with 100 entries.'))
