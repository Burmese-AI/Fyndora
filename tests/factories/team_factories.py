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
    team_coordinator = factory.SubFactory(OrganizationMemberFactory)
    created_by = factory.SubFactory(OrganizationMemberFactory)


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


class AuditorMemberFactory(TeamMemberFactory):
    """Factory for creating financial auditor team members."""

    role = TeamMemberRole.AUDITOR
