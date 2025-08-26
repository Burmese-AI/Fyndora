"""
Integration tests for Workspace workflows.

Tests how workspaces work with organizations, teams, admins, and business processes.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.db import IntegrityError, transaction

from apps.teams.constants import TeamMemberRole
from apps.workspaces.models import Workspace
from apps.workspaces.constants import StatusChoices
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    WorkspaceFactory,
    ActiveWorkspaceFactory,
    ArchivedWorkspaceFactory,
    ClosedWorkspaceFactory,
    WorkspaceTeamFactory,
    TeamFactory,
    TeamMemberFactory,
)


@pytest.mark.integration
@pytest.mark.django_db
class TestWorkspaceCreationWorkflows:
    """Test workspace creation and basic management workflows."""

    def test_create_workspace_with_admin_workflow(self):
        """Test complete workspace creation with admin assignment."""
        # Create organization and admin
        org = OrganizationFactory()
        admin_member = OrganizationMemberFactory(organization=org)

        # Create campaign workspace with finance admin
        workspace = WorkspaceFactory(
            organization=org,
            title="Q1 2024 Campaign",
            description="First quarter fundraising campaign workspace",
            workspace_admin=admin_member,
            created_by=admin_member,
            remittance_rate=Decimal("92.50"),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )

        # Verify workspace creation
        assert workspace.title == "Q1 2024 Campaign"
        assert workspace.organization == org
        assert workspace.workspace_admin == admin_member
        assert workspace.created_by == admin_member
        assert workspace.workspace_admin.organization == org
        assert workspace.remittance_rate == Decimal("92.50")
        assert workspace.status == StatusChoices.ACTIVE

    def test_workspace_status_lifecycle_workflow(self):
        """Test workspace status changes through lifecycle."""
        workspace = ActiveWorkspaceFactory(title="Summer Campaign 2024")

        # Start as active
        assert workspace.status == StatusChoices.ACTIVE

        # Archive workspace
        workspace.status = StatusChoices.ARCHIVED
        workspace.save()
        workspace.refresh_from_db()
        assert workspace.status == StatusChoices.ARCHIVED

        # Close workspace
        workspace.status = StatusChoices.CLOSED
        workspace.end_date = date.today()
        workspace.save()
        workspace.refresh_from_db()
        assert workspace.status == StatusChoices.CLOSED
        assert workspace.end_date == date.today()

    def test_workspace_unique_title_per_organization(self):
        """Test that workspace titles must be unique within organization."""
        org = OrganizationFactory()
        WorkspaceFactory(organization=org, title="Unique Workspace")

        # Attempting to create another workspace with same title in same org should fail

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkspaceFactory(organization=org, title="Unique Workspace")

        # But different organization should work
        different_org = OrganizationFactory()
        workspace2 = WorkspaceFactory(
            organization=different_org, title="Unique Workspace"
        )
        assert workspace2.title == "Unique Workspace"
        assert workspace2.organization != org


@pytest.mark.integration
@pytest.mark.django_db
class TestWorkspaceTeamManagementWorkflows:
    """Test workspace-team relationship management workflows."""

    def test_add_multiple_teams_to_workspace_workflow(self):
        """Test adding multiple teams to a workspace."""
        # Create organization, campaign workspace and fundraising teams
        org = OrganizationFactory()
        workspace = WorkspaceFactory(title="Holiday Campaign 2024", organization=org)
        team1 = TeamFactory(organization=org, title="Door-to-Door Fundraising")
        team2 = TeamFactory(organization=org, title="Digital Outreach Team")
        team3 = TeamFactory(organization=org, title="Corporate Partnership Team")

        # Add teams to workspace
        WorkspaceTeamFactory(workspace=workspace, team=team1)
        WorkspaceTeamFactory(workspace=workspace, team=team2)
        WorkspaceTeamFactory(workspace=workspace, team=team3)

        # Verify relationships
        workspace_teams = workspace.joined_teams.all()
        assert workspace_teams.count() == 3

        team_titles = [wt.team.title for wt in workspace_teams]
        assert "Door-to-Door Fundraising" in team_titles
        assert "Digital Outreach Team" in team_titles
        assert "Corporate Partnership Team" in team_titles

        # Verify reverse relationships
        assert team1.joined_teams.filter(workspace=workspace).exists()
        assert team2.joined_teams.filter(workspace=workspace).exists()
        assert team3.joined_teams.filter(workspace=workspace).exists()

    def test_team_multiple_workspaces_workflow(self):
        """Test that a team can be assigned to multiple workspaces."""
        org = OrganizationFactory()
        team = TeamFactory(organization=org, title="Shared Team")
        workspace1 = WorkspaceFactory(title="Workspace Alpha", organization=org)
        workspace2 = WorkspaceFactory(title="Workspace Beta", organization=org)

        # Add same team to different workspaces
        wt1 = WorkspaceTeamFactory(workspace=workspace1, team=team)
        wt2 = WorkspaceTeamFactory(workspace=workspace2, team=team)

        # Verify relationships
        assert wt1.workspace == workspace1
        assert wt2.workspace == workspace2
        assert wt1.team == team
        assert wt2.team == team

        # Team should be in both workspaces
        team_workspaces = team.joined_teams.all()
        assert team_workspaces.count() == 2
        workspace_ids = [wt.workspace.workspace_id for wt in team_workspaces]
        assert workspace1.workspace_id in workspace_ids
        assert workspace2.workspace_id in workspace_ids

    def test_workspace_team_unique_constraint_workflow(self):
        """Test that team can only be added once per workspace."""
        org = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org)
        team = TeamFactory(organization=org)

        # Add team first time - should succeed
        WorkspaceTeamFactory(workspace=workspace, team=team)

        # Try to add same team again - should fail
        with pytest.raises(IntegrityError):
            WorkspaceTeamFactory(workspace=workspace, team=team)

    def test_remove_team_from_workspace_workflow(self):
        """Test removing team from workspace."""
        org = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org)
        team = TeamFactory(organization=org)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)

        # Verify team is in workspace
        assert workspace.joined_teams.filter(team=team).exists()

        # Remove team from workspace
        workspace_team.delete()

        # Verify team is no longer in workspace
        assert not workspace.joined_teams.filter(team=team).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestWorkspaceAdminManagementWorkflows:
    """Test workspace admin assignment and management workflows."""

    def test_assign_workspace_admin_workflow(self):
        """Test assigning workspace admin."""
        org = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org)
        admin_member = OrganizationMemberFactory(organization=org)

        # Initially no admin
        assert workspace.workspace_admin is None

        # Assign admin
        workspace.workspace_admin = admin_member
        workspace.save()
        workspace.refresh_from_db()

        # Verify admin assignment
        assert workspace.workspace_admin == admin_member
        assert workspace.workspace_admin.organization == org

    def test_transfer_workspace_admin_workflow(self):
        """Test transferring workspace admin to another member."""
        org = OrganizationFactory()
        old_admin = OrganizationMemberFactory(organization=org)
        new_admin = OrganizationMemberFactory(organization=org)

        workspace = WorkspaceFactory(organization=org, workspace_admin=old_admin)

        # Verify initial admin
        assert workspace.workspace_admin == old_admin

        # Transfer to new admin
        workspace.workspace_admin = new_admin
        workspace.save()
        workspace.refresh_from_db()

        # Verify transfer
        assert workspace.workspace_admin == new_admin
        assert workspace.workspace_admin.organization == org

    def test_workspace_admin_multiple_workspaces_workflow(self):
        """Test that organization member can admin multiple workspaces."""
        org = OrganizationFactory()
        admin = OrganizationMemberFactory(organization=org)

        # Create multiple workspaces with same admin
        workspace1 = WorkspaceFactory(
            organization=org, workspace_admin=admin, title="WS1"
        )
        workspace2 = WorkspaceFactory(
            organization=org, workspace_admin=admin, title="WS2"
        )

        # Verify admin relationships
        assert workspace1.workspace_admin == admin
        assert workspace2.workspace_admin == admin

        # Query workspaces administered by this member
        administered_workspaces = Workspace.objects.filter(workspace_admin=admin)
        assert administered_workspaces.count() == 2
        assert workspace1 in administered_workspaces
        assert workspace2 in administered_workspaces


@pytest.mark.integration
@pytest.mark.django_db
class TestWorkspaceBusinessLogicWorkflows:
    """Test workspace business logic and calculations."""

    def test_workspace_remittance_rate_inheritance_workflow(self):
        """Test remittance rate inheritance from workspace to teams."""
        # Create organization, workspace with custom rate
        org = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org, remittance_rate=Decimal("88.00"))
        team = TeamFactory(organization=org)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)

        # Verify workspace rate
        assert workspace.remittance_rate == Decimal("88.00")
        assert workspace_team.custom_remittance_rate is None

        # WorkspaceTeam with custom rate should override
        custom_team = TeamFactory(organization=org)
        custom_workspace_team = WorkspaceTeamFactory(
            workspace=workspace,
            team=custom_team,
            custom_remittance_rate=Decimal("95.00"),
        )

        assert custom_workspace_team.custom_remittance_rate == Decimal("95.00")

        # Custom rate overrides workspace default

    def test_workspace_expense_calculation_workflow(self):
        """Test workspace expense tracking."""
        workspace = WorkspaceFactory(expense=Decimal("1000.00"))

        # Simulate adding expenses
        workspace.expense += Decimal("500.00")  # Add team expense
        workspace.expense += Decimal("200.00")  # Add direct expense
        workspace.save()

        workspace.refresh_from_db()
        assert workspace.expense == Decimal("1700.00")

    def test_workspace_date_validation_workflow(self):
        """Test workspace date range validation."""
        start_date = date.today()
        end_date = start_date + timedelta(days=180)

        workspace = WorkspaceFactory(start_date=start_date, end_date=end_date)

        assert workspace.start_date == start_date
        assert workspace.end_date == end_date
        assert workspace.end_date > workspace.start_date


@pytest.mark.integration
@pytest.mark.django_db
class TestWorkspaceQueryWorkflows:
    """Test workspace querying and filtering workflows."""

    def test_get_workspaces_by_organization_workflow(self):
        """Test getting all workspaces for an organization."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()

        # Create workspaces for different orgs
        ws1 = WorkspaceFactory(organization=org1, title="Org1 WS1")
        ws2 = WorkspaceFactory(organization=org1, title="Org1 WS2")
        ws3 = WorkspaceFactory(organization=org2, title="Org2 WS1")

        # Query by organization
        org1_workspaces = Workspace.objects.filter(organization=org1)
        org2_workspaces = Workspace.objects.filter(organization=org2)

        assert org1_workspaces.count() == 2
        assert org2_workspaces.count() == 1
        assert ws1 in org1_workspaces
        assert ws2 in org1_workspaces
        assert ws3 in org2_workspaces

    def test_get_workspaces_by_status_workflow(self):
        """Test getting workspaces filtered by status."""
        # Create workspaces with different statuses
        active_ws = ActiveWorkspaceFactory()
        archived_ws = ArchivedWorkspaceFactory()
        closed_ws = ClosedWorkspaceFactory()

        # Query by status
        active_workspaces = Workspace.objects.filter(status=StatusChoices.ACTIVE)
        archived_workspaces = Workspace.objects.filter(status=StatusChoices.ARCHIVED)
        closed_workspaces = Workspace.objects.filter(status=StatusChoices.CLOSED)

        assert active_ws in active_workspaces
        assert archived_ws in archived_workspaces
        assert closed_ws in closed_workspaces

    def test_get_workspace_teams_with_members_workflow(self):
        """Test getting workspace teams with their members."""
        org = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org)
        team = TeamFactory(organization=org)
        WorkspaceTeamFactory(workspace=workspace, team=team)

        # Add members to team
        TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        TeamMemberFactory(
            team=team, role=TeamMemberRole.AUDITOR
        )  # Formerly TeamCoordinatorFactory

        # Get workspace teams with members
        workspace_teams = workspace.joined_teams.all().select_related("team")

        for wt in workspace_teams:
            # Access team members through team
            team_members = wt.team.members.all()
            assert team_members.count() == 2

            # Should have different roles
            roles = [tm.role for tm in team_members]
            assert TeamMemberRole.SUBMITTER in roles
            assert TeamMemberRole.AUDITOR in roles

    def test_get_admin_workspaces_workflow(self):
        """Test getting all workspaces administered by a member."""
        org = OrganizationFactory()
        admin = OrganizationMemberFactory(organization=org)

        # Create workspaces with this admin
        ws1 = WorkspaceFactory(organization=org, workspace_admin=admin)
        ws2 = WorkspaceFactory(organization=org, workspace_admin=admin)
        ws3 = WorkspaceFactory(organization=org)  # Different admin

        # Query workspaces by admin
        admin_workspaces = admin.administered_workspaces.all()

        assert admin_workspaces.count() == 2
        assert ws1 in admin_workspaces
        assert ws2 in admin_workspaces
        assert ws3 not in admin_workspaces


print("TEST OVERRIDE WORKING")
