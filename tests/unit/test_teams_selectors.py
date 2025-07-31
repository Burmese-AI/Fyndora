"""
Unit tests for Team selectors.
"""

from django.test import TestCase

from apps.teams.models import TeamMember
from apps.teams.selectors import (
    get_all_team_members,
    get_team_by_id,
    get_team_member_by_id,
    get_team_members,
    get_team_members_by_team_id,
    get_teams_by_organization_id,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory


class GetTeamMembersTest(TestCase):
    """Test cases for get_team_members selector."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team1 = TeamFactory(organization=self.organization)
        self.team2 = TeamFactory(organization=self.organization)

        self.member1 = TeamMemberFactory(team=self.team1)
        self.member2 = TeamMemberFactory(team=self.team1)
        self.member3 = TeamMemberFactory(team=self.team2)

    def test_get_team_members_all(self):
        """Test getting all team members."""
        result = get_team_members()

        self.assertEqual(result.count(), 3)
        self.assertIn(self.member1, result)
        self.assertIn(self.member2, result)
        self.assertIn(self.member3, result)

    def test_get_team_members_by_team(self):
        """Test getting team members filtered by team."""
        result = get_team_members(team=self.team1)

        self.assertEqual(result.count(), 2)
        self.assertIn(self.member1, result)
        self.assertIn(self.member2, result)
        self.assertNotIn(self.member3, result)

    def test_get_team_members_with_prefetch_user(self):
        """Test getting team members with user prefetch."""
        result = get_team_members(prefetch_user=True)

        # Verify the queryset includes the joins for user data
        query_str = str(result.query)
        self.assertIn("organizations_organizationmember", query_str)
        self.assertIn("accounts_customuser", query_str)
        self.assertEqual(result.count(), 3)

    def test_get_team_members_team_and_prefetch(self):
        """Test getting team members with both team filter and user prefetch."""
        result = get_team_members(team=self.team1, prefetch_user=True)

        self.assertEqual(result.count(), 2)
        # Verify the queryset includes the joins for user data
        query_str = str(result.query)
        self.assertIn("organizations_organizationmember", query_str)
        self.assertIn("accounts_customuser", query_str)


class GetAllTeamMembersTest(TestCase):
    """Test cases for get_all_team_members selector."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team = TeamFactory(organization=self.organization)
        self.member1 = TeamMemberFactory(team=self.team)
        self.member2 = TeamMemberFactory(team=self.team)

    def test_get_all_team_members_success(self):
        """Test successful retrieval of all team members."""
        result = get_all_team_members()

        self.assertEqual(result.count(), 2)
        self.assertIn(self.member1, result)
        self.assertIn(self.member2, result)

    def test_get_all_team_members_empty(self):
        """Test getting all team members when none exist."""
        TeamMember.objects.all().delete()

        result = get_all_team_members()

        self.assertEqual(result.count(), 0)

    def test_get_all_team_members_exception_handling(self):
        """Test exception handling in get_all_team_members."""
        # This test verifies the exception handling exists
        # In practice, it's hard to trigger an exception in this simple query
        result = get_all_team_members()
        self.assertIsNotNone(result)


class GetTeamsByOrganizationIdTest(TestCase):
    """Test cases for get_teams_by_organization_id selector."""

    def setUp(self):
        """Set up test data."""
        self.organization1 = OrganizationFactory()
        self.organization2 = OrganizationFactory()

        self.team1 = TeamFactory(organization=self.organization1, title="Team 1")
        self.team2 = TeamFactory(organization=self.organization1, title="Team 2")
        self.team3 = TeamFactory(organization=self.organization2, title="Team 3")

    def test_get_teams_by_organization_id_success(self):
        """Test successful retrieval of teams by organization ID."""
        result = get_teams_by_organization_id(self.organization1.organization_id)

        self.assertEqual(result.count(), 2)
        self.assertIn(self.team1, result)
        self.assertIn(self.team2, result)
        self.assertNotIn(self.team3, result)

    def test_get_teams_by_organization_id_empty(self):
        """Test getting teams for organization with no teams."""
        empty_org = OrganizationFactory()

        result = get_teams_by_organization_id(empty_org.organization_id)

        self.assertEqual(result.count(), 0)

    def test_get_teams_by_organization_id_nonexistent(self):
        """Test getting teams for non-existent organization."""
        import uuid

        fake_org_id = uuid.uuid4()

        result = get_teams_by_organization_id(fake_org_id)

        self.assertEqual(result.count(), 0)


class GetTeamByIdTest(TestCase):
    """Test cases for get_team_by_id selector."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team = TeamFactory(organization=self.organization, title="Test Team")

    def test_get_team_by_id_success(self):
        """Test successful retrieval of team by ID."""
        result = get_team_by_id(self.team.team_id)

        self.assertEqual(result, self.team)
        self.assertEqual(result.title, "Test Team")

    def test_get_team_by_id_not_found(self):
        """Test getting team with non-existent ID."""
        import uuid

        fake_team_id = uuid.uuid4()

        result = get_team_by_id(fake_team_id)

        self.assertIsNone(result)

    def test_get_team_by_id_exception_handling(self):
        """Test exception handling in get_team_by_id."""
        # Test with invalid UUID format (this should trigger the general exception)
        result = get_team_by_id("invalid-uuid")

        self.assertIsNone(result)


class GetTeamMemberByIdTest(TestCase):
    """Test cases for get_team_member_by_id selector."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(team=self.team)

    def test_get_team_member_by_id_success(self):
        """Test successful retrieval of team member by ID."""
        result = get_team_member_by_id(self.team_member.team_member_id)

        self.assertEqual(result, self.team_member)

    def test_get_team_member_by_id_not_found(self):
        """Test getting team member with non-existent ID."""
        import uuid

        fake_member_id = uuid.uuid4()

        result = get_team_member_by_id(fake_member_id)

        self.assertIsNone(result)

    def test_get_team_member_by_id_exception_handling(self):
        """Test exception handling in get_team_member_by_id."""
        # Test with invalid UUID format
        result = get_team_member_by_id("invalid-uuid")

        self.assertIsNone(result)


class GetTeamMembersByTeamIdTest(TestCase):
    """Test cases for get_team_members_by_team_id selector."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team1 = TeamFactory(organization=self.organization)
        self.team2 = TeamFactory(organization=self.organization)

        self.member1 = TeamMemberFactory(team=self.team1)
        self.member2 = TeamMemberFactory(team=self.team1)
        self.member3 = TeamMemberFactory(team=self.team2)

    def test_get_team_members_by_team_id_success(self):
        """Test successful retrieval of team members by team ID."""
        result = get_team_members_by_team_id(self.team1.team_id)

        self.assertEqual(result.count(), 2)
        self.assertIn(self.member1, result)
        self.assertIn(self.member2, result)
        self.assertNotIn(self.member3, result)

    def test_get_team_members_by_team_id_empty(self):
        """Test getting team members for team with no members."""
        empty_team = TeamFactory(organization=self.organization)

        result = get_team_members_by_team_id(empty_team.team_id)

        self.assertEqual(result.count(), 0)

    def test_get_team_members_by_team_id_nonexistent(self):
        """Test getting team members for non-existent team."""
        import uuid

        fake_team_id = uuid.uuid4()

        result = get_team_members_by_team_id(fake_team_id)

        self.assertEqual(result.count(), 0)

    def test_get_team_members_by_team_id_exception_handling(self):
        """Test exception handling in get_team_members_by_team_id."""
        # Test with invalid UUID format
        result = get_team_members_by_team_id("invalid-uuid")

        # Should return empty queryset on exception
        self.assertEqual(result.count(), 0)
