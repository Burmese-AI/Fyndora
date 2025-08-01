"""
Unit tests for workspace selectors.

Tests the query functions in apps.workspaces.selectors module.
Focuses on database queries and data retrieval logic.
"""

from unittest.mock import patch

import pytest
from django.test import TestCase

from apps.currencies.models import Currency
from apps.teams.constants import TeamMemberRole
from apps.workspaces.selectors import (
    get_workspace_team_member_by_workspace_team_and_org_member,
    get_workspace_team_role_by_workspace_team_and_org_member,
    get_user_workspace_teams_under_organization,
    get_all_related_workspace_teams,
    get_user_workspaces_under_organization,
    get_organization_by_id,
    get_organization_members_by_organization_id,
    get_workspace_by_id,
    get_orgMember_by_user_id_and_organization_id,
    get_teams_by_organization_id,
    get_workspace_teams_by_workspace_id,
    get_team_by_id,
    get_workspaces_with_team_counts,
    get_single_workspace_with_team_counts,
    get_workspace_team_by_workspace_team_id,
    get_workspace_exchange_rates,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    OrganizationWithOwnerFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory
from tests.factories.user_factories import CustomUserFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceExchangeRateFactory,
)


@pytest.mark.unit
class TestWorkspaceTeamSelectors(TestCase):
    """Test workspace team related selectors."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.team = TeamFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )

    @pytest.mark.django_db
    def test_get_workspace_team_member_by_workspace_team_and_org_member(self):
        """Test getting workspace team member by workspace team and org member."""
        team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team,
            role=TeamMemberRole.SUBMITTER,
        )

        result = get_workspace_team_member_by_workspace_team_and_org_member(
            self.workspace_team, self.org_member
        )

        self.assertEqual(result, team_member)

    @pytest.mark.django_db
    def test_get_workspace_team_member_not_found(self):
        """Test getting workspace team member when member doesn't exist."""
        other_org_member = OrganizationMemberFactory(organization=self.organization)

        result = get_workspace_team_member_by_workspace_team_and_org_member(
            self.workspace_team, other_org_member
        )

        self.assertIsNone(result)

    @pytest.mark.django_db
    def test_get_workspace_team_role_by_workspace_team_and_org_member(self):
        """Test getting workspace team role by workspace team and org member."""
        TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )

        result = get_workspace_team_role_by_workspace_team_and_org_member(
            self.workspace_team, self.org_member
        )

        self.assertEqual(result, TeamMemberRole.AUDITOR)

    @pytest.mark.django_db
    def test_get_user_workspace_teams_under_organization(self):
        """Test getting user workspace teams under organization."""
        # Create team member
        TeamMemberFactory(organization_member=self.org_member, team=self.team)

        result = get_user_workspace_teams_under_organization(
            self.organization.organization_id, self.user
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.workspace_team)

    @pytest.mark.django_db
    def test_get_user_workspace_teams_as_coordinator(self):
        """Test getting workspace teams where user is team coordinator."""
        # Set user as team coordinator
        self.team.team_coordinator = self.org_member
        self.team.save()

        result = get_user_workspace_teams_under_organization(
            self.organization.organization_id, self.user
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.workspace_team)

    @pytest.mark.django_db
    def test_get_all_related_workspace_teams_as_owner(self):
        """Test getting all related workspace teams as organization owner."""
        org_with_owner = OrganizationWithOwnerFactory()
        workspace = WorkspaceFactory(organization=org_with_owner)
        team = TeamFactory(organization=org_with_owner)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)

        result = get_all_related_workspace_teams(
            org_with_owner, org_with_owner.owner.user, group_by_workspace=False
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), workspace_team)

    @pytest.mark.django_db
    def test_get_all_related_workspace_teams_grouped(self):
        """Test getting all related workspace teams grouped by workspace."""
        org_with_owner = OrganizationWithOwnerFactory()
        workspace = WorkspaceFactory(organization=org_with_owner)
        team1 = TeamFactory(organization=org_with_owner)
        team2 = TeamFactory(organization=org_with_owner)
        workspace_team1 = WorkspaceTeamFactory(workspace=workspace, team=team1)
        workspace_team2 = WorkspaceTeamFactory(workspace=workspace, team=team2)

        result = get_all_related_workspace_teams(
            org_with_owner, org_with_owner.owner.user, group_by_workspace=True
        )

        self.assertIsInstance(result, dict)
        self.assertIn(workspace, result)
        self.assertEqual(len(result[workspace]), 2)
        self.assertIn(workspace_team1, result[workspace])
        self.assertIn(workspace_team2, result[workspace])

    @pytest.mark.django_db
    def test_get_all_related_workspace_teams_as_non_owner(self):
        """Test getting related workspace teams as non-owner."""
        # Create workspace admin
        workspace_admin = OrganizationMemberFactory(organization=self.organization)
        workspace = WorkspaceFactory(
            organization=self.organization, workspace_admin=workspace_admin
        )
        team = TeamFactory(organization=self.organization)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)

        result = get_all_related_workspace_teams(
            self.organization, workspace_admin.user, group_by_workspace=False
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), workspace_team)


