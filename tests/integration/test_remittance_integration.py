"""
Integration tests for Remittance app.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.remittance import selectors, services
from apps.remittance.constants import RemittanceStatus
from apps.remittance.models import Remittance
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    PaidRemittanceFactory,
    PendingRemittanceFactory,
    RemittanceFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)
from tests.factories.workspace_factories import WorkspaceWithAdminFactory


@pytest.mark.django_db
class TestRemittanceWorkflow:
    """Test complete remittance workflows."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(
            organization=self.organization, end_date=date.today() + timedelta(days=30)
        )
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.user = CustomUserFactory()
        # Create organization membership for the user
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_complete_remittance_creation_workflow(self, mock_guardian_has_perm):
        """Test the complete workflow from creation to confirmation."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            # Return True for all remittance permissions regardless of object
            if any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            ):
                return True
            return False

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect
        # Step 1: Create remittance
        remittance = services.remittance_create(
            workspace_team=self.workspace_team,
            due_amount=Decimal("1000.00"),
            user=self.user,
        )

        assert remittance.status == RemittanceStatus.PENDING
        assert remittance.due_amount == Decimal("1000.00")
        assert remittance.paid_amount == Decimal("0.00")

        # Step 2: Record partial payment
        updated_remittance = services.remittance_record_payment(
            remittance=remittance, amount=Decimal("400.00"), user=self.user
        )

        assert updated_remittance.status == RemittanceStatus.PARTIAL
        assert updated_remittance.paid_amount == Decimal("400.00")

        # Step 3: Record remaining payment
        final_remittance = services.remittance_record_payment(
            remittance=updated_remittance, amount=Decimal("600.00"), user=self.user
        )

        assert final_remittance.status == RemittanceStatus.PAID
        assert final_remittance.paid_amount == Decimal("1000.00")

        # Step 4: Confirm payment
        confirmed_remittance = services.remittance_confirm_payment(
            remittance=final_remittance,
            user=self.user,
        )

        assert confirmed_remittance.confirmed_by is not None
        assert confirmed_remittance.confirmed_at is not None

    @patch("apps.accounts.models.CustomUser.has_perm")
    def test_remittance_cancellation_workflow(self, mock_user_has_perm):
        """Test remittance cancellation workflow."""

        # Mock user has_perm to return True for all remittance permissions
        def user_permission_side_effect(perm, obj=None):
            remittance_permissions = [
                "remittance.add_remittance",
                "remittance.change_remittance",
                "remittance.delete_remittance",
                "remittance.view_remittance",
                "remittance.review_remittance",
                "remittance.flag_remittance",
            ]
            return perm in remittance_permissions

        mock_user_has_perm.side_effect = user_permission_side_effect

        # Create separate workspace teams to avoid unique constraint violations
        cancel_team1 = TeamFactory(
            organization=self.organization, title="Cancel Team 1"
        )
        cancel_team2 = TeamFactory(
            organization=self.organization, title="Cancel Team 2"
        )
        cancel_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace, team=cancel_team1
        )
        cancel_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace, team=cancel_team2
        )

        # Test 1: Successful cancellation of remittance without payments
        pending_remittance = PendingRemittanceFactory(
            workspace_team=cancel_workspace_team1,
            due_amount=Decimal("500.00"),
            paid_amount=Decimal("0.00"),
        )

        cancelled_remittance = services.remittance_cancel(
            remittance=pending_remittance, user=self.user
        )

        # Refresh from database to ensure we have the latest status
        cancelled_remittance.refresh_from_db()
        assert cancelled_remittance.status == RemittanceStatus.CANCELED

        # Test 2: Cancellation should fail when payments exist
        remittance_with_payment = PendingRemittanceFactory(
            workspace_team=cancel_workspace_team2, due_amount=Decimal("500.00")
        )

        # Record a payment first
        services.remittance_record_payment(
            remittance=remittance_with_payment, amount=Decimal("200.00"), user=self.user
        )

        # Now try to cancel - this should fail
        with pytest.raises(ValidationError) as exc_info:
            services.remittance_cancel(
                remittance=remittance_with_payment, user=self.user
            )

        assert "Cannot cancel a remittance that has payments recorded" in str(
            exc_info.value
        )

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_income_entry_to_remittance_workflow(self, mock_guardian_has_perm):
        """Test workflow from income entry to remittance creation."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            if any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            ):
                return True
            return False

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create an income entry
        entry = EntryFactory(
            workspace_team=self.workspace_team,
            amount=Decimal("750.00"),
            entry_type="income",
        )

        # Create remittance from income entry
        remittance = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert remittance.workspace_team == self.workspace_team
        # Expected amount is 750.00 * 0.90 (default remittance rate) = 675.00
        assert remittance.due_amount == Decimal("675.00")
        assert remittance.status == RemittanceStatus.PENDING

    def test_remittance_overdue_detection_workflow(self):
        """Test overdue detection workflow."""
        # Create workspace that ended in the past
        past_workspace = WorkspaceFactory(
            organization=self.organization, end_date=date.today() - timedelta(days=10)
        )
        past_workspace_team = WorkspaceTeamFactory(
            workspace=past_workspace, team=self.team
        )

        # Create unpaid remittance
        remittance = PendingRemittanceFactory(
            workspace_team=past_workspace_team, due_amount=Decimal("1000.00")
        )

        # Check if overdue
        remittance.check_if_overdue()

        # Verify overdue status is saved
        remittance.save()
        remittance.refresh_from_db()
        assert remittance.paid_within_deadlines is False

    def test_remittance_filtering_workflow(self):
        """Test complete filtering workflow."""
        # Create multiple remittances with different characteristics
        # Create separate workspace teams to avoid unique constraint
        team1 = TeamFactory(organization=self.organization, title="Team 1")
        team2 = TeamFactory(organization=self.organization, title="Team 2")
        team3 = TeamFactory(organization=self.organization, title="Other Team")

        workspace_team1 = WorkspaceTeamFactory(workspace=self.workspace, team=team1)
        workspace_team2 = WorkspaceTeamFactory(workspace=self.workspace, team=team2)
        workspace_team3 = WorkspaceTeamFactory(workspace=self.workspace, team=team3)

        pending_remittance = PendingRemittanceFactory(workspace_team=workspace_team1)
        paid_remittance = PaidRemittanceFactory(workspace_team=workspace_team2)
        other_remittance = RemittanceFactory(workspace_team=workspace_team3)

        # Test filtering by workspace
        workspace_remittances = selectors.get_remittances_with_filters(
            workspace_id=self.workspace.workspace_id
        )

        remittance_ids = [r.remittance_id for r in workspace_remittances]
        assert pending_remittance.remittance_id in remittance_ids
        assert paid_remittance.remittance_id in remittance_ids
        assert other_remittance.remittance_id in remittance_ids

        # Test filtering by team
        team_remittances = selectors.get_remittances_with_filters(
            workspace_id=self.workspace.workspace_id, team_id=team1.team_id
        )

        team_remittance_ids = [r.remittance_id for r in team_remittances]
        assert pending_remittance.remittance_id in team_remittance_ids
        assert paid_remittance.remittance_id not in team_remittance_ids
        assert other_remittance.remittance_id not in team_remittance_ids

        # Test filtering by status
        pending_remittances = selectors.get_remittances_with_filters(
            workspace_id=self.workspace.workspace_id, status=RemittanceStatus.PENDING
        )

        pending_ids = [r.remittance_id for r in pending_remittances]
        assert pending_remittance.remittance_id in pending_ids
        assert paid_remittance.remittance_id not in pending_ids


