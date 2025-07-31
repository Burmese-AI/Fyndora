"""
Factory classes for creating test instances of Invitation models.
"""

from datetime import timedelta
from uuid import uuid4

import factory
from django.utils import timezone

from apps.invitations.models import Invitation

from .organization_factories import OrganizationFactory, OrganizationMemberFactory


class InvitationFactory(factory.django.DjangoModelFactory):
    """Factory for creating Invitation instances."""

    class Meta:
        model = Invitation

    invitation_id = factory.LazyFunction(uuid4)
    organization = factory.SubFactory(OrganizationFactory)
    email = factory.Faker("email")
    invited_by = factory.SubFactory(OrganizationMemberFactory)
    token = factory.LazyFunction(uuid4)
    is_used = False
    is_active = True
    expired_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))


class ExpiredInvitationFactory(InvitationFactory):
    """Factory for creating expired invitations."""

    expired_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))


class UsedInvitationFactory(InvitationFactory):
    """Factory for creating used invitations."""

    is_used = True
    is_active = False


class InactiveInvitationFactory(InvitationFactory):
    """Factory for creating inactive invitations."""

    is_active = False


class InvitationWithSpecificEmailFactory(InvitationFactory):
    """Factory for creating invitations with a specific email."""

    @factory.lazy_attribute
    def email(self):
        return (
            self.email_address
            if hasattr(self, "email_address")
            else factory.Faker("email").generate()
        )


class InvitationForOrganizationFactory(InvitationFactory):
    """Factory for creating invitations for a specific organization."""

    @factory.lazy_attribute
    def organization(self):
        return (
            self.target_organization
            if hasattr(self, "target_organization")
            else factory.SubFactory(OrganizationFactory)
        )

    @factory.lazy_attribute
    def invited_by(self):
        # Create an organization member for the target organization
        if hasattr(self, "target_organization"):
            return OrganizationMemberFactory(organization=self.target_organization)
        return factory.SubFactory(OrganizationMemberFactory)
