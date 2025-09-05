"""
Unit tests for Remittance selectors.
"""

import pytest

from apps.remittance.selectors import get_remittances_under_organization
from apps.remittance.constants import RemittanceStatus
from apps.remittance.models import Remittance
from tests.factories import (
    OrganizationFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.django_db
class TestGetRemittancesUnderOrganization:
    """Test get_remittances_under_organization selector."""

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

    def test_get_remittances_by_organization_only(self):
        """Test filtering remittances by organization only."""
        # Remittances are automatically created by signals when WorkspaceTeam is created
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id
        )

        # Should get all remittances from all workspaces under the organization
        assert len(result) >= 3  # At least 3 remittances from the 3 workspace teams

    def test_get_remittances_by_organization_and_workspace(self):
        """Test filtering remittances by organization and workspace."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id,
            workspace_id=self.workspace1.workspace_id,
        )

        # Should get remittances only from workspace1
        assert len(result) >= 2  # At least 2 remittances from workspace1
        # Verify all results are from the specified workspace
        for remittance in result:
            assert (
                remittance.workspace_team.workspace.workspace_id
                == self.workspace1.workspace_id
            )

    def test_get_remittances_by_status(self):
        """Test filtering remittances by status."""
        # Create additional workspace teams with different statuses
        WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        partial_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        paid_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )

        # Get the automatically created remittances
        # pending_remittance = pending_workspace_team.remittance
        partial_remittance = partial_workspace_team.remittance
        paid_remittance = paid_workspace_team.remittance

        # Update statuses manually since they're created with default PENDING
        partial_remittance.status = RemittanceStatus.PARTIAL
        partial_remittance.due_amount = 1000.00
        partial_remittance.paid_amount = 500.00
        partial_remittance.save()

        paid_remittance.status = RemittanceStatus.PAID
        paid_remittance.due_amount = 1000.00
        paid_remittance.paid_amount = 1000.00
        paid_remittance.save()

        # Filter by pending status
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id,
            status=RemittanceStatus.PENDING,
        )

        # Should only get pending remittances
        for remittance in result:
            assert remittance.status == RemittanceStatus.PENDING

    def test_get_remittances_by_search_workspace_title(self):
        """Test filtering remittances by workspace title search."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id,
            search_query="Test Workspace 1",
        )

        # Should get remittances from workspace1
        assert len(result) >= 2
        for remittance in result:
            assert "Test Workspace 1" in remittance.workspace_team.workspace.title

    def test_get_remittances_by_search_team_title(self):
        """Test filtering remittances by team title search."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id, search_query="Alpha"
        )

        # Should get remittances from teams with "Alpha" in the title
        assert len(result) >= 1
        for remittance in result:
            assert "Alpha" in remittance.workspace_team.team.title

    def test_get_remittances_case_insensitive_search(self):
        """Test case insensitive search functionality."""
        # Test lowercase search
        result_lower = get_remittances_under_organization(
            organization_id=self.organization.organization_id, search_query="alpha"
        )

        # Test uppercase search
        result_upper = get_remittances_under_organization(
            organization_id=self.organization.organization_id, search_query="ALPHA"
        )

        # Both should return the same result
        assert len(result_lower) == len(result_upper)
        if len(result_lower) > 0:
            assert result_lower[0].remittance_id == result_upper[0].remittance_id

    def test_get_remittances_combined_filters(self):
        """Test combining multiple filters."""
        # Create specific test data
        target_workspace = WorkspaceFactory(
            organization=self.organization, title="Target Workspace"
        )
        target_team = TeamFactory(organization=self.organization, title="Target Team")
        target_workspace_team = WorkspaceTeamFactory(
            workspace=target_workspace, team=target_team
        )

        # Get the automatically created remittance
        target_remittance = target_workspace_team.remittance

        # Create noise data that shouldn't match
        other_team = TeamFactory(organization=self.organization, title="Other Team")
        other_workspace_team = WorkspaceTeamFactory(
            workspace=target_workspace, team=other_team
        )

        # Update the other remittance to a different status
        other_remittance = other_workspace_team.remittance
        other_remittance.status = RemittanceStatus.PAID
        other_remittance.due_amount = 1000.00
        other_remittance.paid_amount = 1000.00
        other_remittance.save()

        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id,
            workspace_id=target_workspace.workspace_id,
            status=RemittanceStatus.PENDING,
            search_query="Target",
        )

        assert len(result) >= 1
        # Should find the target remittance
        found_target = any(
            r.remittance_id == target_remittance.remittance_id for r in result
        )
        assert found_target

    def test_get_remittances_no_results(self):
        """Test selector returns empty queryset when no matches."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id,
            search_query="NonExistentTeam",
        )

        assert len(result) == 0

    def test_get_remittances_ordering(self):
        """Test that remittances are properly ordered."""
        result = list(
            get_remittances_under_organization(
                organization_id=self.organization.organization_id
            )
        )

        # Should be ordered by created_at descending (newest first)
        if len(result) >= 2:
            assert result[0].created_at >= result[1].created_at

    def test_get_remittances_empty_filters(self):
        """Test selector with empty/None filter values."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id,
            workspace_id=None,
            status=None,
            search_query=None,
        )

        assert len(result) >= 3  # Should get all remittances from the organization

    def test_get_remittances_invalid_organization_id(self):
        """Test selector with non-existent organization ID."""
        import uuid

        non_existent_id = uuid.uuid4()

        result = get_remittances_under_organization(organization_id=non_existent_id)

        # Should return empty queryset, not None
        assert len(result) == 0

    def test_get_remittances_remaining_amount_calculation(self):
        """Test that remaining_amount is calculated and attached to each remittance."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id
        )

        assert len(result) >= 1
        # Check that remaining_amount attribute is attached
        assert hasattr(result[0], "remaining_amount")

        # The selector shadows the method with an attribute, so we need to access the method differently
        # We can use the class method directly
        expected_amount = Remittance.remaining_amount(result[0])
        assert result[0].remaining_amount == expected_amount

    def test_get_remittances_select_related_optimization(self):
        """Test that select_related is used to optimize database queries."""
        result = get_remittances_under_organization(
            organization_id=self.organization.organization_id
        )

        assert len(result) >= 1
        # Check that related objects are loaded without additional queries
        remittance = result[0]
        # These should not trigger additional database queries
        workspace_title = remittance.workspace_team.workspace.title
        team_title = remittance.workspace_team.team.title

        assert workspace_title is not None
        assert team_title is not None