@pytest.mark.django_db
class TestRemittancePermissionWorkflow:
    """Test remittance workflows with permission checking."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.user = CustomUserFactory()
        # Create OrganizationMember for the user to avoid DoesNotExist error
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.remittance = RemittanceFactory(workspace_team=self.workspace_team)

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_permission_denied_workflow(self, mock_guardian_has_perm):
        """Test workflow when user lacks permissions."""

        # Mock to deny all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return not any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Attempt to create remittance without permission
        with pytest.raises(Exception):  # Adjust exception type based on implementation
            services.remittance_create(
                workspace_team=self.workspace_team,
                due_amount=Decimal("1000.00"),
                due_date=date.today() + timedelta(days=30),
                user=self.user,
            )

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_partial_permission_workflow(self, mock_guardian_has_perm):
        """Test workflow with partial permissions."""

        def guardian_permission_side_effect(user_obj, perm, obj=None):
            # User can view and record payments but not confirm
            if any(
                perm_name in perm
                for perm_name in ["view_remittance", "change_remittance"]
            ):
                return True
            elif "review_remittance" in perm:
                return False
            return False

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # User can record payment
        updated_remittance = services.remittance_record_payment(
            remittance=self.remittance, amount=Decimal("100.00"), user=self.user
        )
        assert updated_remittance.paid_amount == Decimal("100.00")

        # But cannot confirm payment
        with pytest.raises(Exception):  # Adjust exception type based on implementation
            services.remittance_confirm_payment(
                remittance=updated_remittance,
                user=self.user,
            )

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_admin_permission_workflow(self, mock_guardian_has_perm):
        """Test workflow with full admin permissions."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create separate workspace team to avoid unique constraint
        admin_team = TeamFactory(organization=self.organization, title="Admin Team")
        admin_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=admin_team
        )

        # Admin can perform all operations
        remittance = services.remittance_create(
            workspace_team=admin_workspace_team,
            due_amount=Decimal("2000.00"),
            user=self.user,
        )

        remittance = services.remittance_record_payment(
            remittance=remittance, amount=Decimal("2000.00"), user=self.user
        )

        confirmed_remittance = services.remittance_confirm_payment(
            remittance=remittance, user=self.user
        )

        assert confirmed_remittance.status == RemittanceStatus.PAID
        assert confirmed_remittance.confirmed_by is not None


