"""
Factory Boy factories for Organization models.
"""

from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.currencies.models import Currency
from apps.organizations.constants import StatusChoices
from apps.organizations.models import (
    Organization,
    OrganizationExchangeRate,
    OrganizationMember,
)
from tests.factories.user_factories import CustomUserFactory


class OrganizationFactory(DjangoModelFactory):
    """Factory for creating Organization instances."""

    class Meta:
        model = Organization

    title = factory.Sequence(lambda n: f"Organization {n}")
    description = factory.Faker("text", max_nb_chars=200)
    status = StatusChoices.ACTIVE


class OrganizationWithOwnerFactory(OrganizationFactory):
    """Factory for creating Organization with an owner."""

    class Meta:
        model = Organization
        skip_postgeneration_save = True

    @factory.post_generation
    def owner(self, create, extracted, **kwargs):
        """
        Create an owner for the organization.
        Accepts a User instance via `extracted` to be set as the owner.
        """
        if not create:
            return

        if extracted:
            # A user instance was passed in.
            owner_user = extracted
        else:
            # Create a new user.
            owner_user = CustomUserFactory()

        # Create a member for the user (or get the existing one) and set as owner.
        member, _ = OrganizationMember.objects.get_or_create(
            organization=self, user=owner_user
        )
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


class OrganizationExchangeRateFactory(DjangoModelFactory):
    """Factory for creating OrganizationExchangeRate instances."""

    class Meta:
        model = OrganizationExchangeRate

    organization = factory.SubFactory(OrganizationFactory)
    currency = factory.LazyFunction(
        lambda: Currency.objects.get_or_create(code="USD", name="US Dollar")[0]
    )
    rate = Decimal("1.25")
    effective_date = factory.LazyFunction(lambda: date.today())
    note = factory.Faker("text", max_nb_chars=100)
    added_by = factory.SubFactory(OrganizationMemberFactory)

