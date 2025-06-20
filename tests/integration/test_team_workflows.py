"""
Integration tests for Team workflows.

Tests how teams work with organizations, members, coordinators, and workspaces.
"""

import pytest
from decimal import Decimal
from django.db import IntegrityError

from apps.teams.models import Team, TeamMember
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    TeamFactory,
    TeamMemberFactory,
    TeamCoordinatorFactory,
    OperationsReviewerFactory,
    WorkspaceAdminMemberFactory,
    AuditorMemberFactory,
)


@pytest.mark.integration
@pytest.mark.django_db
class TestTeamCreationWorkflows:
    """Test team creation and basic management workflows."""

    def test_create_team_with_coordinator_workflow(self):
        """Test complete team creation with coordinator assignment."""
        # Create organization and members
        org = OrganizationFactory()
        coordinator_member = OrganizationMemberFactory(organization=org)

        # Create fundraising team with coordinator
        team = TeamFactory(
            organization=org,
            title="Downtown Fundraising Team",
            description="Urban fundraising and outreach team",
            team_coordinator=coordinator_member,
            created_by=coordinator_member,
        )

        # Verify team creation
        assert team.title == "Downtown Fundraising Team"
        assert team.team_coordinator == coordinator_member
        assert team.created_by == coordinator_member
        assert team.team_coordinator.organization == org
        assert team.organization == org

        # Create team member entry for coordinator
        team_member = TeamCoordinatorFactory(
            team=team, organization_member=coordinator_member
        )

        # Verify coordinator is also a team member
        assert team_member.role == TeamMemberRole.TEAM_COORDINATOR
        assert team_member.team == team
        assert team_member.organization_member == coordinator_member

    def test_team_with_custom_remittance_rate_workflow(self):
        """Test team creation with custom remittance rate."""
        org = OrganizationFactory()
        team = TeamFactory(
            organization=org,
            title="Elite Fundraising Unit", 
            custom_remittance_rate=Decimal("95.00")
        )

        assert team.custom_remittance_rate == Decimal("95.00")
        assert team.title == "Elite Fundraising Unit"
        assert team.organization == org

    def test_team_unique_title_constraint(self):
        """Test that fundraising team titles must be unique across all teams."""
        org = OrganizationFactory()
        TeamFactory(organization=org, title="North Valley Fundraising Team")

        # Attempting to create another team with same title should fail
        with pytest.raises(IntegrityError):
            TeamFactory(organization=org, title="North Valley Fundraising Team")


@pytest.mark.integration
@pytest.mark.django_db
class TestTeamMembershipWorkflows:
    """Test team membership management workflows."""

    def test_add_multiple_members_to_team_workflow(self):
        """Test adding multiple members with different roles to a team."""
        # Setup
        org = OrganizationFactory()
        team = TeamFactory(organization=org)

        # Create organization members
        coord_org_member = OrganizationMemberFactory(organization=org)
        reviewer_org_member = OrganizationMemberFactory(organization=org)
        submitter_org_member = OrganizationMemberFactory(organization=org)
        admin_org_member = OrganizationMemberFactory(organization=org)
        auditor_org_member = OrganizationMemberFactory(organization=org)

        # Add members with different roles
        TeamCoordinatorFactory(team=team, organization_member=coord_org_member)
        OperationsReviewerFactory(team=team, organization_member=reviewer_org_member)
        TeamMemberFactory(
            team=team,
            organization_member=submitter_org_member,
            role=TeamMemberRole.SUBMITTER,
        )
        WorkspaceAdminMemberFactory(team=team, organization_member=admin_org_member)
        AuditorMemberFactory(team=team, organization_member=auditor_org_member)

        # Verify all members added correctly
        team_members = team.members.all()
        assert team_members.count() == 5

        # Verify roles
        roles = [member.role for member in team_members]
        expected_roles = [
            TeamMemberRole.TEAM_COORDINATOR,
            TeamMemberRole.OPERATIONS_REVIEWER,
            TeamMemberRole.SUBMITTER,
            TeamMemberRole.WORKSPACE_ADMIN,
            TeamMemberRole.AUDITOR,
        ]
        for role in expected_roles:
            assert role in roles

    def test_team_member_unique_constraint_workflow(self):
        """Test that organization member can only be added once per team."""
        org = OrganizationFactory()
        team = TeamFactory(organization=org)
        org_member = OrganizationMemberFactory(organization=org)

        # Add member first time - should succeed
        TeamMemberFactory(team=team, organization_member=org_member)

        # Try to add same member again - should fail
        with pytest.raises(IntegrityError):
            TeamMemberFactory(team=team, organization_member=org_member)

    def test_organization_member_multiple_teams_workflow(self):
        """Test that organization member can be in multiple different teams."""
        org = OrganizationFactory()
        org_member = OrganizationMemberFactory(organization=org)
        team1 = TeamFactory(organization=org, title="West Coast Fundraising")
        team2 = TeamFactory(organization=org, title="East Coast Operations")

        # Add same org member to different teams
        member1 = TeamMemberFactory(
            team=team1, organization_member=org_member, role=TeamMemberRole.SUBMITTER
        )
        member2 = TeamCoordinatorFactory(team=team2, organization_member=org_member)

        # Verify memberships
        assert member1.team == team1
        assert member2.team == team2
        assert member1.organization_member == org_member
        assert member2.organization_member == org_member
        assert member1.role == TeamMemberRole.SUBMITTER
        assert member2.role == TeamMemberRole.TEAM_COORDINATOR