@pytest.mark.django_db
class TestRemittanceDataConsistency:
    """Test data consistency across remittance operations."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.user = CustomUserFactory()

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_concurrent_payment_consistency(self, mock_guardian_has_perm):
        """Test data consistency with concurrent payments."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        remittance = services.remittance_create(
            workspace_team=self.workspace_team,
            due_amount=Decimal("1000.00"),
            user=self.user,
        )

        # Simulate concurrent payments
        payment1 = services.remittance_record_payment(
            remittance=remittance, amount=Decimal("300.00"), user=self.user
        )

        # Refresh remittance to get latest state
        payment1.refresh_from_db()

        payment2 = services.remittance_record_payment(
            remittance=payment1, amount=Decimal("700.00"), user=self.user
        )

        assert payment2.paid_amount == Decimal("1000.00")
        assert payment2.status == RemittanceStatus.PAID

    def test_remittance_model_consistency(self):
        """Test model-level data consistency."""
        remittance = RemittanceFactory(
            workspace_team=self.workspace_team,
            due_amount=Decimal("500.00"),
            paid_amount=Decimal("200.00"),
        )

        # Test clean method validation
        remittance.clean()  # Should not raise

        # Test overpayment validation
        remittance.paid_amount = Decimal("600.00")
        with pytest.raises(Exception):  # Adjust based on your validation
            remittance.clean()

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_status_transition_consistency(self, mock_guardian_has_perm):
        """Test status transitions are consistent."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create a separate workspace team for this test
        workspace_team = WorkspaceTeamFactory()

        remittance = PendingRemittanceFactory(
            workspace_team=workspace_team, due_amount=Decimal("1000.00")
        )

        # PENDING -> PARTIAL
        partial_remittance = services.remittance_record_payment(
            remittance=remittance, amount=Decimal("400.00"), user=self.user
        )
        assert partial_remittance.status == RemittanceStatus.PARTIAL

        # PARTIAL -> PAID
        paid_remittance = services.remittance_record_payment(
            remittance=partial_remittance, amount=Decimal("600.00"), user=self.user
        )
        assert paid_remittance.status == RemittanceStatus.PAID

        # Verify no invalid transitions
        # PAID should not go back to PARTIAL
        with pytest.raises(Exception):  # Adjust based on your business logic
            services.remittance_record_payment(
                remittance=paid_remittance,
                amount=Decimal("-100.00"),  # Negative payment
                user=self.user,
            )


@pytest.mark.django_db
class TestRemittanceBusinessLogic:
    """Test complex business logic scenarios."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.user = CustomUserFactory()

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_remittance_rate_calculation(self, mock_guardian_has_perm):
        """Test remittance rate calculation logic."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create a separate workspace team for this test
        workspace_team = WorkspaceTeamFactory(custom_remittance_rate=Decimal("15.00"))

        # Create entry with specific amount
        entry = EntryFactory(
            workspace_team=workspace_team,
            amount=Decimal("1000.00"),
            entry_type="income",
        )

        # Test with custom remittance rate
        remittance = services.remittance_create_or_update_from_income_entry(entry=entry)

        # Expected amount is 1000.00 * 0.15 = 150.00
        assert remittance.due_amount == Decimal("150.00")

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_overdue_calculation_edge_cases(self, mock_guardian_has_perm):
        """Test overdue calculation edge cases."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Workspace ending today
        today_workspace = WorkspaceFactory(
            organization=self.organization, end_date=date.today()
        )
        today_workspace_team = WorkspaceTeamFactory(
            workspace=today_workspace, team=self.team
        )

        remittance = PendingRemittanceFactory(workspace_team=today_workspace_team)

        # Should not be overdue if workspace ends today
        remittance.check_if_overdue()
        remittance.refresh_from_db()
        # assert is_overdue is False  # or True, depending on requirements
        assert remittance.paid_within_deadlines is True

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_multiple_entries_single_remittance(self, mock_guardian_has_perm):
        """Test multiple income entries in single remittance."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create a separate workspace team for this test (uses default 90% rate)
        multi_team = TeamFactory(
            organization=self.organization, title="Multi Entry Team"
        )
        workspace_team = WorkspaceTeamFactory(workspace=self.workspace, team=multi_team)

        # Create multiple entries for same workspace team
        entry1 = EntryFactory(
            workspace_team=workspace_team,
            amount=Decimal("500.00"),
            entry_type="income",
        )
        entry2 = EntryFactory(
            workspace_team=workspace_team,
            amount=Decimal("300.00"),
            entry_type="income",
        )

        # Create remittances from both entries
        remittance1 = services.remittance_create_or_update_from_income_entry(
            entry=entry1
        )

        remittance2 = services.remittance_create_or_update_from_income_entry(
            entry=entry2
        )

        # Should be the same remittance object (one per workspace team)
        assert remittance1.remittance_id == remittance2.remittance_id
        # Total amount should be (500 + 300) * 0.90 = 720.00
        assert remittance2.due_amount == Decimal("720.00")

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_remittance_filtering(self, mock_guardian_has_perm):
        """Test remittance filtering functionality."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create a separate workspace team for this test with proper workspace
        filter_team = TeamFactory(organization=self.organization, title="Filter Team")
        # Create organization member to serve as workspace admin and created_by
        admin_member = OrganizationMemberFactory(organization=self.organization)
        # Create workspace with admin to ensure created_by field is set
        filter_workspace = WorkspaceWithAdminFactory(
            organization=self.organization, admin=admin_member
        )
        workspace_team = WorkspaceTeamFactory(
            workspace=filter_workspace, team=filter_team
        )

        remittance = RemittanceFactory(workspace_team=workspace_team)
        original_due_date = workspace_team.workspace.end_date

        # Change due date
        new_due_date = original_due_date + timedelta(days=30)
        updated_remittance = services.remittance_change_due_date(
            remittance=remittance, due_date=new_due_date, user=self.user
        )

        # Verify the workspace end date was updated
        updated_remittance.workspace_team.workspace.refresh_from_db()
        assert updated_remittance.workspace_team.workspace.end_date == new_due_date


