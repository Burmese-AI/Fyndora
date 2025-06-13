"""
Unit tests for the accounts app models.

Following the test plan: Accounts App (apps.accounts)
- CustomUser Model Tests
- CustomUserManager Tests
- Authentication Tests
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import IntegrityError
import uuid

from apps.accounts.models import CustomUser
from apps.accounts.constants import StatusChoices
from tests.factories import (
    CustomUserFactory,
    StaffUserFactory,
    SuperUserFactory,
    SuspendedUserFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestCustomUserModel(TestCase):
    """Test the CustomUser model - essential functionality only."""

    @pytest.mark.django_db
    def test_user_creation_with_defaults(self):
        """Test user creation with default values."""
        user = CustomUserFactory()

        # Check defaults
        self.assertEqual(user.status, StatusChoices.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.user_id)  # UUID generated
        self.assertTrue(user.email)
        self.assertTrue(user.username)

    @pytest.mark.django_db
    def test_user_unique_constraints(self):
        """Test unique constraints on email and username."""
        from django.db import transaction

        CustomUserFactory(email="test@example.com", username="testuser")

        # Try to create user with duplicate email
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                CustomUserFactory(email="test@example.com")

        # Try to create user with duplicate username
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                CustomUserFactory(username="testuser")

    @pytest.mark.django_db
    def test_staff_user_creation(self):
        """Test staff user creation with correct permissions."""
        user = StaffUserFactory()

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.status, StatusChoices.ACTIVE)

    @pytest.mark.django_db
    def test_superuser_creation(self):
        """Test superuser creation with correct permissions."""
        user = SuperUserFactory()

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.status, StatusChoices.ACTIVE)

    @pytest.mark.django_db
    def test_suspended_user_creation(self):
        """Test suspended user creation."""
        user = SuspendedUserFactory()

        self.assertEqual(user.status, StatusChoices.SUSPENDED)
        self.assertFalse(user.is_active)

    def test_user_str_representation(self):
        """Test string representation format."""
        user = CustomUserFactory.build(
            email="test@example.com",
            username="testuser",
            status=StatusChoices.ACTIVE,
            is_staff=True,
        )

        expected = "test@example.com - testuser - active - Staff: True"
        self.assertEqual(str(user), expected)

    @pytest.mark.django_db
    def test_user_uuid_generation(self):
        """Test that each user gets a unique UUID primary key."""
        user1 = CustomUserFactory()
        user2 = CustomUserFactory()

        self.assertIsInstance(user1.user_id, uuid.UUID)
        self.assertIsInstance(user2.user_id, uuid.UUID)
        self.assertNotEqual(user1.user_id, user2.user_id)

    @pytest.mark.django_db
    def test_password_handling(self):
        """Test password setting and validation."""
        user = CustomUserFactory(password="testpass123")

        # Password should be hashed
        self.assertNotEqual(user.password, "testpass123")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.check_password("wrongpass"))

    def test_model_meta_options(self):
        """Test model meta configuration."""
        self.assertEqual(CustomUser._meta.verbose_name, "user")
        self.assertEqual(CustomUser._meta.verbose_name_plural, "users")
        self.assertEqual(CustomUser._meta.ordering, ["-created_at"])

    def test_authentication_fields(self):
        """Test authentication field configuration."""
        self.assertEqual(CustomUser.USERNAME_FIELD, "username")
        self.assertEqual(CustomUser.REQUIRED_FIELDS, ["email"])


@pytest.mark.unit
class TestCustomUserManager(TestCase):
    """Test the CustomUserManager - essential functionality only."""

    @pytest.mark.django_db
    def test_create_user_success(self):
        """Test successful user creation through manager."""
        user = User.objects.create_user(
            email="test@example.com", username="testuser", password="testpass123"
        )

        self.assertIsInstance(user, CustomUser)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("testpass123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    @pytest.mark.django_db
    def test_create_user_email_required(self):
        """Test that email is required for user creation."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(
                email="", username="testuser", password="testpass123"
            )

        self.assertEqual(str(context.exception), "The Email field is required")

    @pytest.mark.django_db
    def test_create_user_username_required(self):
        """Test that username is required for user creation."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(
                email="test@example.com", username="", password="testpass123"
            )

        self.assertEqual(str(context.exception), "The Username field is required")

    @pytest.mark.django_db
    def test_create_user_duplicate_email_validation(self):
        """Test duplicate email validation in manager."""
        # Create first user
        User.objects.create_user(
            email="duplicate@example.com", username="user1", password="testpass123"
        )

        # Try to create user with duplicate email
        with self.assertRaises(ValidationError) as context:
            User.objects.create_user(
                email="duplicate@example.com", username="user2", password="testpass123"
            )

        self.assertIn("A user with this email already exists.", str(context.exception))

    @pytest.mark.django_db
    def test_create_user_duplicate_username_validation(self):
        """Test duplicate username validation in manager."""
        # Create first user
        User.objects.create_user(
            email="user1@example.com", username="duplicate", password="testpass123"
        )

        # Try to create user with duplicate username
        with self.assertRaises(ValidationError) as context:
            User.objects.create_user(
                email="user2@example.com", username="duplicate", password="testpass123"
            )

        self.assertIn(
            "A user with this username already exists.", str(context.exception)
        )

    @pytest.mark.django_db
    def test_create_superuser_success(self):
        """Test successful superuser creation through manager."""
        user = User.objects.create_superuser(
            email="admin@example.com", username="admin", password="adminpass123"
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, "admin@example.com")
        self.assertEqual(user.username, "admin")

    @pytest.mark.django_db
    def test_create_superuser_with_extra_fields(self):
        """Test superuser creation with additional fields."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="adminpass123",
            status=StatusChoices.ACTIVE,
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.status, StatusChoices.ACTIVE)

    @pytest.mark.django_db
    def test_email_normalization(self):
        """Test that email is normalized during creation."""
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM", username="testuser", password="testpass123"
        )

        # Domain should be normalized to lowercase
        self.assertEqual(user.email, "Test@example.com")

    @pytest.mark.django_db
    def test_create_user_without_password(self):
        """Test creating user without password."""
        user = User.objects.create_user(email="nopass@example.com", username="nopass")

        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.is_active)


