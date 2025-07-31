"""
Factory Boy factories for Remittance models.
"""

from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.remittance.constants import RemittanceStatus
from apps.remittance.models import Remittance

from .organization_factories import OrganizationMemberFactory
from .workspace_factories import WorkspaceTeamFactory


class RemittanceFactory(factory.django.DjangoModelFactory):
    """Factory for creating remittance instances."""

    class Meta:
        model = Remittance

    workspace_team = factory.SubFactory(WorkspaceTeamFactory)
    due_amount = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True, min_value=1
    )
    paid_amount = Decimal("0.00")
    status = RemittanceStatus.PENDING
    confirmed_by = None
    confirmed_at = None
    paid_within_deadlines = True
    review_notes = factory.Faker("text", max_nb_chars=200)


class PendingRemittanceFactory(RemittanceFactory):
    """Factory for creating pending remittances."""

    status = RemittanceStatus.PENDING
    paid_amount = Decimal("0.00")


class PartiallyPaidRemittanceFactory(RemittanceFactory):
    """Factory for creating partially paid remittances."""

    status = RemittanceStatus.PARTIAL
    due_amount = Decimal("1000.00")
    paid_amount = Decimal("500.00")


class PaidRemittanceFactory(RemittanceFactory):
    """Factory for creating fully paid remittances."""

    status = RemittanceStatus.PAID
    due_amount = Decimal("1000.00")
    paid_amount = Decimal("1000.00")
    confirmed_by = factory.SubFactory(OrganizationMemberFactory)
    confirmed_at = factory.LazyFunction(timezone.now)


class OverdueRemittanceFactory(RemittanceFactory):
    """Factory for creating overdue remittances."""

    status = RemittanceStatus.PENDING
    paid_within_deadlines = False

    @factory.lazy_attribute
    def workspace_team(self):
        # Create a workspace team with an expired workspace
        from .workspace_factories import WorkspaceFactory

        past_date = timezone.now().date() - timedelta(days=30)
        workspace = WorkspaceFactory(end_date=past_date)
        return WorkspaceTeamFactory(workspace=workspace)


class LargeAmountRemittanceFactory(RemittanceFactory):
    """Factory for creating large amount remittances."""

    due_amount = factory.Faker(
        "pydecimal", left_digits=6, right_digits=2, positive=True, min_value=10000
    )


class SmallAmountRemittanceFactory(RemittanceFactory):
    """Factory for creating small amount remittances."""

    due_amount = factory.Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=1,
        max_value=100,
    )


class RemittanceWithNotesFactory(RemittanceFactory):
    """Factory for creating remittances with detailed review notes."""

    review_notes = factory.Faker("paragraph", nb_sentences=5)
    status = RemittanceStatus.PAID
    confirmed_by = factory.SubFactory(OrganizationMemberFactory)
    confirmed_at = factory.LazyFunction(timezone.now)
