"""
Factory Boy factories for Entry models.
"""

import uuid
from decimal import Decimal

import factory
from django.contrib.contenttypes.models import ContentType
from factory.django import DjangoModelFactory

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.teams.constants import TeamMemberRole
from tests.factories.organization_factories import OrganizationMemberFactory
from tests.factories.team_factories import TeamMemberFactory, TeamFactory
from tests.factories.workspace_factories import WorkspaceFactory, WorkspaceTeamFactory


class EntryFactory(DjangoModelFactory):
    """Factory for creating financial transaction Entry instances."""

    class Meta:
        model = Entry

    entry_id = factory.LazyFunction(uuid.uuid4)
    submitter = factory.SubFactory(TeamMemberFactory, role=TeamMemberRole.SUBMITTER)
    submitter_content_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get_for_model(obj.submitter)
    )
    submitter_object_id = factory.LazyAttribute(lambda obj: obj.submitter.pk)
    entry_type = factory.Iterator([choice[0] for choice in EntryType.choices])
    amount = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    description = factory.Faker("sentence", nb_words=8)
    status = EntryStatus.PENDING_REVIEW  # Default status
    workspace = factory.LazyAttribute(lambda obj: WorkspaceFactory())
    is_flagged = False

    @factory.lazy_attribute
    def workspace_team(self):
        """
        Create workspace_team based on submitter type.
        If submitter has a team attribute, use it; otherwise create a new team.
        """
        if hasattr(self.submitter, "team"):
            team = self.submitter.team
        else:
            # Create a team if the submitter doesn't have one (e.g., CustomUser)
            team = TeamFactory(organization=self.workspace.organization)

        return WorkspaceTeamFactory(workspace=self.workspace, team=team)

    reviewed_by = None
    review_notes = None


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

    status = EntryStatus.PENDING_REVIEW
    description = factory.Sequence(
        lambda n: f"Financial transaction awaiting review {n}"
    )


class ApprovedEntryFactory(EntryFactory):
    """Factory for creating approved financial transactions."""

    status = EntryStatus.APPROVED
    description = factory.Sequence(lambda n: f"Approved financial transaction {n}")
    reviewed_by = factory.SubFactory(
        "tests.factories.organization_factories.OrganizationMemberFactory"
    )
    review_notes = "This entry has been approved."


class RejectedEntryFactory(EntryFactory):
    """Factory for creating rejected financial transactions."""

    status = EntryStatus.REJECTED
    reviewed_by = factory.SubFactory(OrganizationMemberFactory)
    review_notes = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Rejected financial transaction {n}")


class FlaggedEntryFactory(EntryFactory):
    """Factory for creating flagged financial transactions."""

    is_flagged = True
    reviewed_by = factory.SubFactory(OrganizationMemberFactory)
    review_notes = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Flagged financial transaction {n}")


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
            self.status = EntryStatus.PENDING_REVIEW
        else:
            self.is_flagged = False
            self.status = status

        # Assign appropriate reviewer based on status
        if (
            self.status in [EntryStatus.APPROVED, EntryStatus.REJECTED]
            or self.is_flagged
        ):
            # Use OrganizationMember instead of TeamMember
            self.reviewed_by = OrganizationMemberFactory()
            if self.is_flagged:
                self.review_notes = "Financial transaction has been flagged for review."
            else:
                self.review_notes = f"Financial transaction {self.status} after review."
            self.save()
