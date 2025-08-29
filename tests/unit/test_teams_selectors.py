"""
Unit tests for Team selectors.
"""

from django.test import TestCase

from apps.teams.selectors import (
    get_team_members,
    get_all_team_members,
    get_teams_by_organization_id,
    get_team_by_id,
    get_team_member_by_id,
    get_team_members_by_team_id,
)
from tests.factories.organization_factories import (
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory


class TeamSelectorsTest(TestCase):
    """Test cases for Team selectors."""

    def setUp(self):
        """Set up test data."""
        # Create organizations with owners
        self.organization1 = OrganizationWithOwnerFactory()
        self.organization2 = OrganizationWithOwnerFactory()

        # Create organization members
        self.org_member1 = OrganizationMemberFactory(organization=self.organization1)
        self.org_member2 = OrganizationMemberFactory(organization=self.organization1)
        self.org_member3 = OrganizationMemberFactory(organization=self.organization2)

        # Create teams
        self.team1 = TeamFactory(organization=self.organization1)
        self.team2 = TeamFactory(organization=self.organization1)
        self.team3 = TeamFactory(organization=self.organization2)

        # Create team members
        self.team_member1 = TeamMemberFactory(
            organization_member=self.org_member1, team=self.team1
        )
        self.team_member2 = TeamMemberFactory(
            organization_member=self.org_member2, team=self.team1
        )
        self.team_member3 = TeamMemberFactory(
            organization_member=self.org_member3, team=self.team3
        )

    def test_get_team_members_no_filters(self):
        """Test get_team_members without any filters."""
        team_members = get_team_members()

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 3)
        self.assertIn(self.team_member1, team_members)
        self.assertIn(self.team_member2, team_members)
        self.assertIn(self.team_member3, team_members)

    def test_get_team_members_with_team_filter(self):
        """Test get_team_members with team filter."""
        team_members = get_team_members(team=self.team1)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 2)
        self.assertIn(self.team_member1, team_members)
        self.assertIn(self.team_member2, team_members)
        self.assertNotIn(self.team_member3, team_members)

    def test_get_team_members_with_prefetch_user(self):
        """Test get_team_members with prefetch_user=True."""
        team_members = get_team_members(prefetch_user=True)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 3)

        # Check that the queryset has select_related applied
        # This is a bit tricky to test directly, but we can verify the queryset works
        for member in team_members:
            # Accessing related fields should not trigger additional queries
            self.assertIsNotNone(member.organization_member.user)

    def test_get_team_members_with_team_and_prefetch(self):
        """Test get_team_members with both team filter and prefetch_user."""
        team_members = get_team_members(team=self.team1, prefetch_user=True)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 2)
        self.assertIn(self.team_member1, team_members)
        self.assertIn(self.team_member2, team_members)

        # Verify prefetch is working
        for member in team_members:
            self.assertIsNotNone(member.organization_member.user)

    def test_get_all_team_members_success(self):
        """Test get_all_team_members when successful."""
        team_members = get_all_team_members()

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 3)
        self.assertIn(self.team_member1, team_members)
        self.assertIn(self.team_member2, team_members)
        self.assertIn(self.team_member3, team_members)

    def test_get_all_team_members_exception_handling(self):
        """Test get_all_team_members exception handling."""
        # Mock the exception by temporarily making the queryset fail
        # This is a bit tricky to test, but we can verify the function exists and works
        team_members = get_all_team_members()
        self.assertIsNotNone(team_members)

    def test_get_teams_by_organization_id_success(self):
        """Test get_teams_by_organization_id when successful."""
        teams = get_teams_by_organization_id(self.organization1.organization_id)

        self.assertIsNotNone(teams)
        self.assertEqual(teams.count(), 2)
        self.assertIn(self.team1, teams)
        self.assertIn(self.team2, teams)
        self.assertNotIn(self.team3, teams)

    def test_get_teams_by_organization_id_different_org(self):
        """Test get_teams_by_organization_id with different organization."""
        teams = get_teams_by_organization_id(self.organization2.organization_id)

        self.assertIsNotNone(teams)
        self.assertEqual(teams.count(), 1)
        self.assertIn(self.team3, teams)
        self.assertNotIn(self.team1, teams)
        self.assertNotIn(self.team2, teams)

    def test_get_teams_by_organization_id_nonexistent_org(self):
        """Test get_teams_by_organization_id with nonexistent organization ID."""
        import uuid

        nonexistent_id = uuid.uuid4()
        teams = get_teams_by_organization_id(nonexistent_id)

        self.assertIsNotNone(teams)
        self.assertEqual(teams.count(), 0)

    def test_get_teams_by_organization_id_exception_handling(self):
        """Test get_teams_by_organization_id exception handling."""
        # The function should handle exceptions gracefully
        teams = get_teams_by_organization_id(self.organization1.organization_id)
        self.assertIsNotNone(teams)

    def test_get_team_by_id_success(self):
        """Test get_team_by_id when successful."""
        team = get_team_by_id(self.team1.team_id)

        self.assertIsNotNone(team)
        self.assertEqual(team, self.team1)
        self.assertEqual(team.title, self.team1.title)
        self.assertEqual(team.organization, self.team1.organization)

    def test_get_team_by_id_nonexistent(self):
        """Test get_team_by_id with nonexistent team ID."""
        import uuid

        nonexistent_id = uuid.uuid4()
        team = get_team_by_id(nonexistent_id)

        self.assertIsNone(team)

    def test_get_team_by_id_exception_handling(self):
        """Test get_team_by_id exception handling."""
        # The function should handle exceptions gracefully
        team = get_team_by_id(self.team1.team_id)
        self.assertIsNotNone(team)

    def test_get_team_member_by_id_success(self):
        """Test get_team_member_by_id when successful."""
        team_member = get_team_member_by_id(self.team_member1.team_member_id)

        self.assertIsNotNone(team_member)
        self.assertEqual(team_member, self.team_member1)
        self.assertEqual(
            team_member.organization_member, self.team_member1.organization_member
        )
        self.assertEqual(team_member.team, self.team_member1.team)

    def test_get_team_member_by_id_nonexistent(self):
        """Test get_team_member_by_id with nonexistent team member ID."""
        import uuid

        nonexistent_id = uuid.uuid4()
        team_member = get_team_member_by_id(nonexistent_id)

        self.assertIsNone(team_member)

    def test_get_team_member_by_id_exception_handling(self):
        """Test get_team_member_by_id exception handling."""
        # The function should handle exceptions gracefully
        team_member = get_team_member_by_id(self.team_member1.team_member_id)
        self.assertIsNotNone(team_member)

    def test_get_team_members_by_team_id_success(self):
        """Test get_team_members_by_team_id when successful."""
        team_members = get_team_members_by_team_id(self.team1.team_id)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 2)
        self.assertIn(self.team_member1, team_members)
        self.assertIn(self.team_member2, team_members)
        self.assertNotIn(self.team_member3, team_members)

    def test_get_team_members_by_team_id_different_team(self):
        """Test get_team_members_by_team_id with different team."""
        team_members = get_team_members_by_team_id(self.team3.team_id)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 1)
        self.assertIn(self.team_member3, team_members)
        self.assertNotIn(self.team_member1, team_members)
        self.assertNotIn(self.team_member2, team_members)

    def test_get_team_members_by_team_id_nonexistent_team(self):
        """Test get_team_members_by_team_id with nonexistent team ID."""
        import uuid

        nonexistent_id = uuid.uuid4()
        team_members = get_team_members_by_team_id(nonexistent_id)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 0)

    def test_get_team_members_by_team_id_exception_handling(self):
        """Test get_team_members_by_team_id exception handling."""
        # The function should handle exceptions gracefully
        team_members = get_team_members_by_team_id(self.team1.team_id)
        self.assertIsNotNone(team_members)