@pytest.mark.unit
class TestBasicSelectors(TestCase):
    """Test basic selector functions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

    @pytest.mark.django_db
    def test_get_user_workspaces_under_organization(self):
        """Test getting user workspaces under organization."""
        workspace1 = WorkspaceFactory(organization=self.organization)
        workspace2 = WorkspaceFactory(organization=self.organization)
        # Different organization
        other_org = OrganizationFactory()
        WorkspaceFactory(organization=other_org)

        result = get_user_workspaces_under_organization(
            self.organization.organization_id
        )

        self.assertEqual(result.count(), 3)  # Including self.workspace
        workspace_ids = [w.workspace_id for w in result]
        self.assertIn(workspace1.workspace_id, workspace_ids)
        self.assertIn(workspace2.workspace_id, workspace_ids)

    @pytest.mark.django_db
    def test_get_user_workspaces_under_organization_error(self):
        """Test getting workspaces with invalid organization ID."""
        with patch("builtins.print") as mock_print:
            result = get_user_workspaces_under_organization("invalid-id")

            self.assertEqual(result.count(), 0)
            mock_print.assert_called()

    @pytest.mark.django_db
    def test_get_organization_by_id(self):
        """Test getting organization by ID."""
        result = get_organization_by_id(self.organization.organization_id)
        self.assertEqual(result, self.organization)

    @pytest.mark.django_db
    def test_get_organization_by_id_not_found(self):
        """Test getting organization by invalid ID."""
        with patch("builtins.print") as mock_print:
            result = get_organization_by_id("invalid-id")

            self.assertIsNone(result)
            mock_print.assert_called()

    @pytest.mark.django_db
    def test_get_organization_members_by_organization_id(self):
        """Test getting organization members by organization ID."""
        member1 = OrganizationMemberFactory(organization=self.organization)
        member2 = OrganizationMemberFactory(organization=self.organization)

        result = get_organization_members_by_organization_id(
            self.organization.organization_id
        )

        self.assertEqual(result.count(), 2)
        member_ids = [m.organization_member_id for m in result]
        self.assertIn(member1.organization_member_id, member_ids)
        self.assertIn(member2.organization_member_id, member_ids)

    @pytest.mark.django_db
    def test_get_workspace_by_id(self):
        """Test getting workspace by ID."""
        result = get_workspace_by_id(self.workspace.workspace_id)
        self.assertEqual(result, self.workspace)

    @pytest.mark.django_db
    def test_get_workspace_by_id_not_found(self):
        """Test getting workspace by invalid ID."""
        with patch("builtins.print") as mock_print:
            result = get_workspace_by_id("invalid-id")

            self.assertIsNone(result)
            mock_print.assert_called()

    @pytest.mark.django_db
    def test_get_orgMember_by_user_id_and_organization_id(self):
        """Test getting organization member by user ID and organization ID."""
        user = CustomUserFactory()
        org_member = OrganizationMemberFactory(
            organization=self.organization, user=user
        )

        result = get_orgMember_by_user_id_and_organization_id(
            user.user_id, self.organization.organization_id
        )

        self.assertEqual(result, org_member)

    @pytest.mark.django_db
    def test_get_teams_by_organization_id(self):
        """Test getting teams by organization ID."""
        team1 = TeamFactory(organization=self.organization)
        team2 = TeamFactory(organization=self.organization)

        result = get_teams_by_organization_id(self.organization.organization_id)

        self.assertEqual(result.count(), 3)  # Including self.team
        team_ids = [t.team_id for t in result]
        self.assertIn(team1.team_id, team_ids)
        self.assertIn(team2.team_id, team_ids)

    @pytest.mark.django_db
    def test_get_workspace_teams_by_workspace_id(self):
        """Test getting workspace teams by workspace ID."""
        team1 = TeamFactory(organization=self.organization)
        team2 = TeamFactory(organization=self.organization)
        workspace_team1 = WorkspaceTeamFactory(workspace=self.workspace, team=team1)
        workspace_team2 = WorkspaceTeamFactory(workspace=self.workspace, team=team2)

        result = get_workspace_teams_by_workspace_id(self.workspace.workspace_id)

        self.assertEqual(result.count(), 2)
        workspace_team_ids = [wt.workspace_team_id for wt in result]
        self.assertIn(workspace_team1.workspace_team_id, workspace_team_ids)
        self.assertIn(workspace_team2.workspace_team_id, workspace_team_ids)

    @pytest.mark.django_db
    def test_get_team_by_id(self):
        """Test getting team by ID."""
        result = get_team_by_id(self.team.team_id)
        self.assertEqual(result, self.team)

    @pytest.mark.django_db
    def test_get_workspace_team_by_workspace_team_id(self):
        """Test getting workspace team by ID."""
        workspace_team = WorkspaceTeamFactory(workspace=self.workspace, team=self.team)

        result = get_workspace_team_by_workspace_team_id(
            workspace_team.workspace_team_id
        )

        self.assertEqual(result, workspace_team)


@pytest.mark.unit
class TestAggregateSelectors(TestCase):
    """Test selectors that perform aggregations or complex queries."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()

    @pytest.mark.django_db
    def test_get_workspaces_with_team_counts(self):
        """Test getting workspaces with team counts."""
        workspace1 = WorkspaceFactory(organization=self.organization)
        workspace2 = WorkspaceFactory(organization=self.organization)

        # Add teams to workspace1
        team1 = TeamFactory(organization=self.organization)
        team2 = TeamFactory(organization=self.organization)
        WorkspaceTeamFactory(workspace=workspace1, team=team1)
        WorkspaceTeamFactory(workspace=workspace1, team=team2)

        # Add one team to workspace2
        team3 = TeamFactory(organization=self.organization)
        WorkspaceTeamFactory(workspace=workspace2, team=team3)

        result = get_workspaces_with_team_counts(self.organization.organization_id)

        # Find our workspaces in the result
        workspace1_result = next(
            w for w in result if w.workspace_id == workspace1.workspace_id
        )
        workspace2_result = next(
            w for w in result if w.workspace_id == workspace2.workspace_id
        )

        self.assertEqual(workspace1_result.teams_count, 2)
        self.assertEqual(workspace2_result.teams_count, 1)

    @pytest.mark.django_db
    def test_get_single_workspace_with_team_counts(self):
        """Test getting single workspace with team count."""
        workspace = WorkspaceFactory(organization=self.organization)

        # Add teams
        team1 = TeamFactory(organization=self.organization)
        team2 = TeamFactory(organization=self.organization)
        team3 = TeamFactory(organization=self.organization)
        WorkspaceTeamFactory(workspace=workspace, team=team1)
        WorkspaceTeamFactory(workspace=workspace, team=team2)
        WorkspaceTeamFactory(workspace=workspace, team=team3)

        result = get_single_workspace_with_team_counts(workspace.workspace_id)

        self.assertEqual(result.workspace_id, workspace.workspace_id)
        self.assertEqual(result.teams_count, 3)

    @pytest.mark.django_db
    def test_get_workspace_exchange_rates(self):
        """Test getting workspace exchange rates."""
        workspace = WorkspaceFactory(organization=self.organization)

        # Create currencies to avoid unique constraint violation
        currency1 = Currency.objects.create(code="EUR", name="Euro")
        currency2 = Currency.objects.create(code="GBP", name="British Pound")

        # Create exchange rates with different currencies
        rate1 = WorkspaceExchangeRateFactory(workspace=workspace, currency=currency1)
        rate2 = WorkspaceExchangeRateFactory(workspace=workspace, currency=currency2)

        # Different workspace
        other_workspace = WorkspaceFactory(organization=self.organization)
        WorkspaceExchangeRateFactory(workspace=other_workspace)

        result = get_workspace_exchange_rates(
            organization=self.organization, workspace=workspace
        )

        self.assertEqual(result.count(), 2)
        rate_ids = [r.workspace_exchange_rate_id for r in result]
        self.assertIn(rate1.workspace_exchange_rate_id, rate_ids)
        self.assertIn(rate2.workspace_exchange_rate_id, rate_ids)

    @pytest.mark.django_db
    def test_get_workspace_exchange_rates_error(self):
        """Test getting workspace exchange rates with None parameters."""
        result = get_workspace_exchange_rates(organization=None, workspace=None)

        # Should return empty queryset, not None, since Django handles None gracefully
        self.assertEqual(result.count(), 0)
