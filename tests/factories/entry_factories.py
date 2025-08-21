"""Factory Boy factories for Entry models."""

import uuid
from decimal import Decimal
from datetime import date
from django.utils import timezone

import factory
from factory.django import DjangoModelFactory

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.currencies.models import Currency
from tests.factories.organization_factories import (
    OrganizationMemberFactory,
    OrganizationFactory,
    OrganizationExchangeRateFactory,
)
from tests.factories.team_factories import TeamMemberFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceExchangeRateFactory,
)


class EntryFactory(DjangoModelFactory):
    """Factory for creating financial transaction Entry instances."""

    class Meta:
        model = Entry

    entry_id = factory.LazyFunction(uuid.uuid4)
    entry_type = factory.Iterator([choice[0] for choice in EntryType.choices])
    description = factory.Faker("sentence", nb_words=8)
    organization = factory.SubFactory(OrganizationFactory)
    workspace = factory.SubFactory(WorkspaceFactory)
    workspace_team = factory.SubFactory(WorkspaceTeamFactory)
    amount = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    occurred_at = factory.LazyFunction(lambda: date.today())
    currency = factory.LazyFunction(
        lambda: Currency.objects.get_or_create(code="USD", name="US Dollar")[0]
    )
    exchange_rate_used = Decimal("1.00")
    org_exchange_rate_ref = factory.SubFactory(OrganizationExchangeRateFactory)
    workspace_exchange_rate_ref = factory.SubFactory(WorkspaceExchangeRateFactory)
    submitted_by_org_member = factory.SubFactory(OrganizationMemberFactory)
    submitted_by_team_member = None
    status = EntryStatus.PENDING
    status_last_updated_at = None
    last_status_modified_by = None
    status_note = None
    is_flagged = False

    @factory.post_generation
    def setup_relationships(self, create, extracted, **kwargs):
        """Ensure all relationships are consistent."""
        if not create:
            return

        # Ensure workspace belongs to the same organization
        if self.workspace.organization != self.organization:
            self.workspace.organization = self.organization
            self.workspace.save()

        # Ensure workspace_team uses the same workspace
        if self.workspace_team.workspace != self.workspace:
            self.workspace_team.workspace = self.workspace
            self.workspace_team.save()

        # Get or create exchange rate references to avoid duplicates
        if self.org_exchange_rate_ref:
            from apps.organizations.models import OrganizationExchangeRate

            org_rate, created = OrganizationExchangeRate.objects.get_or_create(
                organization=self.organization,
                currency=self.currency,
                effective_date=self.occurred_at,
                defaults={"rate": self.org_exchange_rate_ref.rate},
            )
            self.org_exchange_rate_ref = org_rate

        if self.workspace_exchange_rate_ref:
            from apps.workspaces.models import WorkspaceExchangeRate

            workspace_rate, created = WorkspaceExchangeRate.objects.get_or_create(
                workspace=self.workspace,
                currency=self.currency,
                effective_date=self.occurred_at,
                defaults={"rate": self.workspace_exchange_rate_ref.rate},
            )
            self.workspace_exchange_rate_ref = workspace_rate

        # Ensure submitted_by_org_member belongs to the same organization
        if (
            self.submitted_by_org_member
            and self.submitted_by_org_member.organization != self.organization
        ):
            self.submitted_by_org_member.organization = self.organization
            self.submitted_by_org_member.save()


class IncomeEntryFactory(EntryFactory):
    """Factory for creating donation/contribution entries."""

    entry_type = EntryType.INCOME
    description = factory.Sequence(
        lambda n: f"Donation collection from supporters batch {n}"
    )


class DisbursementEntryFactory(EntryFactory):
    """Factory for creating expense/disbursement entries."""

    entry_type = EntryType.DISBURSEMENT
    description = factory.Sequence(lambda n: f"Campaign expense payment {n}")


class RemittanceEntryFactory(EntryFactory):
    """Factory for creating remittance payment entries."""

    entry_type = EntryType.REMITTANCE
    description = factory.Sequence(
        lambda n: f"Remittance payment to central platform {n}"
    )


class PendingEntryFactory(EntryFactory):
    """Factory for creating pending review financial transactions."""

    status = EntryStatus.PENDING
    description = factory.Sequence(
        lambda n: f"Financial transaction awaiting review {n}"
    )


class ApprovedEntryFactory(EntryFactory):
    """Factory for creating approved financial transactions."""

    status = EntryStatus.APPROVED
    description = factory.Sequence(lambda n: f"Approved financial transaction {n}")
    last_status_modified_by = factory.SubFactory(OrganizationMemberFactory)
    status_note = "This entry has been approved."
    status_last_updated_at = factory.LazyFunction(lambda: date.today())


class RejectedEntryFactory(EntryFactory):
    """Factory for creating rejected financial transactions."""

    status = EntryStatus.REJECTED
    last_status_modified_by = factory.SubFactory(OrganizationMemberFactory)
    status_note = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Rejected financial transaction {n}")
    status_last_updated_at = factory.LazyFunction(lambda: date.today())


