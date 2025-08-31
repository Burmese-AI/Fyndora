"""
Unit tests for invitation forms.
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django import forms

from apps.invitations.forms import InvitationCreateForm
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)


@pytest.mark.unit
class TestInvitationCreateForm(TestCase):
    """Test cases for the InvitationCreateForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.future_date = timezone.now() + timedelta(days=7)

    def test_form_fields(self):
        """Test that the form has the correct fields."""
        form = InvitationCreateForm()

        assert "email" in form.fields
        assert "expired_at" in form.fields
        assert len(form.fields) == 2

    def test_form_widgets(self):
        """Test that the form has the correct widgets and attributes."""
        form = InvitationCreateForm()

        # Test email widget
        email_widget = form.fields["email"].widget
        assert isinstance(email_widget, forms.EmailInput)
        assert email_widget.attrs["class"] == "input input-bordered w-full"
        assert email_widget.attrs["placeholder"] == "Enter invitee email"

        # Test expired_at widget
        expired_widget = form.fields["expired_at"].widget
        assert isinstance(expired_widget, forms.DateInput)
        assert expired_widget.attrs["class"] == "input input-bordered w-full"
        # Note: DateInput doesn't have a 'type' attribute by default

    def test_form_initialization_with_organization_and_user(self):
        """Test form initialization with organization and user."""
        form = InvitationCreateForm(organization=self.organization, user=self.user)

        assert form.organization == self.organization
        assert form.user == self.user

    def test_form_clean_success(self):
        """Test successful form cleaning with valid data."""
        form_data = {"email": "test@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert form.is_valid()
        cleaned_data = form.clean()
        assert cleaned_data["email"] == "test@example.com"
        assert cleaned_data["expired_at"] == self.future_date

    def test_form_clean_missing_organization(self):
        """Test form cleaning fails when organization is missing."""
        form_data = {"email": "test@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(data=form_data, organization=None, user=self.user)

        assert not form.is_valid()
        assert "Organization ID and User are required." in str(form.errors["__all__"])

    def test_form_clean_missing_user(self):
        """Test form cleaning fails when user is missing."""
        form_data = {"email": "test@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=None
        )

        assert not form.is_valid()
        assert "Organization ID and User are required." in str(form.errors["__all__"])

    def test_form_clean_user_not_organization_member(self):
        """Test form cleaning fails when user is not an organization member."""
        # Create a different user who is not a member of the organization
        other_user = CustomUserFactory()

        form_data = {"email": "test@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=other_user
        )

        assert not form.is_valid()
        assert "You must be a member of the organization to send an invitation." in str(
            form.errors["__all__"]
        )

    def test_form_clean_email_already_organization_member(self):
        """Test form cleaning fails when email belongs to existing organization member."""
        # Create a user who is already a member of the organization
        existing_member = CustomUserFactory(email="existing@example.com")
        OrganizationMemberFactory(organization=self.organization, user=existing_member)

        form_data = {"email": "existing@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert not form.is_valid()
        assert "User with this email is already a member of the organization." in str(
            form.errors["__all__"]
        )

    def test_form_clean_email_user_exists_but_not_member(self):
        """Test form cleaning succeeds when email belongs to user who is not an organization member."""
        # Create a user who exists but is not a member of this organization
        other_organization = OrganizationFactory()
        existing_user = CustomUserFactory(email="existing@example.com")
        OrganizationMemberFactory(organization=other_organization, user=existing_user)

        form_data = {"email": "existing@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert form.is_valid()

    def test_form_clean_email_user_does_not_exist(self):
        """Test form cleaning succeeds when email belongs to non-existent user."""
        form_data = {"email": "newuser@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert form.is_valid()

    def test_clean_expired_at_past_date(self):
        """Test expired_at validation fails for past dates."""
        past_date = timezone.now() - timedelta(days=1)

        form_data = {"email": "test@example.com", "expired_at": past_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert not form.is_valid()
        assert "Expiration date must be in the future." in str(
            form.errors["expired_at"]
        )

    def test_clean_expired_at_future_date(self):
        """Test expired_at validation succeeds for future dates."""
        form_data = {"email": "test@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert form.is_valid()
        cleaned_expired_at = form.clean_expired_at()
        assert cleaned_expired_at == self.future_date

    def test_clean_expired_at_current_time(self):
        """Test expired_at validation fails for current time."""
        current_time = timezone.now()

        form_data = {"email": "test@example.com", "expired_at": current_time}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert not form.is_valid()
        assert "Expiration date must be in the future." in str(
            form.errors["expired_at"]
        )

    def test_form_save_with_valid_data(self):
        """Test form save method with valid data."""
        form_data = {"email": "test@example.com", "expired_at": self.future_date}

        form = InvitationCreateForm(
            data=form_data, organization=self.organization, user=self.user
        )

        assert form.is_valid()
        invitation = form.save(commit=False)

        # Set the required fields that are not in the form
        invitation.organization = self.organization
        invitation.invited_by = self.organization_member

        # Test the form data without actually saving to avoid signal triggers
        assert invitation.email == "test@example.com"
        assert invitation.organization == self.organization
        assert invitation.invited_by == self.organization_member
        assert invitation.expired_at == self.future_date
        assert not invitation.is_used
        assert invitation.is_active
        assert invitation.token is not None
        assert invitation.invitation_id is not None

        # Test that the form can be saved (without triggering signals)
        # We'll just verify the form data is correct
        assert form.cleaned_data["email"] == "test@example.com"
        assert form.cleaned_data["expired_at"] == self.future_date
