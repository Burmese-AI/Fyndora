"""Unit tests for organization utils.

Tests utility functions with various scenarios and edge cases.
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.organizations.utils import (
    remove_permissions_from_member,
    extract_organization_context,
    extract_organization_member_context,
    extract_organization_exchange_rate_context,
)
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    WorkspaceFactory,
    TeamFactory,
    TeamMemberFactory,
    OrganizationExchangeRateFactory,
    CurrencyFactory,
)


class TestRemovePermissionsFromMember(TestCase):
    """Test remove_permissions_from_member utility function."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.member = OrganizationMemberFactory(organization=self.organization)

    @patch('apps.organizations.utils.revoke_workspace_admin_permission')
    @patch('apps.organizations.utils.revoke_operations_reviewer_permission')
    @patch('apps.organizations.utils.revoke_team_coordinator_permission')
    @patch('apps.organizations.utils.revoke_workspace_team_member_permission')
    def test_remove_permissions_from_member_with_workspace_admin_role(self, mock_revoke_team_member, mock_revoke_coordinator, mock_revoke_reviewer, mock_revoke_admin):
        """Test removing permissions when member is workspace admin."""
        # Create workspace where member is admin
        workspace = WorkspaceFactory(organization=self.organization)
        workspace.workspace_admin = self.member
        workspace.save()
        
        # The function will use real relationships, so we don't need to mock them
        
        remove_permissions_from_member(self.member, self.organization)
        
        # Verify workspace admin permission was revoked
        mock_revoke_admin.assert_called_once_with(self.member.user, workspace)
        
        # Verify workspace admin was cleared
        workspace.refresh_from_db()
        self.assertIsNone(workspace.workspace_admin)

    @patch('apps.organizations.utils.revoke_workspace_admin_permission')
    @patch('apps.organizations.utils.revoke_operations_reviewer_permission')
    @patch('apps.organizations.utils.revoke_team_coordinator_permission')
    @patch('apps.organizations.utils.revoke_workspace_team_member_permission')
    def test_remove_permissions_from_member_with_operations_reviewer_role(self, mock_revoke_team_member, mock_revoke_coordinator, mock_revoke_reviewer, mock_revoke_admin):
        """Test removing permissions when member is operations reviewer."""
        # Create workspace where member is operations reviewer
        workspace = WorkspaceFactory(organization=self.organization)
        workspace.operations_reviewer = self.member
        workspace.save()
        
        remove_permissions_from_member(self.member, self.organization)
        
        # Verify operations reviewer permission was revoked
        mock_revoke_reviewer.assert_called_once_with(self.member.user, workspace)
        
        # Verify operations reviewer was cleared
        workspace.refresh_from_db()
        self.assertIsNone(workspace.operations_reviewer)

    @patch('apps.organizations.utils.revoke_workspace_admin_permission')
    @patch('apps.organizations.utils.revoke_operations_reviewer_permission')
    @patch('apps.organizations.utils.revoke_team_coordinator_permission')
    @patch('apps.organizations.utils.revoke_workspace_team_member_permission')
    def test_remove_permissions_from_member_with_team_coordinator_role(self, mock_revoke_team_member, mock_revoke_coordinator, mock_revoke_reviewer, mock_revoke_admin):
        """Test removing permissions when member is team coordinator."""
        # Create team where member is coordinator
        team = TeamFactory(organization=self.organization)
        team.team_coordinator = self.member
        team.save()
        
        remove_permissions_from_member(self.member, self.organization)
        
        # Verify team coordinator permission was revoked
        mock_revoke_coordinator.assert_called_once_with(self.member.user, team)
        
        # Verify team coordinator was cleared
        team.refresh_from_db()
        self.assertIsNone(team.team_coordinator)

    @patch('apps.organizations.utils.revoke_workspace_admin_permission')
    @patch('apps.organizations.utils.revoke_operations_reviewer_permission')
    @patch('apps.organizations.utils.revoke_team_coordinator_permission')
    @patch('apps.organizations.utils.revoke_workspace_team_member_permission')
    def test_remove_permissions_from_member_with_team_memberships(self, mock_revoke_team_member, mock_revoke_coordinator, mock_revoke_reviewer, mock_revoke_admin):
        """Test removing permissions when member has team memberships."""
        # Create team and team membership
        team = TeamFactory(organization=self.organization)
        team_membership = TeamMemberFactory(team=team, organization_member=self.member)
        
        # Create workspace and workspace team
        workspace = WorkspaceFactory(organization=self.organization)
        
        # Import and create WorkspaceTeam
        from apps.workspaces.models import WorkspaceTeam
        workspace_team = WorkspaceTeam.objects.create(
            workspace=workspace,
            team=team
        )
        
        remove_permissions_from_member(self.member, self.organization)
        
        # Verify workspace team member permission was revoked
        mock_revoke_team_member.assert_called_once_with(self.member.user, workspace_team)
        
        # Verify team membership was deleted
        self.assertFalse(TeamMemberFactory._meta.model.objects.filter(pk=team_membership.pk).exists())

    @patch('apps.organizations.utils.revoke_workspace_admin_permission')
    @patch('apps.organizations.utils.revoke_operations_reviewer_permission')
    @patch('apps.organizations.utils.revoke_team_coordinator_permission')
    @patch('apps.organizations.utils.revoke_workspace_team_member_permission')
    def test_remove_permissions_from_member_with_multiple_roles(self, mock_revoke_team_member, mock_revoke_coordinator, mock_revoke_reviewer, mock_revoke_admin):
        """Test removing permissions when member has multiple roles."""
        # Create workspace where member is admin
        workspace1 = WorkspaceFactory(organization=self.organization)
        workspace1.workspace_admin = self.member
        workspace1.save()
        
        # Create workspace where member is operations reviewer
        workspace2 = WorkspaceFactory(organization=self.organization)
        workspace2.operations_reviewer = self.member
        workspace2.save()
        
        # Create team where member is coordinator
        team = TeamFactory(organization=self.organization)
        team.team_coordinator = self.member
        team.save()
        
        remove_permissions_from_member(self.member, self.organization)
        
        # Verify all permissions were revoked
        mock_revoke_admin.assert_called_once_with(self.member.user, workspace1)
        mock_revoke_reviewer.assert_called_once_with(self.member.user, workspace2)
        mock_revoke_coordinator.assert_called_once_with(self.member.user, team)
        
        # Verify all roles were cleared
        workspace1.refresh_from_db()
        workspace2.refresh_from_db()
        team.refresh_from_db()
        self.assertIsNone(workspace1.workspace_admin)
        self.assertIsNone(workspace2.operations_reviewer)
        self.assertIsNone(team.team_coordinator)

    @patch('apps.organizations.utils.revoke_workspace_admin_permission')
    @patch('apps.organizations.utils.revoke_operations_reviewer_permission')
    @patch('apps.organizations.utils.revoke_team_coordinator_permission')
    @patch('apps.organizations.utils.revoke_workspace_team_member_permission')
    def test_remove_permissions_from_member_with_no_roles(self, mock_revoke_team_member, mock_revoke_coordinator, mock_revoke_reviewer, mock_revoke_admin):
        """Test removing permissions when member has no roles."""
        # Member has no roles by default, so no permissions should be revoked
        
        remove_permissions_from_member(self.member, self.organization)
        
        # Verify no permissions were revoked
        mock_revoke_admin.assert_not_called()
        mock_revoke_reviewer.assert_not_called()
        mock_revoke_coordinator.assert_not_called()
        mock_revoke_team_member.assert_not_called()


