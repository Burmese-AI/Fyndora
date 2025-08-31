"""
Unit tests for Remittance models.
"""

from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid

from apps.remittance.models import Remittance
from apps.remittance.constants import RemittanceStatus
from tests.factories.remittance_factories import RemittanceFactory
from tests.factories.workspace_factories import WorkspaceTeamFactory, WorkspaceFactory
from tests.factories.team_factories import TeamFactory
from tests.factories.organization_factories import OrganizationFactory, OrganizationMemberFactory


@pytest.mark.django_db
class TestRemittanceModel:
    """Test the Remittance model functionality."""

    def test_remittance_creation(self):
        """Test basic remittance creation."""
        # Create a workspace team using factories - this will automatically create
        # the organization, workspace, team, and remittance (via signal)
        workspace_team = WorkspaceTeamFactory()
        
        # The remittance should be automatically created by the signal
        remittance = Remittance.objects.get(workspace_team=workspace_team)

        assert isinstance(remittance, Remittance)
        assert remittance.remittance_id is not None
        assert remittance.workspace_team == workspace_team
        assert remittance.due_amount == Decimal("0.00")  # Default value
        assert remittance.paid_amount == Decimal("0.00")  # Default value
        assert remittance.status == RemittanceStatus.PENDING  # Default value
        assert remittance.paid_within_deadlines is True  # Default value

    def test_remittance_factory_override_values(self):
        """Test that the factory can override values when creating remittance."""
        # First create a workspace team (which will have a default remittance)
        workspace_team = WorkspaceTeamFactory()
        
        # Delete the auto-created remittance so we can test the factory
        Remittance.objects.filter(workspace_team=workspace_team).delete()
        
        # Now use the factory to create a remittance with custom values
        remittance = RemittanceFactory(
            workspace_team=workspace_team,
            due_amount=Decimal("1500.00"),
            paid_amount=Decimal("750.00"),
            status=RemittanceStatus.PARTIAL
        )
        
        assert remittance.due_amount == Decimal("1500.00")
        assert remittance.paid_amount == Decimal("750.00")
        assert remittance.status == RemittanceStatus.PARTIAL
        assert remittance.workspace_team == workspace_team

    def test_remittance_workspace_property(self):
        """Test the workspace property returns the correct workspace."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        assert remittance.workspace == workspace_team.workspace
        assert remittance.workspace.organization == workspace_team.workspace.organization

    def test_remittance_remaining_amount_calculation(self):
        """Test the remaining_amount method calculations."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Test with default values (0.00 due, 0.00 paid)
        assert remittance.remaining_amount() == Decimal("0.00")
        
        # Update to test different scenarios
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("300.00")
        remittance.save()
        
        # Test partial payment
        assert remittance.remaining_amount() == Decimal("700.00")
        
        # Test overpayment
        remittance.paid_amount = Decimal("1200.00")
        remittance.save()
        # When overpaid, remaining_amount returns negative value (excess amount)
        assert remittance.remaining_amount() == Decimal("-200.00")

    def test_remittance_overpaid_check(self):
        """Test the check_if_overpaid method."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Initially not overpaid
        assert remittance.is_overpaid is False
        
        # Set overpaid scenario
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("1200.00")
        remittance.check_if_overpaid()
        
        assert remittance.is_overpaid is True
        
        # Set normal payment scenario
        remittance.paid_amount = Decimal("800.00")
        remittance.check_if_overpaid()
        
        assert remittance.is_overpaid is False

    def test_remittance_status_update_pending(self):
        """Test status update when payment is pending."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Set pending scenario
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("0.00")
        remittance.update_status()
        
        assert remittance.status == RemittanceStatus.PENDING

    def test_remittance_status_update_partial(self):
        """Test status update when payment is partial."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Set partial payment scenario
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("500.00")
        remittance.update_status()
        
        assert remittance.status == RemittanceStatus.PARTIAL

    def test_remittance_status_update_paid(self):
        """Test status update when payment is fully paid."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Set fully paid scenario
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("1000.00")
        remittance.update_status()
        
        assert remittance.status == RemittanceStatus.PAID

    def test_remittance_status_update_overpaid(self):
        """Test status update when payment is overpaid."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Set overpaid scenario
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("1200.00")
        remittance.update_status()
        
        assert remittance.status == RemittanceStatus.OVERPAID

    def test_remittance_status_update_canceled(self):
        """Test that canceled status is not changed by update_status."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Set canceled status
        remittance.status = RemittanceStatus.CANCELED
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("500.00")
        remittance.update_status()
        
        # Status should remain canceled
        assert remittance.status == RemittanceStatus.CANCELED

    def test_remittance_overdue_check(self):
        """Test the check_if_overdue method with expired workspace."""
        # Create a workspace that's already expired
        past_date = timezone.now().date() - timedelta(days=30)
        workspace = WorkspaceFactory(end_date=past_date)
        team = TeamFactory(organization=workspace.organization)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
        
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Initially should be within deadlines
        assert remittance.paid_within_deadlines is True
        
        # Check if overdue
        remittance.check_if_overdue()
        
        # Should now be marked as not within deadlines
        assert remittance.paid_within_deadlines is False

    def test_remittance_overdue_check_active_workspace(self):
        """Test overdue check with active workspace."""
        # Create a workspace that's still active
        future_date = timezone.now().date() + timedelta(days=30)
        workspace = WorkspaceFactory(end_date=future_date)
        team = TeamFactory(organization=workspace.organization)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
        
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Should remain within deadlines
        assert remittance.paid_within_deadlines is True
        
        remittance.check_if_overdue()
        
        # Should still be within deadlines
        assert remittance.paid_within_deadlines is True

    def test_remittance_overdue_check_paid_remittance(self):
        """Test that paid remittances are not marked as overdue."""
        # Create an expired workspace
        past_date = timezone.now().date() - timedelta(days=30)
        workspace = WorkspaceFactory(end_date=past_date)
        team = TeamFactory(organization=workspace.organization)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
        
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Set as paid
        remittance.status = RemittanceStatus.PAID
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("1000.00")
        remittance.save()
        
        # Check if overdue
        remittance.check_if_overdue()
        
        # Should remain within deadlines since it's paid
        assert remittance.paid_within_deadlines is True

    def test_remittance_string_representation(self):
        """Test the string representation of the remittance."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Update status to make string representation more meaningful
        remittance.status = RemittanceStatus.PENDING
        remittance.save()
        
        string_repr = str(remittance)
        assert "Remittance" in string_repr
        assert remittance.workspace.title in string_repr
        assert "Pending" in string_repr

    def test_remittance_meta_options(self):
        """Test the Meta class options."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        # Test verbose names
        assert Remittance._meta.verbose_name == "remittance"
        assert Remittance._meta.verbose_name_plural == "remittances"
        
        # Test ordering
        assert Remittance._meta.ordering == ["-created_at"]
        
        # Test permissions exist
        permissions = [perm[0] for perm in Remittance._meta.permissions]
        assert "review_remittance" in permissions
        assert "flag_remittance" in permissions

    def test_remittance_indexes(self):
        """Test that the model has the expected database indexes."""
        indexes = Remittance._meta.indexes
        index_fields = [index.fields for index in indexes]
        
        assert ["status"] in index_fields
        assert ["paid_within_deadlines"] in index_fields

 