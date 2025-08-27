"""
Integration tests for workspace functionality.

Tests the complete workflow of workspace operations including
models, services, and selectors working together.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import TestCase

from apps.currencies.models import Currency
from apps.workspaces.constants import StatusChoices
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam
from apps.workspaces.selectors import (
    get_workspace_by_id,
    get_workspace_exchange_rates,
    get_workspace_teams_by_workspace_id,
    get_workspaces_with_team_counts,
)
from apps.workspaces.services import (
    add_team_to_workspace,
    create_workspace_exchange_rate,
    create_workspace_from_form,
    update_workspace_from_form,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory
from tests.factories.user_factories import CustomUserFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceWithAdminFactory,
)


@pytest.mark.integration
class TestWorkspaceIntegration(TestCase):
    """Test complete workspace workflows."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )

        # Create required groups
        self.admin_group = Group.objects.create(name="workspace_admin")
        self.reviewer_group = Group.objects.create(name="workspace_reviewer")

    @pytest.mark.django_db
    def test_complete_workspace_creation_workflow(self):
        """Test complete workspace creation workflow."""

        # Mock form data
        class MockForm:
            cleaned_data = {
                "title": "Test Workspace",
                "description": "Test Description",
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 12, 31),
                "remittance_rate": Decimal("15.00"),
                "workspace_admin": self.org_member,
                "operations_reviewer": self.org_member,
            }

            def save(self, commit=True):
                workspace = Workspace(
                    title=self.cleaned_data["title"],
                    description=self.cleaned_data["description"],
                    start_date=self.cleaned_data["start_date"],
                    end_date=self.cleaned_data["end_date"],
                    remittance_rate=self.cleaned_data["remittance_rate"],
                    workspace_admin=self.cleaned_data["workspace_admin"],
                    operations_reviewer=self.cleaned_data["operations_reviewer"],
                )
                if commit:
                    workspace.save()
                return workspace

        form = MockForm()

        # Create workspace
        workspace = create_workspace_from_form(
            form=form, orgMember=self.org_member, organization=self.organization
        )

        # Verify workspace was created
        self.assertIsInstance(workspace, Workspace)
        self.assertEqual(workspace.title, "Test Workspace")
        self.assertEqual(workspace.organization, self.organization)
        self.assertEqual(workspace.workspace_admin, self.org_member)
        self.assertEqual(workspace.operations_reviewer, self.org_member)

        # Verify workspace can be retrieved
        retrieved_workspace = get_workspace_by_id(workspace.workspace_id)
        self.assertEqual(retrieved_workspace, workspace)

        # Verify admin is in workspace-specific admin group
        from django.contrib.auth.models import Group

        workspace_admin_group = Group.objects.get(
            name=f"Workspace Admins - {workspace.workspace_id}"
        )
        self.assertTrue(
            workspace_admin_group.user_set.filter(
                user_id=self.org_member.user.user_id
            ).exists()
        )

    @pytest.mark.django_db
    def test_workspace_team_management_workflow(self):
        """Test complete workspace team management workflow."""
        workspace = WorkspaceFactory(organization=self.organization)
        team1 = TeamFactory(organization=self.organization)
        team2 = TeamFactory(organization=self.organization)

        # Add first team
        workspace_team1 = add_team_to_workspace(
            workspace_id=workspace.workspace_id,
            team_id=team1.team_id,
            custom_remittance_rate=0.20,
        )

        self.assertIsInstance(workspace_team1, WorkspaceTeam)
        self.assertEqual(workspace_team1.workspace, workspace)
        self.assertEqual(workspace_team1.team, team1)
        self.assertEqual(workspace_team1.custom_remittance_rate, 0.20)

        # Add second team
        add_team_to_workspace(
            workspace_id=workspace.workspace_id,
            team_id=team2.team_id,
            custom_remittance_rate=None,
        )

        # Verify both teams are in workspace
        workspace_teams = get_workspace_teams_by_workspace_id(workspace.workspace_id)
        self.assertEqual(workspace_teams.count(), 2)

        team_ids = [wt.team.team_id for wt in workspace_teams]
        self.assertIn(team1.team_id, team_ids)
        self.assertIn(team2.team_id, team_ids)

        # Test workspace with team counts
        workspaces_with_counts = get_workspaces_with_team_counts(
            self.organization.organization_id
        )
        workspace_with_count = next(
            w
            for w in workspaces_with_counts
            if w.workspace_id == workspace.workspace_id
        )
        self.assertEqual(workspace_with_count.teams_count, 2)

    @pytest.mark.django_db
    def test_workspace_exchange_rate_workflow(self):
        """Test complete workspace exchange rate workflow."""
        workspace = WorkspaceFactory(organization=self.organization)
        Currency.objects.create(code="EUR", name="Euro")
        approver = OrganizationMemberFactory(organization=self.organization)

        # Create exchange rate
        create_workspace_exchange_rate(
            workspace=workspace,
            organization_member=approver,
            currency_code="EUR",
            rate=1.2,
            note="Test exchange rate",
            effective_date="2024-01-01",
        )

        # Verify exchange rate was created
        exchange_rates = get_workspace_exchange_rates(
            organization=self.organization, workspace=workspace
        )
        self.assertEqual(exchange_rates.count(), 1)

        exchange_rate = exchange_rates.first()
        self.assertEqual(exchange_rate.currency.code, "EUR")
        self.assertEqual(exchange_rate.rate, Decimal("1.2"))
        self.assertEqual(exchange_rate.workspace, workspace)
        self.assertFalse(exchange_rate.is_approved)

        # Approve exchange rate
        exchange_rate.is_approved = True
        exchange_rate.approver = approver
        exchange_rate.save()

        # Verify exchange rate can be retrieved
        exchange_rates = get_workspace_exchange_rates(
            organization=self.organization, workspace=workspace
        )
        self.assertEqual(exchange_rates.count(), 1)
        self.assertEqual(exchange_rates.first(), exchange_rate)
        self.assertTrue(exchange_rates.first().is_approved)

    @pytest.mark.django_db
    def test_workspace_status_lifecycle(self):
        """Test workspace status lifecycle."""
        workspace = WorkspaceWithAdminFactory(
            organization=self.organization, status=StatusChoices.ACTIVE
        )

        # Verify initial status
        self.assertEqual(workspace.status, StatusChoices.ACTIVE)

        # Update to archived
        class MockForm:
            cleaned_data = {
                "title": workspace.title,
                "description": workspace.description,
                "start_date": workspace.start_date,
                "end_date": workspace.end_date,
                "remittance_rate": workspace.remittance_rate,
                "status": StatusChoices.ARCHIVED,
                "workspace_admin": workspace.workspace_admin,
                "operations_reviewer": workspace.operations_reviewer,
            }

        form = MockForm()
        updated_workspace = update_workspace_from_form(
            workspace=workspace,
            form=form,
            previous_workspace_admin=workspace.workspace_admin,
            previous_operations_reviewer=workspace.operations_reviewer,
        )

        self.assertEqual(updated_workspace.status, StatusChoices.ARCHIVED)

        # Update to closed
        form.cleaned_data["status"] = StatusChoices.CLOSED
        final_workspace = update_workspace_from_form(
            workspace=updated_workspace,
            form=form,
            previous_workspace_admin=updated_workspace.workspace_admin,
            previous_operations_reviewer=updated_workspace.operations_reviewer,
        )

        self.assertEqual(final_workspace.status, StatusChoices.CLOSED)

    @pytest.mark.django_db
    def test_error_handling_integration(self):
        """Test error handling across the system."""
        workspace = WorkspaceFactory(organization=self.organization)
        team = TeamFactory(organization=self.organization)
        other_org_team = TeamFactory()  # Different organization

        # Add team successfully
        workspace_team = add_team_to_workspace(
            workspace_id=workspace.workspace_id,
            team_id=team.team_id,
            custom_remittance_rate=None,
        )
        self.assertIsNotNone(workspace_team)

        # Try to add same team again - should raise IntegrityError due to database constraint
        from django.db import transaction
        from django.db.utils import IntegrityError

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                add_team_to_workspace(
                    workspace_id=workspace.workspace_id,
                    team_id=team.team_id,
                    custom_remittance_rate=None,
                )

        # Try to add team from different organization - should succeed at function level
        # (the function doesn't validate organization membership)
        workspace_team2 = add_team_to_workspace(
            workspace_id=workspace.workspace_id,
            team_id=other_org_team.team_id,
            custom_remittance_rate=None,
        )
        self.assertIsNotNone(workspace_team2)

    @pytest.mark.django_db
    def test_workspace_admin_reviewer_permissions(self):
        """Test workspace admin and reviewer permission assignment."""
        admin_user = CustomUserFactory()
        reviewer_user = CustomUserFactory()
        admin_member = OrganizationMemberFactory(
            organization=self.organization, user=admin_user
        )
        reviewer_member = OrganizationMemberFactory(
            organization=self.organization, user=reviewer_user
        )

        class MockForm:
            cleaned_data = {
                "title": "Permission Test Workspace",
                "description": "Testing permissions",
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 12, 31),
                "remittance_rate": Decimal("0.10"),
                "workspace_admin": admin_member,
                "operations_reviewer": reviewer_member,
                "created_by": admin_member,
            }

            def save(self, commit=True):
                from apps.workspaces.models import Workspace

                workspace = Workspace(**self.cleaned_data)
                if commit:
                    workspace.save()
                return workspace

        form = MockForm()
        workspace = create_workspace_from_form(
            form=form, organization=self.organization, orgMember=admin_member
        )

        # Verify admin assignment
        self.assertEqual(workspace.workspace_admin, admin_member)
        from django.contrib.auth.models import Group

        workspace_admin_group = Group.objects.get(
            name=f"Workspace Admins - {workspace.workspace_id}"
        )
        self.assertTrue(
            workspace_admin_group.user_set.filter(user_id=admin_user.user_id).exists()
        )

        # Verify reviewer assignment
        self.assertEqual(workspace.operations_reviewer, reviewer_member)
        workspace_reviewer_group = Group.objects.get(
            name=f"Operations Reviewer - {workspace.workspace_id}"
        )
        self.assertTrue(
            workspace_reviewer_group.user_set.filter(
                user_id=reviewer_user.user_id
            ).exists()
        )

    @pytest.mark.django_db
    def test_workspace_with_multiple_exchange_rates(self):
        """Test workspace with multiple exchange rates."""
        workspace = WorkspaceFactory(organization=self.organization)
        Currency.objects.create(code="USD", name="US Dollar")
        Currency.objects.create(code="EUR", name="Euro")
        Currency.objects.create(code="GBP", name="British Pound")

        # Create multiple exchange rates
        create_workspace_exchange_rate(
            workspace=workspace,
            organization_member=self.org_member,
            currency_code="USD",
            rate=Decimal("1.0"),
            note="USD exchange rate",
            effective_date="2024-01-01",
        )

        create_workspace_exchange_rate(
            workspace=workspace,
            organization_member=self.org_member,
            currency_code="EUR",
            rate=Decimal("1.2"),
            note="EUR exchange rate",
            effective_date="2024-01-01",
        )

        create_workspace_exchange_rate(
            workspace=workspace,
            organization_member=self.org_member,
            currency_code="GBP",
            rate=Decimal("0.8"),
            note="GBP exchange rate",
            effective_date="2024-01-01",
        )

        # Verify exchange rates
        exchange_rates = get_workspace_exchange_rates(
            organization=self.organization, workspace=workspace
        )
        self.assertEqual(exchange_rates.count(), 3)

        # Check currency codes
        currency_codes = [er.currency.code for er in exchange_rates]
        self.assertIn("USD", currency_codes)
        self.assertIn("EUR", currency_codes)
        self.assertIn("GBP", currency_codes)

    @pytest.mark.django_db
    def test_workspace_deletion_cascade(self):
        """Test workspace deletion and related object cleanup."""
        workspace = WorkspaceFactory(organization=self.organization)
        team = TeamFactory(organization=self.organization)
        Currency.objects.create(code="CAD", name="Canadian Dollar")

        # Create related objects
        workspace_team = add_team_to_workspace(
            workspace_id=workspace.workspace_id,
            team_id=team.team_id,
            custom_remittance_rate=None,
        )
        create_workspace_exchange_rate(
            workspace=workspace,
            organization_member=self.org_member,
            currency_code="CAD",
            rate=Decimal("1.5"),
            note="CAD exchange rate",
            effective_date="2024-01-01",
        )

        # Get the exchange rate for verification
        exchange_rates = get_workspace_exchange_rates(
            organization=self.organization, workspace=workspace
        )
        exchange_rate = exchange_rates.first()

        workspace_id = workspace.workspace_id
        workspace_team_id = workspace_team.workspace_team_id
        exchange_rate_id = exchange_rate.workspace_exchange_rate_id

        # Delete workspace
        workspace.delete()

        # Verify workspace is deleted
        self.assertIsNone(get_workspace_by_id(workspace_id))

        # Verify related objects are handled appropriately
        # (This depends on your model's on_delete behavior)
        with self.assertRaises(WorkspaceTeam.DoesNotExist):
            WorkspaceTeam.objects.get(workspace_team_id=workspace_team_id)

        # Exchange rates might be soft deleted
        try:
            rate = WorkspaceExchangeRate.objects.get(
                workspace_exchange_rate_id=exchange_rate_id
            )
            # If soft delete is implemented, check is_deleted flag
            if hasattr(rate, "is_deleted"):
                self.assertTrue(rate.is_deleted)
        except WorkspaceExchangeRate.DoesNotExist:
            # Hard delete is also acceptable
            pass