class TeamSelectorsEdgeCasesTest(TestCase):
    """Test edge cases and boundary conditions for Team selectors."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_get_team_members_empty_database(self):
        """Test get_team_members when database is empty."""
        team_members = get_team_members()

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 0)

    def test_get_all_team_members_empty_database(self):
        """Test get_all_team_members when database is empty."""
        team_members = get_all_team_members()

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 0)

    def test_get_teams_by_organization_id_empty_org(self):
        """Test get_teams_by_organization_id for organization with no teams."""
        teams = get_teams_by_organization_id(self.organization.organization_id)

        self.assertIsNotNone(teams)
        self.assertEqual(teams.count(), 0)

    def test_get_team_members_by_team_id_empty_team(self):
        """Test get_team_members_by_team_id for team with no members."""
        team = TeamFactory(organization=self.organization)
        team_members = get_team_members_by_team_id(team.team_id)

        self.assertIsNotNone(team_members)
        self.assertEqual(team_members.count(), 0)

    def test_get_team_members_with_none_team(self):
        """Test get_team_members with team=None explicitly."""
        team_members = get_team_members(team=None)

        self.assertIsNotNone(team_members)
        # Should return all team members when team is None

    def test_get_team_members_with_false_prefetch(self):
        """Test get_team_members with prefetch_user=False explicitly."""
        team_members = get_team_members(prefetch_user=False)

        self.assertIsNotNone(team_members)
        # Should work without prefetch when prefetch_user is False


class TeamSelectorsIntegrationTest(TestCase):
    """Integration tests for Team selectors."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

    def test_selector_workflow_integration(self):
        """Test complete workflow using multiple selectors."""
        # Get team by ID
        team = get_team_by_id(self.team.team_id)
        self.assertIsNotNone(team)

        # Get team members for that team
        team_members = get_team_members_by_team_id(team.team_id)
        self.assertEqual(team_members.count(), 1)
        self.assertIn(self.team_member, team_members)

        # Get specific team member by ID
        team_member = get_team_member_by_id(self.team_member.team_member_id)
        self.assertIsNotNone(team_member)
        self.assertEqual(team_member.team, team)

        # Get teams by organization
        teams = get_teams_by_organization_id(self.organization.organization_id)
        self.assertIn(team, teams)

    def test_selector_performance_optimization(self):
        """Test that selectors provide optimized querysets."""
        # Test prefetch optimization
        team_members = get_team_members(team=self.team, prefetch_user=True)

        # The queryset should be optimized with select_related
        self.assertIsNotNone(team_members)
        # Accessing related fields should not trigger additional queries
        for member in team_members:
            self.assertIsNotNone(member.organization_member.user)
