"""
Factory Boy factories for Entry models.
"""

import uuid
import factory
from factory.django import DjangoModelFactory
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

from apps.entries.models import Entry
from apps.entries.constants import EntryType
from apps.teams.constants import TeamMemberRole
from tests.factories.team_factories import (
    TeamMemberFactory,
    TeamCoordinatorFactory,
    OperationsReviewerFactory,
    WorkspaceAdminMemberFactory,
)


class EntryFactory(DjangoModelFactory):
    """Factory for creating financial transaction Entry instances."""

    class Meta:
        model = Entry

    entry_id = factory.LazyFunction(uuid.uuid4)
    submitter = factory.SubFactory(TeamMemberFactory, role=TeamMemberRole.SUBMITTER)
    submitter_content_type = factory.LazyAttribute(lambda obj: ContentType.objects.get_for_model(obj.submitter))
    submitter_object_id = factory.LazyAttribute(lambda obj: obj.submitter.pk)
    entry_type = factory.Iterator([choice[0] for choice in EntryType.choices])
    amount = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    description = factory.Faker("sentence", nb_words=8)
    status = "pending_review"  # Default status

    # reviewed_by and review_notes will be set when needed


class IncomeEntryFactory(EntryFactory):
    """Factory for creating donation/contribution entries."""

    entry_type = "income"
    description = factory.Sequence(
        lambda n: f"Donation collection from supporters batch {n}"
    )


class DisbursementEntryFactory(EntryFactory):
    """Factory for creating expense/disbursement entries."""

    entry_type = "disbursement"
    description = factory.Sequence(lambda n: f"Campaign expense payment {n}")


class RemittanceEntryFactory(EntryFactory):
    """Factory for creating remittance payment entries."""

    entry_type = "remittance"
    description = factory.Sequence(
        lambda n: f"Remittance payment to central platform {n}"
    )


class PendingEntryFactory(EntryFactory):
    """Factory for creating pending review financial transactions."""

    status = "pending_review"
    description = factory.Sequence(
        lambda n: f"Financial transaction awaiting review {n}"
    )


class ApprovedEntryFactory(EntryFactory):
    """Factory for creating approved financial transactions."""

    status = "approved"
    reviewed_by = factory.SubFactory(TeamCoordinatorFactory)
    review_notes = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Approved financial transaction {n}")


class RejectedEntryFactory(EntryFactory):
    """Factory for creating rejected financial transactions."""

    status = "rejected"
    reviewed_by = factory.SubFactory(OperationsReviewerFactory)
    review_notes = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Rejected financial transaction {n}")


class FlaggedEntryFactory(EntryFactory):
    """Factory for creating flagged financial transactions."""

    status = "flagged"
    reviewed_by = factory.SubFactory(WorkspaceAdminMemberFactory)
    review_notes = factory.Faker("sentence", nb_words=10)
    description = factory.Sequence(lambda n: f"Flagged financial transaction {n}")


class LargeAmountEntryFactory(EntryFactory):
    """Factory for creating large amount financial transactions."""

    amount = factory.LazyFunction(
        lambda: Decimal("25000.00")
    )  # Realistic large fundraising amount
    entry_type = "income"
    description = factory.Sequence(
        lambda n: f"Major donation from corporate sponsor {n}"
    )


class SmallAmountEntryFactory(EntryFactory):
    """Factory for creating small amount financial transactions."""

    amount = factory.LazyFunction(lambda: Decimal("50.00"))
    entry_type = "disbursement"
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
        status = extracted or "approved"
        self.status = status

        # Assign appropriate reviewer based on status
        if status in ["approved", "rejected", "flagged"]:
            self.reviewed_by = TeamCoordinatorFactory()
            self.review_notes = f"Financial transaction {status} after review"
            self.save()
