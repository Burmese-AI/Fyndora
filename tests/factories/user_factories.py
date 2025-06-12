"""
Factory Boy factories for User models.
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.accounts.models import CustomUser
from apps.accounts.constants import StatusChoices

fake = Faker()


class CustomUserFactory(DjangoModelFactory):
    """Factory for creating CustomUser instances."""

    class Meta:
        model = CustomUser
        skip_postgeneration_save = True

    # Generate unique email and username using sequences
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")

    # Default values
    status = StatusChoices.ACTIVE
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password and save the user."""
        if not create:
            return

        # Set password (extracted password or default)
        password = extracted or "testpass123"
        self.set_password(password)
        self.save()


class StaffUserFactory(CustomUserFactory):
    """Factory for creating staff users."""

    username = factory.Sequence(lambda n: f"staff{n}")
    email = factory.Sequence(lambda n: f"staff{n}@example.com")
    is_staff = True


class SuperUserFactory(CustomUserFactory):
    """Factory for creating superuser instances."""

    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.Sequence(lambda n: f"admin{n}@example.com")
    is_staff = True
    is_superuser = True


class SuspendedUserFactory(CustomUserFactory):
    """Factory for creating suspended users."""

    username = factory.Sequence(lambda n: f"suspended{n}")
    email = factory.Sequence(lambda n: f"suspended{n}@example.com")
    status = StatusChoices.SUSPENDED
    is_active = False