class FlaggedEntryFactory(EntryFactory):
    """Factory for creating flagged financial transactions."""

    is_flagged = True
    last_status_modified_by = factory.SubFactory(OrganizationMemberFactory)
    status_note = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Flagged financial transaction {n}")
    status_last_updated_at = factory.LazyFunction(lambda: date.today())


class LargeAmountEntryFactory(EntryFactory):
    """Factory for creating large amount financial transactions."""

    amount = factory.LazyFunction(
        lambda: Decimal("25000.00")
    )  # Realistic large fundraising amount
    entry_type = EntryType.INCOME
    description = factory.Sequence(
        lambda n: f"Major donation from corporate sponsor {n}"
    )


class SmallAmountEntryFactory(EntryFactory):
    """Factory for creating small amount financial transactions."""

    amount = factory.LazyFunction(lambda: Decimal("50.00"))
    entry_type = EntryType.DISBURSEMENT
    description = factory.Sequence(lambda n: f"Small campaign expense {n}")


class TeamSubmittedEntryFactory(EntryFactory):
    """Factory for creating entries submitted by team members."""

    submitted_by_org_member = None
    submitted_by_team_member = factory.SubFactory(TeamMemberFactory)
    description = factory.Sequence(lambda n: f"Team submitted transaction {n}")

    @factory.post_generation
    def setup_team_relationships(self, create, extracted, **kwargs):
        """Ensure team member belongs to the workspace team."""
        if not create or not self.submitted_by_team_member:
            return

        # Ensure the team member's team matches the workspace team
        if (
            self.workspace_team
            and self.submitted_by_team_member.team != self.workspace_team.team
        ):
            self.submitted_by_team_member.team = self.workspace_team.team
            self.submitted_by_team_member.save()

        # Ensure the team member's organization matches the entry organization
        if (
            self.submitted_by_team_member.organization_member.organization
            != self.organization
        ):
            self.submitted_by_team_member.organization_member.organization = (
                self.organization
            )
            self.submitted_by_team_member.organization_member.save()


class EntryWithReviewFactory(EntryFactory):
    """Factory for creating financial transaction with review completed."""

    class Meta:
        model = Entry
        skip_postgeneration_save = True

    @factory.post_generation
    def review(self, create, extracted, **kwargs):
        """Add financial review to the transaction."""
        if not create:
            return

        # Default to approved with coordinator review
        status = extracted or EntryStatus.APPROVED

        if status == "flagged" or kwargs.get("is_flagged") is True:
            self.is_flagged = True
            self.status = EntryStatus.PENDING
        else:
            self.is_flagged = False
            self.status = status

        # Assign appropriate reviewer based on status
        if (
            self.status in [EntryStatus.APPROVED, EntryStatus.REJECTED]
            or self.is_flagged
        ):
            # Use OrganizationMember instead of TeamMember
            self.last_status_modified_by = OrganizationMemberFactory()
            self.status_last_updated_at = date.today()
            if self.is_flagged:
                self.status_note = "Financial transaction has been flagged for review."
            else:
                self.status_note = f"Financial transaction {self.status} after review."
            self.save()
            
            
class OrganizationExpenseEntryFactory(EntryFactory):
    """Factory for creating organization-level expense entries."""
    entry_type = EntryType.ORG_EXP
    submitted_by_org_member = factory.SubFactory(OrganizationMemberFactory)
    submitted_by_team_member = None
    workspace = None
    workspace_team = None
    description = factory.Sequence(lambda n: f"Organization expense {n}")
    org_exchange_rate_ref = factory.LazyAttribute(
        lambda obj: obj.org_exchange_rate_ref or None
    )


class WorkspaceExpenseEntryFactory(EntryFactory):
    """Factory for creating workspace-level expense entries."""
    entry_type = EntryType.WORKSPACE_EXP
    submitted_by_team_member = factory.SubFactory(TeamMemberFactory)
    submitted_by_org_member = None
    description = factory.Sequence(lambda n: f"Workspace expense {n}")
    workspace_exchange_rate_ref = factory.LazyAttribute(
        lambda obj: obj.workspace_exchange_rate_ref or None
    )

# in tests/factories/entry_factories.py (or wherever your entry factories live)
import factory
from apps.entries.models import Entry
from apps.entries.constants import EntryStatus
from .organization_factories import OrganizationMemberFactory
from .team_factories import TeamMemberFactory

class ReviewedEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Entry

    # You can choose either team member or org member
    submitted_by_team_member = factory.SubFactory(TeamMemberFactory)
    organization = factory.LazyAttribute(lambda o: o.submitted_by_team_member.organization_member.organization)
    workspace = None
    workspace_team = None
    entry_type = "INCOME"
    amount = 100.00
    description = "Reviewed entry"
    status = EntryStatus.REVIEWED

    last_status_modified_by = factory.SubFactory(OrganizationMemberFactory)
    status_note = "Reviewed note"
    status_last_updated_at = factory.LazyFunction(timezone.now)
