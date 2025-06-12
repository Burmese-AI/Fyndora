"""
Unit tests for Team factories.
"""

import pytest
from decimal import Decimal

from apps.teams.models import Team, TeamMember
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    TeamFactory,
    TeamWithCoordinatorFactory,
    TeamMemberFactory,
    TeamCoordinatorFactory,
    OperationsReviewerFactory,
    WorkspaceAdminMemberFactory,
    AuditorMemberFactory,
    TeamWithCustomRateFactory,
)


@pytest.mark.django_db
class TestTeamFactories:
    """Test team-related factories."""

    def test_team_factory_creates_valid_team(self):
        """Test TeamFactory creates a valid team."""
        team = TeamFactory()

        assert isinstance(team, Team)
        assert team.team_id is not None
        assert team.title.startswith("Fundraising Team")
        assert team.description is not None
        assert team.custom_remittance_rate is None
        assert team.team_coordinator is None
        assert team.created_by is None

    def test_team_with_coordinator_factory(self):
        """Test TeamWithCoordinatorFactory creates team with coordinator."""
        team = TeamWithCoordinatorFactory()

        assert isinstance(team, Team)
        assert team.team_coordinator is not None
        assert team.created_by is not None
        assert team.team_coordinator == team.created_by

    def test_team_with_custom_rate_factory(self):
        """Test TeamWithCustomRateFactory creates team with custom rate."""
        team = TeamWithCustomRateFactory()

        assert isinstance(team, Team)
        assert team.custom_remittance_rate == Decimal("95.00")
        assert team.title.startswith("Elite Fundraising Unit")


@pytest.mark.django_db
class TestTeamMemberFactories:
    """Test team member factories."""

    def test_team_member_factory_creates_valid_member(self):
        """Test TeamMemberFactory creates a valid team member."""
        member = TeamMemberFactory()

        assert isinstance(member, TeamMember)
        assert member.team_member_id is not None
        assert member.organization_member is not None
        assert member.team is not None
        assert member.role == TeamMemberRole.SUBMITTER

    def test_team_coordinator_factory(self):
        """Test TeamCoordinatorFactory creates coordinator."""
        coordinator = TeamCoordinatorFactory()

        assert isinstance(coordinator, TeamMember)
        assert coordinator.role == TeamMemberRole.TEAM_COORDINATOR

    def test_operations_reviewer_factory(self):
        """Test OperationsReviewerFactory creates reviewer."""
        reviewer = OperationsReviewerFactory()

        assert isinstance(reviewer, TeamMember)
        assert reviewer.role == TeamMemberRole.OPERATIONS_REVIEWER

    def test_workspace_admin_member_factory(self):
        """Test WorkspaceAdminMemberFactory creates workspace admin."""
        admin = WorkspaceAdminMemberFactory()

        assert isinstance(admin, TeamMember)
        assert admin.role == TeamMemberRole.WORKSPACE_ADMIN

    def test_auditor_member_factory(self):
        """Test AuditorMemberFactory creates auditor."""
        auditor = AuditorMemberFactory()

        assert isinstance(auditor, TeamMember)
        assert auditor.role == TeamMemberRole.AUDITOR

    def test_unique_constraint_respected(self):
        """Test that unique constraint is respected in factories."""
        team = TeamFactory()
        org_member = TeamMemberFactory().organization_member

        # First member should work
        member1 = TeamMemberFactory(team=team, organization_member=org_member)
        assert member1.team == team
        assert member1.organization_member == org_member

        # Second member with same team and org_member should fail
        with pytest.raises(Exception):
            TeamMemberFactory(team=team, organization_member=org_member)
