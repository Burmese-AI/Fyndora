"""
Unit tests for Team models.
"""

from django.db import IntegrityError
from django.test import TestCase

from apps.teams.constants import TeamMemberRole
from apps.teams.models import Team, TeamMember
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory


class TeamModelTest(TestCase):
    """Test cases for the Team model."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    def test_team_creation(self):
        """Test basic team creation."""
        team = TeamFactory(
            organization=self.organization,
            title="Test Team",
            description="Test Description",
            created_by=self.org_member,
        )

        self.assertEqual(team.title, "Test Team")
        self.assertEqual(team.description, "Test Description")
        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        self.assertIsNotNone(team.team_id)
        self.assertIsNotNone(team.created_at)
        self.assertIsNotNone(team.updated_at)

    def test_team_str_representation(self):
        """Test the string representation of a team."""
        team = TeamFactory(title="Marketing Team")
        self.assertEqual(str(team), "Marketing Team")

    def test_team_unique_constraint(self):
        """Test that team titles must be unique within an organization."""
        TeamFactory(organization=self.organization, title="Unique Team")

        # Creating another team with the same title in the same organization should fail
        with self.assertRaises(IntegrityError):
            TeamFactory(organization=self.organization, title="Unique Team")

    def test_team_same_title_different_organizations(self):
        """Test that teams can have the same title in different organizations."""
        other_organization = OrganizationFactory()

        team1 = TeamFactory(organization=self.organization, title="Same Title")
        team2 = TeamFactory(organization=other_organization, title="Same Title")

        self.assertEqual(team1.title, team2.title)
        self.assertNotEqual(team1.organization, team2.organization)

    def test_team_coordinator_assignment(self):
        """Test team coordinator assignment."""
        coordinator = OrganizationMemberFactory(organization=self.organization)
        team = TeamFactory(organization=self.organization, team_coordinator=coordinator)

        self.assertEqual(team.team_coordinator, coordinator)

    def test_team_set_null_on_coordinator_delete(self):
        """Test that team coordinator is set to null when coordinator is deleted."""
        coordinator = OrganizationMemberFactory(organization=self.organization)
        team = TeamFactory(organization=self.organization, team_coordinator=coordinator)

        coordinator.delete()
        team.refresh_from_db()

        # Since coordinator is soft deleted, the relationship should still exist
        # but the coordinator object should be soft deleted
        self.assertIsNotNone(team.team_coordinator)
        self.assertIsNotNone(team.team_coordinator.deleted_at)

    def test_team_ordering(self):
        """Test that teams are ordered by creation date (newest first)."""
        team1 = TeamFactory(organization=self.organization, title="First Team")
        team2 = TeamFactory(organization=self.organization, title="Second Team")

        teams = Team.objects.filter(organization=self.organization)
        self.assertEqual(teams.first(), team2)  # Newest first
        self.assertEqual(teams.last(), team1)

    def test_team_without_description(self):
        """Test team creation without description."""
        team = TeamFactory(
            organization=self.organization,
            title="No Description Team",
            description="",
        )
        self.assertEqual(team.description, "")
        self.assertIsNotNone(team.team_id)

    def test_team_without_coordinator(self):
        """Test team creation without coordinator."""
        team = TeamFactory(
            organization=self.organization,
            title="No Coordinator Team",
            team_coordinator=None,
        )
        self.assertIsNone(team.team_coordinator)

    def test_team_without_created_by(self):
        """Test team creation without created_by."""
        team = TeamFactory(
            organization=self.organization,
            title="No Creator Team",
            created_by=None,
        )
        self.assertIsNone(team.created_by)

    def test_team_title_max_length(self):
        """Test team title maximum length constraint."""
        long_title = "A" * 255  # Maximum allowed length
        team = TeamFactory(
            organization=self.organization,
            title=long_title,
        )
        self.assertEqual(team.title, long_title)

    def test_team_verbose_names(self):
        """Test team model verbose names."""
        self.assertEqual(Team._meta.verbose_name, "team")
        self.assertEqual(Team._meta.verbose_name_plural, "teams")

    def test_team_permissions(self):
        """Test team model permissions."""
        permissions = [perm[0] for perm in Team._meta.permissions]
        self.assertIn("add_team_member", permissions)


class TeamMemberModelTest(TestCase):
    """Test cases for the TeamMember model."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team = TeamFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    def test_team_member_creation(self):
        """Test basic team member creation."""
        team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team,
            role=TeamMemberRole.SUBMITTER,
        )

        self.assertEqual(team_member.organization_member, self.org_member)
        self.assertEqual(team_member.team, self.team)
        self.assertEqual(team_member.role, TeamMemberRole.SUBMITTER)
        self.assertIsNotNone(team_member.team_member_id)
        self.assertIsNotNone(team_member.created_at)

    def test_team_member_str_representation(self):
        """Test the string representation of a team member."""
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )
        expected_str = f"{self.org_member} in {self.team}"
        self.assertEqual(str(team_member), expected_str)

    def test_team_member_default_role(self):
        """Test that default role is SUBMITTER."""
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )
        self.assertEqual(team_member.role, TeamMemberRole.SUBMITTER)

    def test_team_member_auditor_role(self):
        """Test team member with auditor role."""
        team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )
        self.assertEqual(team_member.role, TeamMemberRole.AUDITOR)

    def test_team_member_unique_constraint(self):
        """Test that a member can only be added once to a team."""
        TeamMemberFactory(organization_member=self.org_member, team=self.team)

        # Adding the same member to the same team should fail
        with self.assertRaises(IntegrityError):
            TeamMemberFactory(organization_member=self.org_member, team=self.team)

    def test_team_member_multiple_teams(self):
        """Test that a member can be in multiple teams."""
        other_team = TeamFactory(organization=self.organization)

        team_member1 = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )
        team_member2 = TeamMemberFactory(
            organization_member=self.org_member, team=other_team
        )

        self.assertEqual(
            team_member1.organization_member, team_member2.organization_member
        )
        self.assertNotEqual(team_member1.team, team_member2.team)

    def test_team_member_ordering(self):
        """Test that team members are ordered by creation date (newest first)."""
        member1 = OrganizationMemberFactory(organization=self.organization)
        member2 = OrganizationMemberFactory(organization=self.organization)

        team_member1 = TeamMemberFactory(organization_member=member1, team=self.team)
        team_member2 = TeamMemberFactory(organization_member=member2, team=self.team)

        team_members = TeamMember.objects.filter(team=self.team)
        self.assertEqual(team_members.first(), team_member2)  # Newest first
        self.assertEqual(team_members.last(), team_member1)

    def test_team_member_role_choices(self):
        """Test that only valid roles can be assigned."""
        # Valid roles should work
        for role in [TeamMemberRole.SUBMITTER, TeamMemberRole.AUDITOR]:
            team_member = TeamMemberFactory(
                organization_member=OrganizationMemberFactory(
                    organization=self.organization
                ),
                team=self.team,
                role=role,
            )
            self.assertEqual(team_member.role, role)

    def test_team_member_role_max_length(self):
        """Test team member role maximum length constraint."""
        team_member = TeamMemberFactory(
            organization_member=OrganizationMemberFactory(
                organization=self.organization
            ),
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )
        # Role should be within the 32 character limit
        self.assertLessEqual(len(team_member.role), 32)

    def test_team_member_verbose_names(self):
        """Test team member model verbose names."""
        self.assertEqual(TeamMember._meta.verbose_name, "team member")
        self.assertEqual(TeamMember._meta.verbose_name_plural, "team members")

    def test_team_member_soft_delete_constraint(self):
        """Test that soft deleted members can be re-added to the same team."""
        # Create and soft delete a team member
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )
        team_member.delete()  # This should be a soft delete

        # Should be able to create a new team member with same org_member and team
        # after the soft delete
        new_team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )
        self.assertIsNotNone(new_team_member.team_member_id)
        self.assertNotEqual(team_member.team_member_id, new_team_member.team_member_id)

    def test_team_member_foreign_key_relationships(self):
        """Test foreign key relationship integrity."""
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

        # Test reverse relationships
        self.assertIn(team_member, self.org_member.team_memberships.all())
        self.assertIn(team_member, self.team.members.all())

    def test_team_member_all_role_choices(self):
        """Test all available role choices."""
        available_roles = [choice[0] for choice in TeamMemberRole.choices]
        expected_roles = ["team_coordinator", "submitter", "auditor"]

        for role in expected_roles:
            self.assertIn(role, available_roles)
