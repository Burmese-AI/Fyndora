"""
Unit tests for invitation forms.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.invitations.forms import InvitationCreateForm
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestInvitationCreateForm(TestCase):
    """Test cases for InvitationCreateForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(
            organization=self.organization,
            user=self.user
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'test@example.com',
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertTrue(form.is_valid())

    def test_form_invalid_email(self):
        """Test form with invalid email."""
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'invalid-email',
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_past_expiration_date(self):
        """Test form with past expiration date."""
        past_date = timezone.now() - timedelta(days=1)
        form_data = {
            'email': 'test@example.com',
            'expired_at': past_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('expired_at', form.errors)
        self.assertIn('Expiration date must be in the future', str(form.errors['expired_at']))

    def test_form_inviter_not_organization_member(self):
        """Test form when inviter is not an organization member."""
        non_member = CustomUserFactory()
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'test@example.com',
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=non_member
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('You must be a member of the organization', str(form.errors['__all__']))

    def test_form_invitee_already_member(self):
        """Test form when invitee is already an organization member."""
        existing_member_user = CustomUserFactory(email='existing@example.com')
        OrganizationMemberFactory(
            organization=self.organization,
            user=existing_member_user
        )
        
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'existing@example.com',
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('User with this email is already a member of the organization', str(form.errors['__all__']))

    def test_form_case_insensitive_email_check(self):
        """Test form email validation is case insensitive."""
        existing_member_user = CustomUserFactory(email='Existing@Example.com')
        OrganizationMemberFactory(
            organization=self.organization,
            user=existing_member_user
        )
        
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'existing@example.com',  # Different case
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('User with this email is already a member of the organization', str(form.errors['__all__']))

    def test_form_missing_email(self):
        """Test form with missing email."""
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_missing_expiration_date(self):
        """Test form with missing expiration date."""
        form_data = {
            'email': 'test@example.com'
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('expired_at', form.errors)

    def test_form_initialization_without_organization(self):
        """Test form initialization without organization parameter."""
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'test@example.com',
            'expired_at': future_date
        }
        
        # This should work but validation will fail
        form = InvitationCreateForm(
            data=form_data,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())

    def test_form_initialization_without_invited_by(self):
        """Test form initialization without user parameter."""
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'test@example.com',
            'expired_at': future_date
        }
        
        # This should work but validation will fail
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization
        )
        
        self.assertFalse(form.is_valid())

    def test_form_clean_method_order(self):
        """Test that form validation methods are called in correct order."""
        # Test with valid data first
        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            'email': 'test@example.com',
            'expired_at': future_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        # This should pass all validations
        self.assertTrue(form.is_valid())
        
        # Now test with multiple errors to see they're all caught
        existing_member_user = CustomUserFactory(email='existing@example.com')
        OrganizationMemberFactory(
            organization=self.organization,
            user=existing_member_user
        )
        
        past_date = timezone.now() - timedelta(days=1)
        form_data = {
            'email': 'existing@example.com',
            'expired_at': past_date
        }
        
        form = InvitationCreateForm(
            data=form_data,
            organization=self.organization,
            user=self.user
        )
        
        self.assertFalse(form.is_valid())
        # Should have both email and expired_at errors
        self.assertIn('__all__', form.errors)
        self.assertIn('expired_at', form.errors)