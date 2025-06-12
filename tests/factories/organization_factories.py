"""
Factory Boy factories for Organization models.
"""

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal

from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.constants import StatusChoices
from tests.factories.user_factories import CustomUserFactory


class OrganizationFactory(DjangoModelFactory):
    """Factory for creating Organization instances."""

    class Meta:
        model = Organization

    title = factory.Sequence(lambda n: f"Organization {n}")
    description = factory.Faker("text", max_nb_chars=200)
    status = StatusChoices.ACTIVE
    expense = Decimal("0.00")

    # Owner will be set separately when needed


class OrganizationWithOwnerFactory(OrganizationFactory):
    """Factory for creating Organization with an owner."""

    class Meta:
        model = Organization
        skip_postgeneration_save = True

    @factory.post_generation
    def owner(self, create, extracted, **kwargs):
        """Create an owner for the organization."""
        if not create:
            return

        # Create a user and make them a member, then set as owner
        owner_user = CustomUserFactory()
        member = OrganizationMemberFactory(organization=self, user=owner_user)
        self.owner = member
        self.save()


class OrganizationMemberFactory(DjangoModelFactory):
    """Factory for creating OrganizationMember instances."""

    class Meta:
        model = OrganizationMember

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(CustomUserFactory)
    is_active = True


class InactiveOrganizationMemberFactory(OrganizationMemberFactory):
    """Factory for creating inactive organization members."""

    is_active = False


class ArchivedOrganizationFactory(OrganizationFactory):
    """Factory for creating archived organizations."""

    title = factory.Sequence(lambda n: f"Archived Organization {n}")
    status = StatusChoices.ARCHIVED
