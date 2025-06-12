"""
Factory Boy factories for Workspace models.
"""

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from datetime import date, timedelta

from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.workspaces.constants import StatusChoices
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory


class WorkspaceFactory(DjangoModelFactory):
    """Factory for creating Workspace instances."""

    class Meta:
        model = Workspace

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Sequence(lambda n: f"Workspace {n}")
    description = factory.Faker("text", max_nb_chars=200)
    status = StatusChoices.ACTIVE
    remittance_rate = Decimal("90.00")
    start_date = factory.LazyFunction(lambda: date.today())
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=365))
    expense = Decimal("0.00")

    # workspace_admin and created_by will be set when needed


class WorkspaceWithAdminFactory(WorkspaceFactory):
    """Factory for creating Workspace with an admin."""

    class Meta:
        model = Workspace
        skip_postgeneration_save = True

    @factory.post_generation
    def admin(self, create, extracted, **kwargs):
        """Create an admin for the workspace."""
        if not create:
            return

        # Create organization member as admin
        admin = OrganizationMemberFactory(organization=self.organization)
        self.workspace_admin = admin
        self.created_by = admin
        self.save()


class ActiveWorkspaceFactory(WorkspaceFactory):
    """Factory for creating active workspaces."""

    title = factory.Sequence(lambda n: f"Active Workspace {n}")
    status = StatusChoices.ACTIVE


class ArchivedWorkspaceFactory(WorkspaceFactory):
    """Factory for creating archived workspaces."""

    title = factory.Sequence(lambda n: f"Archived Workspace {n}")
    status = StatusChoices.ARCHIVED


class ClosedWorkspaceFactory(WorkspaceFactory):
    """Factory for creating closed workspaces."""

    title = factory.Sequence(lambda n: f"Closed Workspace {n}")
    status = StatusChoices.CLOSED
    end_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))


class WorkspaceTeamFactory(DjangoModelFactory):
    """Factory for creating WorkspaceTeam instances."""

    class Meta:
        model = WorkspaceTeam

    workspace = factory.SubFactory(WorkspaceFactory)
    team = factory.SubFactory(TeamFactory)


class WorkspaceWithTeamsFactory(WorkspaceFactory):
    """Factory for creating workspace with multiple teams."""

    class Meta:
        model = Workspace
        skip_postgeneration_save = True

    @factory.post_generation
    def teams(self, create, extracted, **kwargs):
        """Create teams for the workspace."""
        if not create:
            return

        # Create default number of teams or use extracted
        team_count = extracted or 2

        for _ in range(team_count):
            team = TeamFactory()
            WorkspaceTeamFactory(workspace=self, team=team)


class CustomRateWorkspaceFactory(WorkspaceFactory):
    """Factory for creating workspace with custom remittance rate."""

    title = factory.Sequence(lambda n: f"Custom Rate Workspace {n}")
    remittance_rate = Decimal("85.00")