@pytest.mark.unit
class TestStatusChoices(TestCase):
    """Test the StatusChoices constants."""

    def test_status_choices_values(self):
        """Test that status choices have correct values."""
        self.assertEqual(StatusChoices.ACTIVE, "active")
        self.assertEqual(StatusChoices.SUSPENDED, "suspended")

    def test_status_choices_labels(self):
        """Test that status choices have correct display labels."""
        choices_dict = dict(StatusChoices.choices)
        self.assertEqual(choices_dict["active"], "Active")
        self.assertEqual(choices_dict["suspended"], "Suspended")

    def test_all_status_choices_present(self):
        """Test that all expected status choices are present."""
        self.assertEqual(len(StatusChoices.choices), 2)
        choice_values = [choice[0] for choice in StatusChoices.choices]
        self.assertIn("active", choice_values)
        self.assertIn("suspended", choice_values)


@pytest.mark.unit
class TestUserModelEdgeCases(TestCase):
    """Test edge cases and boundary conditions for CustomUser model."""

    @pytest.mark.django_db
    def test_user_with_maximum_length_fields(self):
        """Test user creation with maximum field lengths."""
        # Email field max_length is 254 (Django default)
        long_email = "a" * 240 + "@example.com"  # 252 characters
        long_username = "a" * 150  # Username max_length is 150

        user = CustomUserFactory(email=long_email, username=long_username)

        self.assertEqual(user.email, long_email)
        self.assertEqual(user.username, long_username)

    @pytest.mark.django_db
    def test_user_with_special_characters(self):
        """Test user creation with special characters in fields."""
        special_username = "user123_-."
        user = CustomUserFactory(username=special_username)

        self.assertEqual(user.username, special_username)

    @pytest.mark.django_db
    def test_user_inheritance_properties(self):
        """Test that CustomUser properly inherits from base classes."""
        user = CustomUserFactory()

        # AbstractBaseUser properties
        self.assertTrue(hasattr(user, "password"))
        self.assertTrue(hasattr(user, "last_login"))

        # PermissionsMixin properties
        self.assertTrue(hasattr(user, "is_superuser"))
        self.assertTrue(hasattr(user, "groups"))
        self.assertTrue(hasattr(user, "user_permissions"))

        # baseModel properties
        self.assertTrue(hasattr(user, "created_at"))
        self.assertTrue(hasattr(user, "updated_at"))

    @pytest.mark.django_db
    def test_user_status_field_choices(self):
        """Test that status field accepts only valid choices."""
        # Valid choices should work
        active_user = CustomUserFactory(status=StatusChoices.ACTIVE)
        suspended_user = CustomUserFactory(status=StatusChoices.SUSPENDED)

        self.assertEqual(active_user.status, StatusChoices.ACTIVE)
        self.assertEqual(suspended_user.status, StatusChoices.SUSPENDED)