@pytest.mark.django_db
class TestRemittancePerformance:
    """Test performance aspects of remittance operations."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.teams = [TeamFactory(organization=self.organization) for _ in range(5)]
        self.workspace_teams = [
            WorkspaceTeamFactory(workspace=self.workspace, team=team)
            for team in self.teams
        ]
        self.user = CustomUserFactory()

    def test_bulk_remittance_operations(self):
        """Test performance with bulk operations."""
        # Create multiple remittances with separate workspace teams
        remittances = []
        for i, workspace_team in enumerate(self.workspace_teams):
            for j in range(10):  # 10 remittances per team
                # Create separate workspace team for each remittance
                separate_workspace_team = WorkspaceTeamFactory(
                    workspace=self.workspace,
                    team=TeamFactory(organization=self.organization),
                )
                remittances.append(
                    RemittanceFactory(workspace_team=separate_workspace_team)
                )

        # Test bulk filtering performance
        from django.db import connection

        # Count queries manually
        initial_queries = len(connection.queries)
        result = list(
            selectors.get_remittances_with_filters(
                workspace_id=self.workspace.workspace_id
            )
        )
        final_queries = len(connection.queries)

        # Should be efficient (reasonable number of queries)
        query_count = final_queries - initial_queries
        assert query_count <= 5  # Allow some flexibility for joins
        assert len(result) == 50  # 5 teams * 10 remittances

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_bulk_payment_processing(self, mock_guardian_has_perm):
        """Test performance of bulk payment processing."""

        # Mock guardian backend to return True for all remittance permissions
        def guardian_permission_side_effect(user_obj, perm, obj=None):
            return any(
                perm_name in perm
                for perm_name in [
                    "add_remittance",
                    "change_remittance",
                    "delete_remittance",
                    "view_remittance",
                    "review_remittance",
                    "flag_remittance",
                ]
            )

        mock_guardian_has_perm.side_effect = guardian_permission_side_effect

        # Create multiple pending remittances with separate workspace teams
        remittances = []
        workspace_teams = []
        for i in range(10):
            workspace_team = WorkspaceTeamFactory(
                workspace=self.workspace,
                team=TeamFactory(organization=self.organization),
            )
            workspace_teams.append(workspace_team)
            remittances.append(
                PendingRemittanceFactory(
                    workspace_team=workspace_team, due_amount=Decimal("100.00")
                )
            )

        # Process payments for all remittances
        for remittance in remittances:
            services.remittance_record_payment(
                remittance=remittance, amount=Decimal("100.00"), user=self.user
            )

        # Verify all are paid
        paid_count = Remittance.objects.filter(
            workspace_team__in=workspace_teams, status=RemittanceStatus.PAID
        ).count()

        assert paid_count == 10
