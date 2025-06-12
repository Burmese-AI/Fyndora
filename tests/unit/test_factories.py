"""
Tests for our test factories.

These tests ensure our factories create valid model instances.
"""

import pytest
from django.test import TestCase
from django.db import IntegrityError

from tests.factories import (
    CustomUserFactory,
    StaffUserFactory,
    SuperUserFactory,
    SuspendedUserFactory,
    OrganizationFactory,
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
    InactiveOrganizationMemberFactory,
    ArchivedOrganizationFactory,
)
from apps.accounts.models import CustomUser
from apps.organizations.models import Organization, OrganizationMember


@pytest.mark.unit
class TestUserFactories(TestCase):
    """Test user factories create valid instances."""

    @pytest.mark.django_db
    def test_custom_user_factory_creates_valid_user(self):
        """Test CustomUserFactory creates a valid user."""
        user = CustomUserFactory()

        self.assertIsInstance(user, CustomUser)
        self.assertTrue(user.email)
        self.assertTrue(user.username)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    @pytest.mark.django_db
    def test_staff_user_factory_creates_staff_user(self):
        """Test StaffUserFactory creates a staff user."""
        user = StaffUserFactory()

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)

    @pytest.mark.django_db
    def test_superuser_factory_creates_superuser(self):
        """Test SuperUserFactory creates a superuser."""
        user = SuperUserFactory()

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    @pytest.mark.django_db
    def test_suspended_user_factory_creates_suspended_user(self):
        """Test SuspendedUserFactory creates a suspended user."""
        user = SuspendedUserFactory()

        self.assertFalse(user.is_active)

    @pytest.mark.django_db
    def test_user_factories_create_unique_users(self):
        """Test that factories create users with unique emails and usernames."""
        user1 = CustomUserFactory()
        user2 = CustomUserFactory()

        self.assertNotEqual(user1.email, user2.email)
        self.assertNotEqual(user1.username, user2.username)


@pytest.mark.unit
class TestOrganizationFactories(TestCase):
    """Test organization factories create valid instances."""

    @pytest.mark.django_db
    def test_organization_factory_creates_valid_organization(self):
        """Test OrganizationFactory creates a valid organization."""
        org = OrganizationFactory()

        self.assertIsInstance(org, Organization)
        self.assertTrue(org.title)
        self.assertIsNone(org.owner)  # No owner by default

    @pytest.mark.django_db
    def test_organization_with_owner_factory_creates_owner(self):
        """Test OrganizationWithOwnerFactory creates organization with owner."""
        org = OrganizationWithOwnerFactory()

        self.assertIsNotNone(org.owner)
        self.assertIsInstance(org.owner, OrganizationMember)
        self.assertEqual(org.owner.organization, org)

    @pytest.mark.django_db
    def test_organization_member_factory_creates_valid_member(self):
        """Test OrganizationMemberFactory creates a valid member."""
        member = OrganizationMemberFactory()

        self.assertIsInstance(member, OrganizationMember)
        self.assertIsInstance(member.organization, Organization)
        self.assertIsInstance(member.user, CustomUser)
        self.assertTrue(member.is_active)

    @pytest.mark.django_db
    def test_inactive_organization_member_factory(self):
        """Test InactiveOrganizationMemberFactory creates inactive member."""
        member = InactiveOrganizationMemberFactory()

        self.assertFalse(member.is_active)

    @pytest.mark.django_db
    def test_archived_organization_factory(self):
        """Test ArchivedOrganizationFactory creates archived organization."""
        org = ArchivedOrganizationFactory()

        from apps.organizations.constants import StatusChoices

        self.assertEqual(org.status, StatusChoices.ARCHIVED)


@pytest.mark.unit
class TestFactoryIntegration(TestCase):
    """Test factories work together properly."""

    @pytest.mark.django_db
    def test_multiple_members_same_organization(self):
        """Test creating multiple members for same organization."""
        org = OrganizationFactory()

        member1 = OrganizationMemberFactory(organization=org)
        member2 = OrganizationMemberFactory(organization=org)

        self.assertEqual(member1.organization, org)
        self.assertEqual(member2.organization, org)
        self.assertNotEqual(member1.user, member2.user)

    @pytest.mark.django_db
    def test_factories_respect_unique_constraints(self):
        """Test that factories respect model unique constraints."""
        user = CustomUserFactory()
        org = OrganizationFactory()

        # Create first member
        OrganizationMemberFactory(organization=org, user=user)

        # Try to create duplicate - should fail
        with self.assertRaises(IntegrityError):
            OrganizationMemberFactory(organization=org, user=user)
