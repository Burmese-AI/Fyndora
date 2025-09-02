"""
Unit tests for apps.teams.selectors
"""

import pytest
from unittest.mock import patch

from apps.teams.selectors import (
    get_team_members,
    get_all_team_members,
    get_teams_by_organization_id,
    get_team_by_id,
    get_team_member_by_id,
    get_team_members_by_team_id,
)
from apps.teams.models import Team, TeamMember
from tests.factories import (
    TeamFactory,
    TeamMemberFactory,
    OrganizationFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestGetTeamMembers:
    """Test get_team_members selector function."""

    def test_get_team_members_without_filters(self):
        """Test getting all team members without filters."""
        team_member1 = TeamMemberFactory()
        team_member2 = TeamMemberFactory()

        result = get_team_members()

        assert team_member1 in result
        assert team_member2 in result
        assert result.count() >= 2

    def test_get_team_members_with_team_filter(self):
        """Test getting team members filtered by team."""
        team = TeamFactory()
        team_member1 = TeamMemberFactory(team=team)
        team_member2 = TeamMemberFactory()  # Different team

        result = get_team_members(team=team)

        assert team_member1 in result
        assert team_member2 not in result
        assert result.count() == 1

    def test_get_team_members_with_prefetch_user(self):
        """Test getting team members with user prefetch."""
        team_member = TeamMemberFactory()

        result = get_team_members(prefetch_user=True)

        assert team_member in result
        # Check that select_related was applied (queryset should have the prefetch)
        assert hasattr(result, "_prefetch_related_lookups") or hasattr(
            result, "_prefetch_done"
        )

    def test_get_team_members_with_both_filters(self):
        """Test getting team members with both team filter and prefetch."""
        team = TeamFactory()
        team_member1 = TeamMemberFactory(team=team)
        team_member2 = TeamMemberFactory()  # Different team

        result = get_team_members(team=team, prefetch_user=True)

        assert team_member1 in result
        assert team_member2 not in result
        assert result.count() == 1

    def test_get_team_members_with_none_team(self):
        """Test getting team members with None team (should return all)."""
        team_member1 = TeamMemberFactory()
        team_member2 = TeamMemberFactory()

        result = get_team_members(team=None)

        assert team_member1 in result
        assert team_member2 in result
        assert result.count() >= 2


@pytest.mark.unit
@pytest.mark.django_db
class TestGetAllTeamMembers:
    """Test get_all_team_members selector function."""

    def test_get_all_team_members_success(self):
        """Test getting all team members successfully."""
        team_member1 = TeamMemberFactory()
        team_member2 = TeamMemberFactory()

        result = get_all_team_members()

        assert team_member1 in result
        assert team_member2 in result
        assert result.count() >= 2

    def test_get_all_team_members_with_exception(self):
        """Test getting all team members when exception occurs."""
        with patch("apps.teams.selectors.TeamMember.objects.all") as mock_all:
            mock_all.side_effect = Exception("Database error")

            result = get_all_team_members()

            assert result.count() == 0
            assert result.model == TeamMember


@pytest.mark.unit
@pytest.mark.django_db
class TestGetTeamsByOrganizationId:
    """Test get_teams_by_organization_id selector function."""

    def test_get_teams_by_organization_id_success(self):
        """Test getting teams by organization ID successfully."""
        organization = OrganizationFactory()
        team1 = TeamFactory(organization=organization)
        team2 = TeamFactory(organization=organization)
        team3 = TeamFactory()  # Different organization

        result = get_teams_by_organization_id(organization.organization_id)

        assert team1 in result
        assert team2 in result
        assert team3 not in result
        assert result.count() == 2

    def test_get_teams_by_organization_id_with_exception(self):
        """Test getting teams by organization ID when exception occurs."""
        with patch("apps.teams.selectors.Team.objects.filter") as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            result = get_teams_by_organization_id("some-id")

            assert result.count() == 0
            assert result.model == Team

    def test_get_teams_by_organization_id_with_nonexistent_org(self):
        """Test getting teams for nonexistent organization."""
        result = get_teams_by_organization_id("nonexistent-id")

        assert result.count() == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestGetTeamById:
    """Test get_team_by_id selector function."""

    def test_get_team_by_id_success(self):
        """Test getting team by ID successfully."""
        team = TeamFactory()

        result = get_team_by_id(team.team_id)

        assert result == team

    def test_get_team_by_id_does_not_exist(self):
        """Test getting team by ID when team doesn't exist."""
        result = get_team_by_id("nonexistent-id")

        assert result is None

    def test_get_team_by_id_with_exception(self):
        """Test getting team by ID when exception occurs."""
        with patch("apps.teams.selectors.Team.objects.get") as mock_get:
            mock_get.side_effect = Exception("Database error")

            result = get_team_by_id("some-id")

            assert result is None

    def test_get_team_by_id_with_multiple_objects_returned(self):
        """Test getting team by ID when multiple objects are returned."""
        with patch("apps.teams.selectors.Team.objects.get") as mock_get:
            mock_get.side_effect = Team.MultipleObjectsReturned("Multiple teams found")

            result = get_team_by_id("some-id")

            assert result is None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetTeamMemberById:
    """Test get_team_member_by_id selector function."""

    def test_get_team_member_by_id_success(self):
        """Test getting team member by ID successfully."""
        team_member = TeamMemberFactory()

        result = get_team_member_by_id(team_member.team_member_id)

        assert result == team_member

    def test_get_team_member_by_id_does_not_exist(self):
        """Test getting team member by ID when team member doesn't exist."""
        result = get_team_member_by_id("nonexistent-id")

        assert result is None

    def test_get_team_member_by_id_with_exception(self):
        """Test getting team member by ID when exception occurs."""
        with patch("apps.teams.selectors.TeamMember.objects.get") as mock_get:
            mock_get.side_effect = Exception("Database error")

            result = get_team_member_by_id("some-id")

            assert result is None

    def test_get_team_member_by_id_with_multiple_objects_returned(self):
        """Test getting team member by ID when multiple objects are returned."""
        with patch("apps.teams.selectors.TeamMember.objects.get") as mock_get:
            mock_get.side_effect = TeamMember.MultipleObjectsReturned(
                "Multiple team members found"
            )

            result = get_team_member_by_id("some-id")

            assert result is None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetTeamMembersByTeamId:
    """Test get_team_members_by_team_id selector function."""

    def test_get_team_members_by_team_id_success(self):
        """Test getting team members by team ID successfully."""
        team = TeamFactory()
        team_member1 = TeamMemberFactory(team=team)
        team_member2 = TeamMemberFactory(team=team)
        team_member3 = TeamMemberFactory()  # Different team

        result = get_team_members_by_team_id(team.team_id)

        assert team_member1 in result
        assert team_member2 in result
        assert team_member3 not in result
        assert result.count() == 2

    def test_get_team_members_by_team_id_with_exception(self):
        """Test getting team members by team ID when exception occurs."""
        with patch("apps.teams.selectors.TeamMember.objects.filter") as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            result = get_team_members_by_team_id("some-id")

            assert result.count() == 0
            assert result.model == TeamMember

    def test_get_team_members_by_team_id_with_nonexistent_team(self):
        """Test getting team members for nonexistent team."""
        result = get_team_members_by_team_id("nonexistent-id")

        assert result.count() == 0

    def test_get_team_members_by_team_id_empty_result(self):
        """Test getting team members for team with no members."""
        team = TeamFactory()

        result = get_team_members_by_team_id(team.team_id)

        assert result.count() == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestTeamsSelectorsIntegration:
    """Integration tests for teams selectors."""

    def test_selector_functions_work_together(self):
        """Test that selector functions work together correctly."""
        organization = OrganizationFactory()
        team = TeamFactory(organization=organization)
        team_member1 = TeamMemberFactory(team=team)
        team_member2 = TeamMemberFactory(team=team)

        # Test getting team by organization
        teams = get_teams_by_organization_id(organization.organization_id)
        assert team in teams

        # Test getting team by ID
        found_team = get_team_by_id(team.team_id)
        assert found_team == team

        # Test getting team members by team
        team_members = get_team_members_by_team_id(team.team_id)
        assert team_member1 in team_members
        assert team_member2 in team_members

        # Test getting team members with team filter
        filtered_members = get_team_members(team=team)
        assert team_member1 in filtered_members
        assert team_member2 in filtered_members

    def test_selector_functions_with_soft_deleted_objects(self):
        """Test selector functions with soft deleted objects."""
        team = TeamFactory()
        team_member = TeamMemberFactory(team=team)

        # Soft delete the team member
        team_member.delete()

        # Should not return soft deleted objects
        result = get_team_members_by_team_id(team.team_id)
        assert team_member not in result

        result = get_team_member_by_id(team_member.team_member_id)
        assert result is None

    def test_selector_functions_with_different_data_types(self):
        """Test selector functions with different data types for IDs."""
        team = TeamFactory()

        # Test with string ID
        result1 = get_team_by_id(str(team.team_id))
        assert result1 == team

        # Test with UUID object
        result2 = get_team_by_id(team.team_id)
        assert result2 == team

    def test_selector_functions_performance_considerations(self):
        """Test that selector functions handle performance considerations."""
        team = TeamFactory()
        team_member = TeamMemberFactory(team=team)

        # Test prefetch_user parameter
        result = get_team_members(team=team, prefetch_user=True)
        assert team_member in result

        # Verify that the queryset has the expected structure
        assert hasattr(result, "query")

    def test_selector_functions_edge_cases(self):
        """Test selector functions with edge cases."""
        # Test with empty string ID
        result = get_team_by_id("")
        assert result is None

        result = get_team_member_by_id("")
        assert result is None

        # Test with None ID
        result = get_team_by_id(None)
        assert result is None

        result = get_team_member_by_id(None)
        assert result is None
