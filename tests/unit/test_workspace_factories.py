"""
Unit tests for Workspace factories.
"""

import pytest
from decimal import Decimal
from datetime import date

from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.workspaces.constants import StatusChoices
from tests.factories import (
    WorkspaceFactory,
    WorkspaceWithAdminFactory,
    ActiveWorkspaceFactory,
    ArchivedWorkspaceFactory,
    ClosedWorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceWithTeamsFactory,
    CustomRateWorkspaceFactory,
)


@pytest.mark.django_db
class TestWorkspaceFactories:
    """Test workspace-related factories."""

    def test_workspace_factory_creates_valid_workspace(self):
        """Test WorkspaceFactory creates a valid workspace."""
        workspace = WorkspaceFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.workspace_id is not None
        assert workspace.organization is not None
        assert workspace.title.startswith("Workspace")
        assert workspace.description is not None
        assert workspace.status == StatusChoices.ACTIVE
        assert workspace.remittance_rate == Decimal("90.00")
        assert isinstance(workspace.start_date, date)
        assert workspace.expense == Decimal("0.00")
        assert workspace.workspace_admin is None
        assert workspace.operation_reviewer is None
        assert workspace.created_by is None

    def test_workspace_with_admin_factory(self):
        """Test WorkspaceWithAdminFactory creates workspace with admin."""
        workspace = WorkspaceWithAdminFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.workspace_admin is not None
        assert workspace.created_by is not None
        assert workspace.workspace_admin == workspace.created_by
        assert workspace.workspace_admin.organization == workspace.organization

    def test_active_workspace_factory(self):
        """Test ActiveWorkspaceFactory creates active workspace."""
        workspace = ActiveWorkspaceFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.status == StatusChoices.ACTIVE
        assert workspace.title.startswith("Active Workspace")

    def test_archived_workspace_factory(self):
        """Test ArchivedWorkspaceFactory creates archived workspace."""
        workspace = ArchivedWorkspaceFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.status == StatusChoices.ARCHIVED
        assert workspace.title.startswith("Archived Workspace")

    def test_closed_workspace_factory(self):
        """Test ClosedWorkspaceFactory creates closed workspace."""
        workspace = ClosedWorkspaceFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.status == StatusChoices.CLOSED
        assert workspace.title.startswith("Closed Workspace")
        assert workspace.end_date is not None
        assert workspace.end_date < date.today()

    def test_custom_rate_workspace_factory(self):
        """Test CustomRateWorkspaceFactory creates workspace with custom rate."""
        workspace = CustomRateWorkspaceFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.remittance_rate == Decimal("85.00")
        assert workspace.title.startswith("Custom Rate Workspace")


@pytest.mark.django_db
class TestWorkspaceTeamFactories:
    """Test workspace team factories."""

    def test_workspace_team_factory_creates_valid_relationship(self):
        """Test WorkspaceTeamFactory creates valid workspace-team relationship."""
        workspace_team = WorkspaceTeamFactory()

        assert isinstance(workspace_team, WorkspaceTeam)
        assert workspace_team.workspace_team_id is not None
        assert workspace_team.workspace is not None
        assert workspace_team.team is not None

    def test_workspace_with_teams_factory(self):
        """Test WorkspaceWithTeamsFactory creates workspace with teams."""
        workspace = WorkspaceWithTeamsFactory()

        assert isinstance(workspace, Workspace)
        assert workspace.workspace_teams.count() == 2  # Default count

        # Test with custom team count
        workspace_many_teams = WorkspaceWithTeamsFactory(teams=5)
        assert workspace_many_teams.workspace_teams.count() == 5

    def test_unique_constraint_respected(self):
        """Test that unique constraint is respected in factories."""
        workspace = WorkspaceFactory()
        team = WorkspaceTeamFactory().team

        # First relationship should work
        workspace_team1 = WorkspaceTeamFactory(workspace=workspace, team=team)
        assert workspace_team1.workspace == workspace
        assert workspace_team1.team == team

        # Second relationship with same workspace and team should fail
        with pytest.raises(Exception):
            WorkspaceTeamFactory(workspace=workspace, team=team)


@pytest.mark.django_db
class TestWorkspaceUniqueConstraints:
    """Test workspace unique constraints."""

    def test_unique_workspace_title_per_organization(self):
        """Test that workspace titles must be unique within organization."""
        org = WorkspaceFactory().organization
        title = "Duplicate Title"

        # First workspace should work
        workspace1 = WorkspaceFactory(organization=org, title=title)
        assert workspace1.title == title

        # Second workspace with same org and title should fail
        with pytest.raises(Exception):
            WorkspaceFactory(organization=org, title=title)
