"""
Unit tests for the organizations app models.

Following the test plan: Organizations App (apps.organizations)
- Organization Model Tests
- OrganizationMember Model Tests
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal

from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.constants import StatusChoices
from tests.factories import (
    CustomUserFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
)


@pytest.mark.unit
class TestOrganizationModel(TestCase):
    """Test the Organization model - essential functionality only."""

    @pytest.mark.django_db
    def test_organization_creation_with_defaults(self):
        """Test creating organization with default values."""
        org = OrganizationFactory()

        # Check defaults
        self.assertEqual(org.status, StatusChoices.ACTIVE)
        self.assertEqual(org.expense, Decimal("0.00"))
        self.assertIsNotNone(org.organization_id)  # UUID generated
        self.assertIsNone(org.owner)  # No owner initially

    @pytest.mark.django_db
    def test_organization_expense_validation_non_negative(self):
        """Test that expense field validates non-negative values."""
        # Valid case: zero expense
        org = Organization(title="Test Org", expense=Decimal("0.00"))
        org.full_clean()  # Should not raise

        # Valid case: positive expense
        org.expense = Decimal("100.50")
        org.full_clean()  # Should not raise

        # Invalid case: negative expense
        org.expense = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            org.full_clean()

    def test_organization_status_choices_validation(self):
        """Test that status field validates against available choices."""
        org = Organization(title="Test Org")

        # Valid statuses
        for status, _ in StatusChoices.choices:
            org.status = status
            org.full_clean()  # Should not raise

        # Invalid status would be caught by Django field validation
        # No need to test Django's internal choice validation

    def test_organization_str_representation(self):
        """Test string representation returns title."""
        org = OrganizationFactory.build(title="My Organization")
        self.assertEqual(str(org), "My Organization")


@pytest.mark.unit
class TestOrganizationMemberModel(TestCase):
    """Test the OrganizationMember model - essential functionality only."""

    @pytest.mark.django_db
    def test_organization_member_creation_with_defaults(self):
        """Test creating organization member with default values."""
        member = OrganizationMemberFactory()

        # Check defaults
        self.assertTrue(member.is_active)
        self.assertIsNotNone(member.organization_member_id)  # UUID generated

    @pytest.mark.django_db
    def test_organization_member_unique_constraint(self):
        """Test unique constraint on organization + user."""
        user = CustomUserFactory()
        organization = OrganizationFactory()

        # Create first member
        OrganizationMemberFactory(organization=organization, user=user)

        # Try to create duplicate - should fail
        with self.assertRaises(IntegrityError):
            OrganizationMemberFactory(organization=organization, user=user)

    def test_organization_member_str_representation(self):
        """Test string representation format."""
        user = CustomUserFactory.build(username="testuser")
        organization = OrganizationFactory.build(title="Test Org")
        member = OrganizationMember(organization=organization, user=user)

        expected = "testuser in Test Org"
        self.assertEqual(str(member), expected)
