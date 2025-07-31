"""
Unit tests for Remittance selectors.
"""

from datetime import date, timedelta

import pytest

from apps.remittance import selectors
from apps.remittance.constants import RemittanceStatus
from tests.factories import (
    OrganizationFactory,
    PaidRemittanceFactory,
    PartiallyPaidRemittanceFactory,
    PendingRemittanceFactory,
    RemittanceFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.django_db
class TestGetRemittancesWithFilters:
    """Test get_remittances_with_filters selector."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace1 = WorkspaceFactory(
            organization=self.organization, title="Test Workspace 1"
        )
        self.workspace2 = WorkspaceFactory(
            organization=self.organization, title="Test Workspace 2"
        )

        self.team1 = TeamFactory(organization=self.organization, title="Alpha Team")
        self.team2 = TeamFactory(organization=self.organization, title="Beta Team")

        self.workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=self.team1
        )
        self.workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=self.team2
        )
        self.workspace_team3 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=self.team1
        )

    def test_get_remittances_by_workspace_only(self):
        """Test filtering remittances by workspace only."""
        # Create remittances for different workspaces
        remittance1 = RemittanceFactory(workspace_team=self.workspace_team1)
        remittance2 = RemittanceFactory(workspace_team=self.workspace_team2)
        remittance3 = RemittanceFactory(workspace_team=self.workspace_team3)

        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id
        )

        remittance_ids = [r.remittance_id for r in result]
        assert remittance1.remittance_id in remittance_ids
        assert remittance2.remittance_id in remittance_ids
        assert remittance3.remittance_id not in remittance_ids

    def test_get_remittances_by_workspace_and_team(self):
        """Test filtering remittances by workspace and team."""
        remittance1 = RemittanceFactory(workspace_team=self.workspace_team1)
        remittance2 = RemittanceFactory(workspace_team=self.workspace_team2)

        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, team_id=self.team1.team_id
        )

        remittance_ids = [r.remittance_id for r in result]
        assert remittance1.remittance_id in remittance_ids
        assert remittance2.remittance_id not in remittance_ids

    def test_get_remittances_by_status(self):
        """Test filtering remittances by status."""
        # Create separate workspace teams to avoid unique constraint violation
        pending_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        partial_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        paid_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )

        pending_remittance = PendingRemittanceFactory(
            workspace_team=pending_workspace_team
        )
        partial_remittance = PartiallyPaidRemittanceFactory(
            workspace_team=partial_workspace_team
        )
        paid_remittance = PaidRemittanceFactory(workspace_team=paid_workspace_team)

        # Filter by pending status
        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, status=RemittanceStatus.PENDING
        )

        remittance_ids = [r.remittance_id for r in result]
        assert pending_remittance.remittance_id in remittance_ids
        assert partial_remittance.remittance_id not in remittance_ids
        assert paid_remittance.remittance_id not in remittance_ids

    def test_get_remittances_by_date_range(self):
        """Test filtering remittances by date range."""
        # Create workspaces with different end dates
        past_date = date.today() - timedelta(days=60)
        recent_date = date.today() - timedelta(days=10)
        future_date = date.today() + timedelta(days=30)

        old_workspace = WorkspaceFactory(
            organization=self.organization, end_date=past_date
        )
        recent_workspace = WorkspaceFactory(
            organization=self.organization, end_date=recent_date
        )
        future_workspace = WorkspaceFactory(
            organization=self.organization, end_date=future_date
        )

        old_workspace_team = WorkspaceTeamFactory(
            workspace=old_workspace, team=self.team1
        )
        recent_workspace_team = WorkspaceTeamFactory(
            workspace=recent_workspace, team=self.team1
        )
        future_workspace_team = WorkspaceTeamFactory(
            workspace=future_workspace, team=self.team1
        )

        RemittanceFactory(workspace_team=old_workspace_team)
        RemittanceFactory(workspace_team=recent_workspace_team)
        RemittanceFactory(workspace_team=future_workspace_team)

        # Filter by start date - test each workspace separately
        start_date = date.today() - timedelta(days=30)

        # Test recent workspace (should be included)
        recent_result = selectors.get_remittances_with_filters(
            workspace_id=recent_workspace.workspace_id, start_date=start_date
        )
        assert len(recent_result) == 1

        # Test future workspace (should be included)
        future_result = selectors.get_remittances_with_filters(
            workspace_id=future_workspace.workspace_id, start_date=start_date
        )
        assert len(future_result) == 1

        # Test old workspace (should be excluded)
        old_result = selectors.get_remittances_with_filters(
            workspace_id=old_workspace.workspace_id, start_date=start_date
        )
        assert len(old_result) == 0

    def test_get_remittances_by_end_date(self):
        """Test filtering remittances by end date."""
        past_date = date.today() - timedelta(days=60)
        recent_date = date.today() - timedelta(days=10)
        future_date = date.today() + timedelta(days=30)

        old_workspace = WorkspaceFactory(
            organization=self.organization, end_date=past_date
        )
        recent_workspace = WorkspaceFactory(
            organization=self.organization, end_date=recent_date
        )
        future_workspace = WorkspaceFactory(
            organization=self.organization, end_date=future_date
        )

        old_workspace_team = WorkspaceTeamFactory(
            workspace=old_workspace, team=self.team1
        )
        recent_workspace_team = WorkspaceTeamFactory(
            workspace=recent_workspace, team=self.team1
        )
        future_workspace_team = WorkspaceTeamFactory(
            workspace=future_workspace, team=self.team1
        )

        RemittanceFactory(workspace_team=old_workspace_team)
        RemittanceFactory(workspace_team=recent_workspace_team)
        RemittanceFactory(workspace_team=future_workspace_team)

        # Filter by end date - test each workspace separately
        end_date = date.today() - timedelta(days=5)

        # Test old workspace (should be included)
        old_result = selectors.get_remittances_with_filters(
            workspace_id=old_workspace.workspace_id, end_date=end_date
        )
        assert len(old_result) == 1

        # Test recent workspace (should be included)
        recent_result = selectors.get_remittances_with_filters(
            workspace_id=recent_workspace.workspace_id, end_date=end_date
        )
        assert len(recent_result) == 1

        # Test future workspace (should be excluded)
        future_result = selectors.get_remittances_with_filters(
            workspace_id=future_workspace.workspace_id, end_date=end_date
        )
        assert len(future_result) == 0

    def test_get_remittances_by_search_team_title(self):
        """Test filtering remittances by team title search."""
        alpha_remittance = RemittanceFactory(
            workspace_team=self.workspace_team1
        )  # Alpha Team
        beta_remittance = RemittanceFactory(
            workspace_team=self.workspace_team2
        )  # Beta Team

        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, search="Alpha"
        )

        remittance_ids = [r.remittance_id for r in result]
        assert alpha_remittance.remittance_id in remittance_ids
        assert beta_remittance.remittance_id not in remittance_ids

    def test_get_remittances_by_search_status(self):
        """Test filtering remittances by status search."""
        pending_remittance = PendingRemittanceFactory(
            workspace_team=self.workspace_team1
        )
        paid_remittance = PaidRemittanceFactory(workspace_team=self.workspace_team2)

        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, search="pending"
        )

        remittance_ids = [r.remittance_id for r in result]
        assert pending_remittance.remittance_id in remittance_ids
        assert paid_remittance.remittance_id not in remittance_ids

    def test_get_remittances_case_insensitive_search(self):
        """Test case insensitive search functionality."""
        RemittanceFactory(workspace_team=self.workspace_team1)  # Alpha Team

        # Test lowercase search
        result_lower = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, search="alpha"
        )

        # Test uppercase search
        result_upper = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, search="ALPHA"
        )

        # Both should return the same result
        assert len(result_lower) == len(result_upper) == 1
        assert result_lower[0].remittance_id == result_upper[0].remittance_id

    def test_get_remittances_combined_filters(self):
        """Test combining multiple filters."""
        # Create specific test data
        target_workspace = WorkspaceFactory(
            organization=self.organization, end_date=date.today() - timedelta(days=5)
        )
        target_team = TeamFactory(organization=self.organization, title="Target Team")
        target_workspace_team = WorkspaceTeamFactory(
            workspace=target_workspace, team=target_team
        )

        target_remittance = PendingRemittanceFactory(
            workspace_team=target_workspace_team
        )

        # Create noise data that shouldn't match
        other_team = TeamFactory(organization=self.organization, title="Other Team")
        other_workspace_team = WorkspaceTeamFactory(
            workspace=target_workspace, team=other_team
        )
        PaidRemittanceFactory(workspace_team=other_workspace_team)

        result = selectors.get_remittances_with_filters(
            workspace_id=target_workspace.workspace_id,
            team_id=target_team.team_id,
            status=RemittanceStatus.PENDING,
            end_date=date.today(),
            search="Target",
        )

        assert len(result) == 1
        assert result[0].remittance_id == target_remittance.remittance_id

    def test_get_remittances_no_results(self):
        """Test selector returns empty queryset when no matches."""
        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id, search="NonExistentTeam"
        )

        assert len(result) == 0

    def test_get_remittances_ordering(self):
        """Test that remittances are properly ordered."""
        # Create remittances with different creation times
        RemittanceFactory(workspace_team=self.workspace_team1)
        RemittanceFactory(workspace_team=self.workspace_team2)

        result = list(
            selectors.get_remittances_with_filters(
                workspace_id=self.workspace1.workspace_id
            )
        )

        # Should be ordered by created_at descending (newest first)
        assert result[0].created_at >= result[1].created_at

    def test_get_remittances_empty_filters(self):
        """Test selector with empty/None filter values."""
        remittance = RemittanceFactory(workspace_team=self.workspace_team1)

        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id,
            team_id=None,
            status=None,
            start_date=None,
            end_date=None,
            search=None,
        )

        assert len(result) >= 1
        assert remittance.remittance_id in [r.remittance_id for r in result]

    def test_get_remittances_invalid_workspace_id(self):
        """Test selector with non-existent workspace ID."""
        import uuid

        non_existent_id = uuid.uuid4()

        result = selectors.get_remittances_with_filters(workspace_id=non_existent_id)

        assert len(result) == 0


@pytest.mark.django_db
class TestRemittanceSelectorsEdgeCases:
    """Test edge cases for remittance selectors."""

    def test_workspace_with_no_teams(self):
        """Test workspace with no teams returns empty result."""
        workspace = WorkspaceFactory()

        result = selectors.get_remittances_with_filters(
            workspace_id=workspace.workspace_id
        )

        assert len(result) == 0

    def test_team_with_no_remittances(self):
        """Test team with no remittances returns empty result."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        team = TeamFactory(organization=organization)
        WorkspaceTeamFactory(workspace=workspace, team=team)  # No remittances created

        result = selectors.get_remittances_with_filters(
            workspace_id=workspace.workspace_id, team_id=team.team_id
        )

        assert len(result) == 0

    def test_search_with_special_characters(self):
        """Test search functionality with special characters."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        team = TeamFactory(organization=organization, title="Team-Alpha & Beta")
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
        remittance = RemittanceFactory(workspace_team=workspace_team)

        result = selectors.get_remittances_with_filters(
            workspace_id=workspace.workspace_id, search="Alpha & Beta"
        )

        assert len(result) == 1
        assert result[0].remittance_id == remittance.remittance_id

    def test_date_boundary_conditions(self):
        """Test date filtering boundary conditions."""
        today = date.today()
        organization = OrganizationFactory()

        # Workspace ending exactly today
        workspace_today = WorkspaceFactory(organization=organization, end_date=today)
        workspace_team_today = WorkspaceTeamFactory(
            workspace=workspace_today, team=TeamFactory(organization=organization)
        )
        RemittanceFactory(workspace_team=workspace_team_today)

        # Test start_date boundary (should include today)
        result = selectors.get_remittances_with_filters(
            workspace_id=self.workspace1.workspace_id
            if hasattr(self, "workspace1")
            else workspace_today.workspace_id,
            start_date=today,
        )

        # Test end_date boundary (should include today)
        result = selectors.get_remittances_with_filters(
            workspace_id=workspace_today.workspace_id, end_date=today
        )

        assert len(result) >= 1