@pytest.mark.integration
@pytest.mark.django_db
class TestTeamHierarchyWorkflows:
    """Test team hierarchy and role-based workflows."""

    def test_team_coordinator_assignment_workflow(self):
        """Test assigning and reassigning team coordinators."""
        org = OrganizationFactory()
        team = TeamFactory(organization=org)

        # Create two potential coordinators
        coord1_org_member = OrganizationMemberFactory(organization=org)
        coord2_org_member = OrganizationMemberFactory(organization=org)

        # Assign first coordinator
        coord1 = TeamCoordinatorFactory(
            team=team, organization_member=coord1_org_member
        )

        # Update team to have this coordinator
        team.team_coordinator = coord1_org_member
        team.save()

        assert team.team_coordinator == coord1_org_member
        assert coord1.role == TeamMemberRole.TEAM_COORDINATOR

        # Reassign to new coordinator
        TeamCoordinatorFactory(team=team, organization_member=coord2_org_member)

        team.team_coordinator = coord2_org_member
        team.save()

        # Verify reassignment
        team.refresh_from_db()
        assert team.team_coordinator == coord2_org_member

    def test_reviewer_hierarchy_workflow(self):
        """Test that reviewers can review submissions from submitters."""
        org = OrganizationFactory()
        team = TeamFactory(organization=org)

        # Create reviewer and submitter
        reviewer = OperationsReviewerFactory(team=team)
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Verify hierarchy setup
        assert reviewer.role == TeamMemberRole.OPERATIONS_REVIEWER
        assert submitter.role == TeamMemberRole.SUBMITTER
        assert reviewer.team == submitter.team

        # Both should be in same team but different roles
        team_roles = team.members.values_list("role", flat=True)
        assert TeamMemberRole.OPERATIONS_REVIEWER in team_roles
        assert TeamMemberRole.SUBMITTER in team_roles


@pytest.mark.integration
@pytest.mark.django_db
class TestTeamQueryWorkflows:
    """Test team querying and filtering workflows."""

    def test_get_teams_by_coordinator_workflow(self):
        """Test getting all teams coordinated by a specific member."""
        org = OrganizationFactory()
        coordinator_member = OrganizationMemberFactory(organization=org)

        # Create teams with this coordinator
        team1 = TeamFactory(organization=org, team_coordinator=coordinator_member)
        team2 = TeamFactory(organization=org, team_coordinator=coordinator_member)
        team3 = TeamFactory(organization=org)  # Different coordinator

        # Query teams by coordinator
        coordinated_teams = Team.objects.filter(team_coordinator=coordinator_member)

        assert coordinated_teams.count() == 2
        assert team1 in coordinated_teams
        assert team2 in coordinated_teams
        assert team3 not in coordinated_teams

    def test_get_team_members_by_role_workflow(self):
        """Test getting team members filtered by role."""
        org = OrganizationFactory()
        team = TeamFactory(organization=org)

        # Add members with different roles
        coord = TeamCoordinatorFactory(team=team)
        submitter1 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        submitter2 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        reviewer = OperationsReviewerFactory(team=team)

        # Query by role
        submitters = team.members.filter(role=TeamMemberRole.SUBMITTER)
        coordinators = team.members.filter(role=TeamMemberRole.TEAM_COORDINATOR)
        reviewers = team.members.filter(role=TeamMemberRole.OPERATIONS_REVIEWER)

        # Verify filtering
        assert submitters.count() == 2
        assert coordinators.count() == 1
        assert reviewers.count() == 1

        assert submitter1 in submitters
        assert submitter2 in submitters
        assert coord in coordinators
        assert reviewer in reviewers

    def test_get_organization_member_teams_workflow(self):
        """Test getting all teams for a specific organization member."""
        org = OrganizationFactory()
        org_member = OrganizationMemberFactory(organization=org)

        # Add to multiple teams with different roles
        team1 = TeamFactory(organization=org)
        team2 = TeamFactory(organization=org)
        team3 = TeamFactory(organization=org)

        TeamMemberFactory(
            team=team1, organization_member=org_member, role=TeamMemberRole.SUBMITTER
        )
        TeamCoordinatorFactory(team=team2, organization_member=org_member)
        # Not in team3

        # Query teams for this org member
        member_teams = TeamMember.objects.filter(
            organization_member=org_member
        ).select_related("team")

        assert member_teams.count() == 2
        team_ids = [tm.team.team_id for tm in member_teams]
        assert team1.team_id in team_ids
        assert team2.team_id in team_ids
        assert team3.team_id not in team_ids
