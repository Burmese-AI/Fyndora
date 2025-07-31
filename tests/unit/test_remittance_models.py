"""
Unit tests for Remittance models.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.remittance.models import Remittance
from apps.remittance.constants import RemittanceStatus
from tests.factories import (
    RemittanceFactory,
    PendingRemittanceFactory,
    PartiallyPaidRemittanceFactory,
    PaidRemittanceFactory,
    OverdueRemittanceFactory,
    WorkspaceTeamFactory,
    WorkspaceFactory,
    OrganizationMemberFactory,
)


@pytest.mark.django_db
class TestRemittanceModel:
    """Test the Remittance model functionality."""

    def test_remittance_creation(self):
        """Test basic remittance creation."""
        remittance = RemittanceFactory()
        
        assert isinstance(remittance, Remittance)
        assert remittance.remittance_id is not None
        assert remittance.workspace_team is not None
        assert remittance.due_amount >= 0
        assert remittance.paid_amount >= 0
        assert remittance.status in [choice[0] for choice in RemittanceStatus.choices]
        assert remittance.paid_within_deadlines is True

    def test_remittance_str_representation(self):
        """Test string representation of remittance."""
        remittance = RemittanceFactory(status=RemittanceStatus.PENDING)
        
        str_repr = str(remittance)
        assert str(remittance.remittance_id) in str_repr
        assert remittance.workspace.title in str_repr
        assert "Pending" in str_repr

    def test_workspace_property(self):
        """Test workspace property for backward compatibility."""
        remittance = RemittanceFactory()
        
        assert remittance.workspace == remittance.workspace_team.workspace

    def test_update_status_pending(self):
        """Test status update when paid_amount is 0."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00")
        )
        
        remittance.update_status()
        assert remittance.status == RemittanceStatus.PENDING

    def test_update_status_partial(self):
        """Test status update when partially paid."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("500.00")
        )
        
        remittance.update_status()
        assert remittance.status == RemittanceStatus.PARTIAL

    def test_update_status_paid(self):
        """Test status update when fully paid."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00")
        )
        
        remittance.update_status()
        assert remittance.status == RemittanceStatus.PAID

    def test_update_status_overpaid(self):
        """Test status update when overpaid."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("1200.00")
        )
        
        remittance.update_status()
        assert remittance.status == RemittanceStatus.PAID

    def test_check_if_overdue_not_overdue(self):
        """Test check_if_overdue when workspace is not ended."""
        future_date = timezone.now().date() + timedelta(days=30)
        workspace = WorkspaceFactory(end_date=future_date)
        workspace_team = WorkspaceTeamFactory(workspace=workspace)
        remittance = RemittanceFactory(
            workspace_team=workspace_team,
            status=RemittanceStatus.PENDING,
            paid_within_deadlines=True
        )
        
        remittance.check_if_overdue()
        assert remittance.paid_within_deadlines is True

    def test_check_if_overdue_is_overdue(self):
        """Test check_if_overdue when workspace has ended and not paid."""
        past_date = timezone.now().date() - timedelta(days=30)
        workspace = WorkspaceFactory(end_date=past_date)
        workspace_team = WorkspaceTeamFactory(workspace=workspace)
        remittance = RemittanceFactory(
            workspace_team=workspace_team,
            status=RemittanceStatus.PENDING,
            paid_within_deadlines=True
        )
        
        remittance.check_if_overdue()
        assert remittance.paid_within_deadlines is False

    def test_check_if_overdue_already_paid(self):
        """Test check_if_overdue when already paid - should not change deadline status."""
        past_date = timezone.now().date() - timedelta(days=30)
        workspace = WorkspaceFactory(end_date=past_date)
        workspace_team = WorkspaceTeamFactory(workspace=workspace)
        remittance = RemittanceFactory(
            workspace_team=workspace_team,
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
            paid_within_deadlines=True
        )
        
        remittance.check_if_overdue()
        assert remittance.paid_within_deadlines is True

    def test_clean_valid_payment(self):
        """Test clean method with valid payment amount."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("800.00")
        )
        
        # Should not raise any exception
        remittance.clean()

    def test_clean_overpayment_raises_error(self):
        """Test clean method raises error when paid amount exceeds due amount."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("1200.00")
        )
        
        with pytest.raises(ValidationError) as exc_info:
            remittance.clean()
        
        assert "Paid amount cannot exceed the due amount" in str(exc_info.value)

    def test_save_updates_status_and_overdue(self):
        """Test save method calls update_status and check_if_overdue."""
        past_date = timezone.now().date() - timedelta(days=30)
        workspace = WorkspaceFactory(end_date=past_date)
        workspace_team = WorkspaceTeamFactory(workspace=workspace)
        
        remittance = Remittance(
            workspace_team=workspace_team,
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("500.00"),
            paid_within_deadlines=True
        )
        
        remittance.save()
        
        # Status should be updated to PARTIAL
        assert remittance.status == RemittanceStatus.PARTIAL
        # Should be marked as overdue
        assert remittance.paid_within_deadlines is False

    def test_meta_ordering(self):
        """Test model meta ordering by created_at descending."""
        # Create remittances with different creation times
        RemittanceFactory()
        RemittanceFactory()
        
        remittances = list(Remittance.objects.all())
        
        # Should be ordered by created_at descending (newest first)
        assert remittances[0].created_at >= remittances[1].created_at

    def test_meta_indexes(self):
        """Test that model has proper database indexes."""
        meta = Remittance._meta
        index_fields = []
        
        for index in meta.indexes:
            index_fields.extend(index.fields)
        
        assert "status" in index_fields
        assert "paid_within_deadlines" in index_fields


@pytest.mark.django_db
class TestRemittanceFactories:
    """Test remittance factories create valid instances."""

    def test_pending_remittance_factory(self):
        """Test PendingRemittanceFactory creates pending remittance."""
        remittance = PendingRemittanceFactory()
        
        assert remittance.status == RemittanceStatus.PENDING
        assert remittance.paid_amount == Decimal("0.00")
        assert remittance.confirmed_by is None
        assert remittance.confirmed_at is None

    def test_partially_paid_remittance_factory(self):
        """Test PartiallyPaidRemittanceFactory creates partially paid remittance."""
        remittance = PartiallyPaidRemittanceFactory()
        
        assert remittance.status == RemittanceStatus.PARTIAL
        assert remittance.due_amount == Decimal("1000.00")
        assert remittance.paid_amount == Decimal("500.00")
        assert remittance.paid_amount < remittance.due_amount

    def test_paid_remittance_factory(self):
        """Test PaidRemittanceFactory creates fully paid remittance."""
        remittance = PaidRemittanceFactory()
        
        assert remittance.status == RemittanceStatus.PAID
        assert remittance.due_amount == Decimal("1000.00")
        assert remittance.paid_amount == Decimal("1000.00")
        assert remittance.confirmed_by is not None
        assert remittance.confirmed_at is not None

    def test_overdue_remittance_factory(self):
        """Test OverdueRemittanceFactory creates overdue remittance."""
        remittance = OverdueRemittanceFactory()
        
        assert remittance.status == RemittanceStatus.PENDING
        assert remittance.paid_within_deadlines is False
        # Workspace should have ended
        assert remittance.workspace_team.workspace.end_date < timezone.now().date()


@pytest.mark.django_db
class TestRemittanceValidation:
    """Test remittance model validation."""

    def test_due_amount_minimum_validation(self):
        """Test due_amount minimum value validation."""
        with pytest.raises(ValidationError):
            remittance = RemittanceFactory(due_amount=Decimal("-100.00"))
            remittance.full_clean()

    def test_paid_amount_minimum_validation(self):
        """Test paid_amount minimum value validation."""
        with pytest.raises(ValidationError):
            remittance = RemittanceFactory(paid_amount=Decimal("-50.00"))
            remittance.full_clean()

    def test_workspace_team_required(self):
        """Test workspace_team is required."""
        with pytest.raises(ValidationError):
            remittance = Remittance(
                workspace_team=None,
                due_amount=Decimal("1000.00")
            )
            remittance.full_clean()

    def test_unique_workspace_team_constraint(self):
        """Test one-to-one relationship with workspace_team."""
        workspace_team = WorkspaceTeamFactory()
        
        # First remittance should be fine
        RemittanceFactory(workspace_team=workspace_team)
        
        # Second remittance with same workspace_team should fail
        with pytest.raises(Exception):  # IntegrityError or ValidationError
            RemittanceFactory(workspace_team=workspace_team)


@pytest.mark.django_db
class TestRemittanceBusinessLogic:
    """Test remittance business logic scenarios."""

    def test_payment_progression_workflow(self):
        """Test complete payment progression from pending to paid."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00")
        )
        
        # Initially pending
        assert remittance.status == RemittanceStatus.PENDING
        
        # Make partial payment
        remittance.paid_amount = Decimal("400.00")
        remittance.save()
        assert remittance.status == RemittanceStatus.PARTIAL
        
        # Complete payment
        remittance.paid_amount = Decimal("1000.00")
        remittance.save()
        assert remittance.status == RemittanceStatus.PAID

    def test_confirmation_workflow(self):
        """Test remittance confirmation workflow."""
        member = OrganizationMemberFactory()
        remittance = PaidRemittanceFactory(
            confirmed_by=None,
            confirmed_at=None
        )
        
        # Confirm the remittance
        remittance.confirmed_by = member
        remittance.confirmed_at = timezone.now()
        remittance.save()
        
        assert remittance.confirmed_by == member
        assert remittance.confirmed_at is not None

    def test_overdue_detection_workflow(self):
        """Test overdue detection workflow."""
        # Create workspace that ends today
        today = timezone.now().date()
        workspace = WorkspaceFactory(end_date=today)
        workspace_team = WorkspaceTeamFactory(workspace=workspace)
        
        remittance = RemittanceFactory(
            workspace_team=workspace_team,
            status=RemittanceStatus.PENDING,
            paid_within_deadlines=True
        )
        
        # Simulate time passing (workspace has ended)
        workspace.end_date = today - timedelta(days=1)
        workspace.save()
        
        # Check overdue status
        remittance.check_if_overdue()
        assert remittance.paid_within_deadlines is False