class TestExtractOrganizationContext(TestCase):
    """Test extract_organization_context utility function."""

    def test_extract_organization_context_with_organization(self):
        """Test extracting context from organization with owner."""
        organization = OrganizationFactory()
        owner_member = OrganizationMemberFactory(organization=organization)
        organization.owner = owner_member
        organization.save()
        
        context = extract_organization_context(organization)
        
        self.assertEqual(context['organization_id'], str(organization.pk))
        self.assertEqual(context['organization_title'], organization.title)
        self.assertEqual(context['organization_status'], organization.status)
        self.assertEqual(context['owner_id'], str(owner_member.user.pk))
        self.assertEqual(context['owner_email'], owner_member.user.email)

    def test_extract_organization_context_without_owner(self):
        """Test extracting context from organization without owner."""
        organization = OrganizationFactory()
        organization.owner = None
        organization.save()
        
        context = extract_organization_context(organization)
        
        self.assertEqual(context['organization_id'], str(organization.pk))
        self.assertEqual(context['organization_title'], organization.title)
        self.assertIsNone(context['owner_id'])
        self.assertIsNone(context['owner_email'])

    def test_extract_organization_context_none(self):
        """Test extracting context from None organization."""
        context = extract_organization_context(None)
        
        self.assertEqual(context, {})


class TestExtractOrganizationMemberContext(TestCase):
    """Test extract_organization_member_context utility function."""

    def test_extract_organization_member_context_with_member(self):
        """Test extracting context from organization member."""
        member = OrganizationMemberFactory()
        
        context = extract_organization_member_context(member)
        
        self.assertEqual(context['member_id'], str(member.pk))
        self.assertEqual(context['organization_id'], str(member.organization.pk))
        self.assertEqual(context['organization_title'], member.organization.title)
        self.assertEqual(context['user_id'], str(member.user.pk))
        self.assertEqual(context['user_email'], member.user.email)
        self.assertEqual(context['member_status'], 'active')
        self.assertTrue(context['is_active'])
        self.assertEqual(context['role'], 'member')

    def test_extract_organization_member_context_none(self):
        """Test extracting context from None member."""
        context = extract_organization_member_context(None)
        
        self.assertEqual(context, {})


class TestExtractOrganizationExchangeRateContext(TestCase):
    """Test extract_organization_exchange_rate_context utility function."""

    def test_extract_organization_exchange_rate_context_with_rate(self):
        """Test extracting context from organization exchange rate."""
        exchange_rate = OrganizationExchangeRateFactory()
        
        context = extract_organization_exchange_rate_context(exchange_rate)
        
        self.assertEqual(context['exchange_rate_id'], str(exchange_rate.pk))
        self.assertEqual(context['organization_id'], str(exchange_rate.organization.pk))
        self.assertEqual(context['organization_title'], exchange_rate.organization.title)
        self.assertEqual(context['currency_code'], exchange_rate.currency.code)
        self.assertEqual(context['rate'], str(exchange_rate.rate))
        self.assertEqual(context['note'], exchange_rate.note)

    def test_extract_organization_exchange_rate_context_none(self):
        """Test extracting context from None exchange rate."""
        context = extract_organization_exchange_rate_context(None)
        
        self.assertEqual(context, {})