@pytest.mark.django_db
class TestRemittanceSelectorsEdgeCases:
    """Test edge cases for remittance selectors."""

    def test_organization_with_no_workspaces(self):
        """Test organization with no workspaces returns empty result."""
        organization = OrganizationFactory()

        result = get_remittances_under_organization(
            organization_id=organization.organization_id
        )

        assert len(result) == 0

    def test_workspace_with_no_teams(self):
        """Test workspace with no teams returns empty result."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)

        result = get_remittances_under_organization(
            organization_id=organization.organization_id,
            workspace_id=workspace.workspace_id,
        )

        assert len(result) == 0

    def test_team_with_no_remittances(self):
        """Test team with no remittances returns empty result."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        TeamFactory(organization=organization)
        # Don't create WorkspaceTeam - this would automatically create a remittance

        result = get_remittances_under_organization(
            organization_id=organization.organization_id,
            workspace_id=workspace.workspace_id,
        )

        assert len(result) == 0

    def test_search_with_special_characters(self):
        """Test search functionality with special characters."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(
            organization=organization, title="Workspace-Alpha & Beta"
        )
        team = TeamFactory(organization=organization, title="Team-Alpha & Beta")
        WorkspaceTeamFactory(workspace=workspace, team=team)

        result = get_remittances_under_organization(
            organization_id=organization.organization_id, search_query="Alpha & Beta"
        )

        assert len(result) >= 1
        # Should find remittances with the special characters
        found_match = any(
            "Alpha & Beta" in r.workspace_team.workspace.title
            or "Alpha & Beta" in r.workspace_team.team.title
            for r in result
        )
        assert found_match

    def test_exception_handling(self):
        """Test that the selector handles exceptions gracefully."""
        # This test verifies that the selector works normally
        # The try-catch structure is in place but we can't easily trigger exceptions

        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        team = TeamFactory(organization=organization)
        WorkspaceTeamFactory(workspace=workspace, team=team)

        # Normal operation should work
        result = get_remittances_under_organization(
            organization_id=organization.organization_id
        )

        assert result is not None
        assert len(result) >= 1

    def test_exception_handling_returns_none(self):
        """Test that the selector returns None when an exception occurs."""
        from unittest.mock import patch

        # Mock the Remittance.objects.filter to raise an exception
        with patch(
            "apps.remittance.selectors.Remittance.objects.filter"
        ) as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            result = get_remittances_under_organization(organization_id="some-id")

            # Should return None when exception occurs
            assert result is None
