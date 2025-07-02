"""
Factory Boy factories for Team models.
"""

import factory
from factory.django import DjangoModelFactory

from apps.teams.models import Team, TeamMember
from apps.teams.constants import TeamMemberRole
from tests.factories.organization_factories import (
    OrganizationMemberFactory,
    OrganizationFactory,
)


class TeamFactory(DjangoModelFactory):
    """Factory for creating fundraising Team instances."""

    class Meta:
        model = Team

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Sequence(lambda n: f"Fundraising Team {n}")
    description = factory.Faker("sentence", nb_words=6)
    # custom_remittance_rate = None  # Usually null, can override .. remove after deleting the column

    # created_by and team_coordinator will be set when needed


class TeamWithCoordinatorFactory(TeamFactory):
    """Factory for creating fundraising Team with a coordinator."""

    class Meta:
        model = Team
        skip_postgeneration_save = True

    @factory.post_generation
    def coordinator(self, create, extracted, **kwargs):
        """Create a coordinator for the fundraising team."""
        if not create:
            return

        # Create organization member as coordinator
        coordinator = OrganizationMemberFactory()
        self.team_coordinator = coordinator
        self.created_by = coordinator
        self.save()


class TeamMemberFactory(DjangoModelFactory):
    """Factory for creating TeamMember instances (field agents, coordinators, etc.)."""

    class Meta:
        model = TeamMember

    organization_member = factory.SubFactory(OrganizationMemberFactory)
    team = factory.SubFactory(TeamFactory)
    role = TeamMemberRole.SUBMITTER  # Default to field agent


class TeamCoordinatorFactory(TeamMemberFactory):
    """Factory for creating fundraising team coordinators."""

    role = TeamMemberRole.TEAM_COORDINATOR


class OperationsReviewerFactory(TeamMemberFactory):
    """Factory for creating financial operations reviewers."""

    role = TeamMemberRole.OPERATIONS_REVIEWER


class WorkspaceAdminMemberFactory(TeamMemberFactory):
    """Factory for creating campaign workspace admin team members."""

    role = TeamMemberRole.WORKSPACE_ADMIN


class AuditorMemberFactory(TeamMemberFactory):
    """Factory for creating financial auditor team members."""

    role = TeamMemberRole.AUDITOR


class TeamWithCustomRateFactory(TeamFactory):
    """Factory for creating fundraising team with custom remittance rate."""

    title = factory.Sequence(lambda n: f"Elite Fundraising Unit {n}")
    # custom_remittance_rate = Decimal("95.00")  # Higher remittance rate for elite teams Removed after deleting the column..
