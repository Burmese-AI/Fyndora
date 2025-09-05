"""
Unit tests for the seed_data management command.
"""

from unittest.mock import patch, MagicMock, call
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import sys

from apps.core.management.commands.seed_data import Command
from apps.accounts.models import CustomUser
from apps.organizations.models import Organization, OrganizationMember, OrganizationExchangeRate
from apps.workspaces.models import Workspace, WorkspaceTeam, WorkspaceExchangeRate
from apps.teams.models import Team, TeamMember
from apps.entries.models import Entry
from apps.currencies.models import Currency
from apps.entries.constants import EntryType, EntryStatus
from apps.teams.constants import TeamMemberRole
from apps.accounts.constants import StatusChoices as UserStatusChoices
from apps.organizations.constants import StatusChoices as OrgStatusChoices
from apps.workspaces.constants import StatusChoices as WorkspaceStatusChoices


class SeedDataCommandTest(TestCase):
    """Test cases for the seed_data management command."""

    def setUp(self):
        """Set up test data."""
        self.command = Command()
        self.out = StringIO()
        self.command.stdout = self.out

    def test_add_arguments(self):
        """Test that command arguments are properly defined."""
        from django.core.management import CommandParser
        parser = CommandParser()
        self.command.add_arguments(parser)
        
        # Test that all expected arguments exist
        args = [action.dest for action in parser._actions]
        expected_args = [
            'organizations', 'workspaces_per_org', 'teams_per_org', 
            'users_per_org', 'entries_per_workspace', 'clear_existing'
        ]
        for arg in expected_args:
            self.assertIn(arg, args)

    @patch('apps.core.management.commands.seed_data.Command.create_currencies')
    @patch('apps.core.management.commands.seed_data.Command.create_organizations')
    @patch('apps.core.management.commands.seed_data.Command.create_teams')
    @patch('apps.core.management.commands.seed_data.Command.create_workspaces')
    @patch('apps.core.management.commands.seed_data.Command.create_workspace_teams')
    @patch('apps.core.management.commands.seed_data.Command.create_exchange_rates')
    @patch('apps.core.management.commands.seed_data.Command.create_entries')
    @patch('apps.core.management.commands.seed_data.Command.resolve_role_conflicts')
    @patch('apps.core.management.commands.seed_data.Entry.objects.count')
    @patch('apps.core.management.commands.seed_data.Currency.objects.count')
    def test_handle_success(
        self, mock_currency_count, mock_entry_count, mock_resolve_conflicts,
        mock_create_entries, mock_create_exchange_rates, mock_create_workspace_teams,
        mock_create_workspaces, mock_create_teams, mock_create_organizations,
        mock_create_currencies
    ):
        """Test successful command execution."""
        # Mock return values
        mock_organizations = [MagicMock()]
        mock_teams = [MagicMock()]
        mock_workspaces = [MagicMock()]
        mock_workspace_teams = [MagicMock()]
        
        mock_create_organizations.return_value = mock_organizations
        mock_create_teams.return_value = mock_teams
        mock_create_workspaces.return_value = mock_workspaces
        mock_create_workspace_teams.return_value = mock_workspace_teams
        mock_entry_count.return_value = 100
        mock_currency_count.return_value = 8

        # Test command execution
        options = {
            'organizations': 1,
            'workspaces_per_org': 1,
            'teams_per_org': 1,
            'users_per_org': 5,
            'entries_per_workspace': 10,
            'clear_existing': False
        }
        
        self.command.handle(**options)

        # Verify all methods were called
        mock_create_currencies.assert_called_once()
        mock_create_organizations.assert_called_once_with(count=1, users_per_org=5)
        mock_create_teams.assert_called_once_with(organizations=mock_organizations, teams_per_org=1)
        mock_create_workspaces.assert_called_once_with(organizations=mock_organizations, workspaces_per_org=1)
        mock_create_workspace_teams.assert_called_once_with(workspaces=mock_workspaces, teams=mock_teams)
        mock_create_exchange_rates.assert_called_once_with(mock_organizations, mock_workspaces)
        mock_create_entries.assert_called_once_with(workspaces=mock_workspaces, workspace_teams=mock_workspace_teams, entries_per_workspace=10)
        mock_resolve_conflicts.assert_called_once_with(mock_organizations, mock_workspaces, mock_teams)

    @patch('builtins.input', return_value='no')
    @patch('apps.core.management.commands.seed_data.Command.clear_existing_data')
    def test_handle_clear_existing_cancelled(self, mock_clear_data, mock_input):
        """Test command when clear_existing is cancelled by user."""
        options = {
            'organizations': 1,
            'workspaces_per_org': 1,
            'teams_per_org': 1,
            'users_per_org': 5,
            'entries_per_workspace': 10,
            'clear_existing': True
        }
        
        self.command.handle(**options)
        
        # Should not call clear_existing_data
        mock_clear_data.assert_not_called()
        
        # Should show cancellation message
        output = self.out.getvalue()
        self.assertIn("Database clearing cancelled by user", output)

    @patch('builtins.input', return_value='yes')
    @patch('apps.core.management.commands.seed_data.Command.clear_existing_data')
    @patch('apps.core.management.commands.seed_data.Command.create_currencies')
    @patch('apps.core.management.commands.seed_data.Command.create_organizations')
    @patch('apps.core.management.commands.seed_data.Command.create_teams')
    @patch('apps.core.management.commands.seed_data.Command.create_workspaces')
    @patch('apps.core.management.commands.seed_data.Command.create_workspace_teams')
    @patch('apps.core.management.commands.seed_data.Command.create_exchange_rates')
    @patch('apps.core.management.commands.seed_data.Command.create_entries')
    @patch('apps.core.management.commands.seed_data.Command.resolve_role_conflicts')
    @patch('apps.core.management.commands.seed_data.Entry.objects.count')
    @patch('apps.core.management.commands.seed_data.Currency.objects.count')
    def test_handle_clear_existing_confirmed(
        self, mock_currency_count, mock_entry_count, mock_resolve_conflicts,
        mock_create_entries, mock_create_exchange_rates, mock_create_workspace_teams,
        mock_create_workspaces, mock_create_teams, mock_create_organizations,
        mock_create_currencies, mock_clear_data, mock_input
    ):
        """Test command when clear_existing is confirmed by user."""
        # Mock return values
        mock_organizations = [MagicMock()]
        mock_teams = [MagicMock()]
        mock_workspaces = [MagicMock()]
        mock_workspace_teams = [MagicMock()]
        
        mock_create_organizations.return_value = mock_organizations
        mock_create_teams.return_value = mock_teams
        mock_create_workspaces.return_value = mock_workspaces
        mock_create_workspace_teams.return_value = mock_workspace_teams
        mock_entry_count.return_value = 100
        mock_currency_count.return_value = 8

        options = {
            'organizations': 1,
            'workspaces_per_org': 1,
            'teams_per_org': 1,
            'users_per_org': 5,
            'entries_per_workspace': 10,
            'clear_existing': True
        }
        
        self.command.handle(**options)
        
        # Should call clear_existing_data
        mock_clear_data.assert_called_once()

    @patch('apps.core.management.commands.seed_data.Command.create_currencies')
    def test_handle_exception(self, mock_create_currencies):
        """Test command when an exception occurs."""
        mock_create_currencies.side_effect = Exception("Test error")
        
        options = {
            'organizations': 1,
            'workspaces_per_org': 1,
            'teams_per_org': 1,
            'users_per_org': 5,
            'entries_per_workspace': 10,
            'clear_existing': False
        }
        
        with self.assertRaises(Exception):
            self.command.handle(**options)
        
        output = self.out.getvalue()
        self.assertIn("Error seeding data: Test error", output)

    @patch('apps.core.management.commands.seed_data.Currency.objects.get_or_create')
    def test_create_currencies_success(self, mock_get_or_create):
        """Test successful currency creation."""
        mock_get_or_create.return_value = (MagicMock(), True)
        
        self.command.create_currencies()
        
        # Should create 8 currencies
        assert mock_get_or_create.call_count == 8
        
        output = self.out.getvalue()
        self.assertIn("Created 8 currencies", output)

    @patch('apps.core.management.commands.seed_data.Currency.objects.get_or_create')
    def test_create_currencies_exception(self, mock_get_or_create):
        """Test currency creation with exception."""
        mock_get_or_create.side_effect = Exception("Currency error")
        
        self.command.create_currencies()
        
        output = self.out.getvalue()
        self.assertIn("Warning: Could not create currencies: Currency error", output)

    @patch('apps.core.management.commands.seed_data.CustomUser.objects.create_user')
    @patch('apps.core.management.commands.seed_data.Organization.objects.create')
    @patch('apps.core.management.commands.seed_data.OrganizationMember.objects.create')
    @patch('apps.core.management.commands.seed_data.Group.objects.get_or_create')
    @patch('apps.core.management.commands.seed_data.get_permissions_for_role')
    @patch('apps.core.management.commands.seed_data.assign_perm')
    def test_create_organizations_success(
        self, mock_assign_perm, mock_get_permissions, mock_group_create,
        mock_org_member_create, mock_org_create, mock_user_create
    ):
        """Test successful organization creation."""
        # Mock objects
        mock_user = MagicMock()
        mock_org = MagicMock()
        mock_org_member = MagicMock()
        mock_group = MagicMock()
        
        mock_user_create.return_value = mock_user
        mock_org_create.return_value = mock_org
        mock_org_member_create.return_value = mock_org_member
        mock_group_create.return_value = (mock_group, True)
        mock_get_permissions.return_value = ['perm1', 'perm2']
        
        organizations = self.command.create_organizations(count=1, users_per_org=3)
        
        # Should create 1 organization
        self.assertEqual(len(organizations), 1)
        
        # Should create users (1 owner + 2 members)
        assert mock_user_create.call_count == 3
        
        # Should create organization
        mock_org_create.assert_called_once()
        
        # Should create organization members
        assert mock_org_member_create.call_count == 3

    @patch('apps.core.management.commands.seed_data.CustomUser.objects.create_user')
    def test_create_organizations_exception(self, mock_user_create):
        """Test organization creation with exception."""
        mock_user_create.side_effect = Exception("User creation error")
        
        with self.assertRaises(Exception):
            self.command.create_organizations(count=1, users_per_org=3)
        
        output = self.out.getvalue()
        self.assertIn("Error creating organizations: User creation error", output)

    @patch('apps.core.management.commands.seed_data.Team.objects.create')
    @patch('apps.core.management.commands.seed_data.TeamMember.objects.create')
    @patch('apps.core.management.commands.seed_data.assign_team_permissions')
    @patch('apps.core.management.commands.seed_data.Team.objects.filter')
    def test_create_teams_success(
        self, mock_team_filter, mock_assign_permissions, mock_team_member_create, mock_team_create
    ):
        """Test successful team creation."""
        # Mock organization with members
        mock_org = MagicMock()
        mock_owner = MagicMock()
        mock_member1 = MagicMock()
        mock_member2 = MagicMock()
        mock_org.owner = mock_owner
        mock_org.members.all.return_value = [mock_owner, mock_member1, mock_member2]
        
        # Mock team filter to return no existing teams (for uniqueness check)
        mock_team_filter.return_value.exists.return_value = False
        
        mock_team = MagicMock()
        mock_team_create.return_value = mock_team
        
        organizations = [mock_org]
        teams = self.command.create_teams(organizations=organizations, teams_per_org=1)
        
        # Should create 1 team
        self.assertEqual(len(teams), 1)
        
        # Should create team
        mock_team_create.assert_called_once()
        
        # Should create team members
        mock_team_member_create.assert_called()
        
        # Should assign permissions
        mock_assign_permissions.assert_called_once()

    @patch('apps.core.management.commands.seed_data.Team.objects.create')
    @patch('apps.core.management.commands.seed_data.Team.objects.filter')
    def test_create_teams_exception(self, mock_team_filter, mock_team_create):
        """Test team creation with exception."""
        mock_team_filter.return_value.exists.return_value = False
        mock_team_create.side_effect = Exception("Team creation error")
        
        mock_org = MagicMock()
        mock_owner = MagicMock()
        mock_org.owner = mock_owner
        mock_org.members.all.return_value = [mock_owner]
        organizations = [mock_org]
        
        with self.assertRaises(Exception):
            self.command.create_teams(organizations=organizations, teams_per_org=1)
        
        output = self.out.getvalue()
        self.assertIn("Error creating teams: Team creation error", output)

    @patch('apps.core.management.commands.seed_data.Workspace.objects.create')
    @patch('apps.core.management.commands.seed_data.assign_workspace_permissions')
    @patch('apps.core.management.commands.seed_data.Workspace.objects.filter')
    def test_create_workspaces_success(
        self, mock_workspace_filter, mock_assign_permissions, mock_workspace_create
    ):
        """Test successful workspace creation."""
        # Mock organization with members
        mock_org = MagicMock()
        mock_owner = MagicMock()
        mock_member1 = MagicMock()
        mock_member2 = MagicMock()
        mock_org.owner = mock_owner
        mock_org.members.all.return_value = [mock_owner, mock_member1, mock_member2]
        
        # Mock workspace filter to return no existing workspaces (for uniqueness check)
        mock_workspace_filter.return_value.exists.return_value = False
        
        mock_workspace = MagicMock()
        mock_workspace_create.return_value = mock_workspace
        
        organizations = [mock_org]
        workspaces = self.command.create_workspaces(organizations=organizations, workspaces_per_org=1)
        
        # Should create 1 workspace
        self.assertEqual(len(workspaces), 1)
        
        # Should create workspace
        mock_workspace_create.assert_called_once()
        
        # Should assign permissions
        mock_assign_permissions.assert_called_once()

    @patch('apps.core.management.commands.seed_data.Workspace.objects.create')
    @patch('apps.core.management.commands.seed_data.Workspace.objects.filter')
    def test_create_workspaces_exception(self, mock_workspace_filter, mock_workspace_create):
        """Test workspace creation with exception."""
        mock_workspace_filter.return_value.exists.return_value = False
        mock_workspace_create.side_effect = Exception("Workspace creation error")
        
        mock_org = MagicMock()
        mock_owner = MagicMock()
        mock_member1 = MagicMock()
        mock_member2 = MagicMock()
        mock_org.owner = mock_owner
        mock_org.members.all.return_value = [mock_owner, mock_member1, mock_member2]
        organizations = [mock_org]
        
        with self.assertRaises(Exception):
            self.command.create_workspaces(organizations=organizations, workspaces_per_org=1)
        
        output = self.out.getvalue()
        self.assertIn("Error creating workspaces: Workspace creation error", output)

    @patch('apps.core.management.commands.seed_data.WorkspaceTeam.objects.create')
    @patch('apps.core.management.commands.seed_data.assign_workspace_team_permissions')
    def test_create_workspace_teams_success(
        self, mock_assign_permissions, mock_workspace_team_create
    ):
        """Test successful workspace team creation."""
        # Mock workspace and team
        mock_workspace = MagicMock()
        mock_team = MagicMock()
        mock_workspace.organization = MagicMock()
        mock_workspace.organization.owner = MagicMock()
        mock_workspace.organization.owner.user = MagicMock()
        
        # Mock team organization to match workspace organization
        mock_team.organization = mock_workspace.organization
        
        mock_workspace_team = MagicMock()
        mock_workspace_team_create.return_value = mock_workspace_team
        
        workspaces = [mock_workspace]
        teams = [mock_team]
        workspace_teams = self.command.create_workspace_teams(workspaces=workspaces, teams=teams)
        
        # Should create workspace teams
        self.assertGreater(len(workspace_teams), 0)
        
        # Should create workspace team
        mock_workspace_team_create.assert_called()
        
        # Should assign permissions
        mock_assign_permissions.assert_called()

    @patch('apps.core.management.commands.seed_data.WorkspaceTeam.objects.create')
    def test_create_workspace_teams_exception(self, mock_workspace_team_create):
        """Test workspace team creation with exception."""
        mock_workspace_team_create.side_effect = Exception("Workspace team creation error")
        
        mock_workspace = MagicMock()
        mock_workspace.organization = MagicMock()
        mock_team = MagicMock()
        mock_team.organization = mock_workspace.organization
        workspaces = [mock_workspace]
        teams = [mock_team]
        
        with self.assertRaises(Exception):
            self.command.create_workspace_teams(workspaces=workspaces, teams=teams)
        
        output = self.out.getvalue()
        self.assertIn("Error creating workspace teams: Workspace team creation error", output)

    @patch('apps.core.management.commands.seed_data.Entry.objects.create')
    @patch('apps.core.management.commands.seed_data.Currency.objects.all')
    def test_create_entries_success(self, mock_currency_all, mock_entry_create):
        """Test successful entry creation."""
        # Mock currencies
        mock_currency = MagicMock()
        mock_currency_all.return_value = [mock_currency]
        
        # Mock workspace and workspace team
        mock_workspace = MagicMock()
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace = mock_workspace
        
        workspaces = [mock_workspace]
        workspace_teams = [mock_workspace_team]
        
        # Mock the get_appropriate_exchange_rate method
        with patch.object(self.command, 'get_appropriate_exchange_rate', return_value=(Decimal('1.0'), None, None)):
            self.command.create_entries(workspaces=workspaces, workspace_teams=workspace_teams, entries_per_workspace=5)
        
        # Should create entries
        mock_entry_create.assert_called()

    @patch('apps.core.management.commands.seed_data.Entry.objects.create')
    @patch('apps.core.management.commands.seed_data.Currency.objects.all')
    def test_create_entries_exception(self, mock_currency_all, mock_entry_create):
        """Test entry creation with exception."""
        mock_currency = MagicMock()
        mock_currency_all.return_value = [mock_currency]
        mock_entry_create.side_effect = Exception("Entry creation error")
        
        mock_workspace = MagicMock()
        mock_workspace.start_date = date.today() - timedelta(days=30)
        mock_workspace.end_date = date.today()
        workspaces = [mock_workspace]
        workspace_teams = []
        
        # Mock the get_appropriate_exchange_rate method to return a valid rate
        with patch.object(self.command, 'get_appropriate_exchange_rate', return_value=(Decimal('1.0'), None, None)):
            with self.assertRaises(Exception):
                self.command.create_entries(workspaces=workspaces, workspace_teams=workspace_teams, entries_per_workspace=5)
            
            output = self.out.getvalue()
            self.assertIn("Error creating entries: Entry creation error", output)

    @patch('apps.core.management.commands.seed_data.OrganizationExchangeRate.objects.create')
    @patch('apps.core.management.commands.seed_data.WorkspaceExchangeRate.objects.create')
    @patch('apps.core.management.commands.seed_data.Currency.objects.all')
    def test_create_exchange_rates_success(
        self, mock_currency_all, mock_ws_rate_create, mock_org_rate_create
    ):
        """Test successful exchange rate creation."""
        # Mock currencies
        mock_currency1 = MagicMock()
        mock_currency2 = MagicMock()
        mock_currency3 = MagicMock()
        mock_currency_all.return_value = [mock_currency1, mock_currency2, mock_currency3]
        
        # Mock organization and workspace
        mock_org = MagicMock()
        mock_org.owner = MagicMock()
        mock_workspace = MagicMock()
        mock_workspace.workspace_admin = MagicMock()
        mock_workspace.operations_reviewer = MagicMock()
        mock_workspace.start_date = date.today() - timedelta(days=30)
        
        organizations = [mock_org]
        workspaces = [mock_workspace]
        
        self.command.create_exchange_rates(organizations=organizations, workspaces=workspaces)
        
        # Should create exchange rates
        mock_org_rate_create.assert_called()
        mock_ws_rate_create.assert_called()
        
        output = self.out.getvalue()
        self.assertIn("Created exchange rates for organizations and workspaces", output)

    @patch('apps.core.management.commands.seed_data.OrganizationExchangeRate.objects.create')
    @patch('apps.core.management.commands.seed_data.Currency.objects.all')
    def test_create_exchange_rates_exception(self, mock_currency_all, mock_org_rate_create):
        """Test exchange rate creation with exception."""
        mock_currency = MagicMock()
        mock_currency_all.return_value = [mock_currency]
        mock_org_rate_create.side_effect = Exception("Exchange rate creation error")
        
        mock_org = MagicMock()
        mock_org.owner = MagicMock()
        organizations = [mock_org]
        workspaces = []
        
        self.command.create_exchange_rates(organizations=organizations, workspaces=workspaces)
        
        output = self.out.getvalue()
        self.assertIn("Warning: Could not create exchange rates: Exchange rate creation error", output)

    def test_resolve_role_conflicts_success(self):
        """Test successful role conflict resolution."""
        # Mock organization with members
        mock_org = MagicMock()
        mock_owner = MagicMock()
        mock_member1 = MagicMock()
        mock_member2 = MagicMock()
        mock_org.owner = mock_owner
        mock_org.members.all.return_value = [mock_owner, mock_member1, mock_member2]
        
        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.organization = mock_org
        mock_workspace.workspace_admin = mock_member1
        mock_workspace.operations_reviewer = mock_member2
        
        # Mock team
        mock_team = MagicMock()
        mock_team.organization = mock_org
        mock_team.team_coordinator = mock_member1  # This creates a conflict
        
        organizations = [mock_org]
        workspaces = [mock_workspace]
        teams = [mock_team]
        
        self.command.resolve_role_conflicts(organizations=organizations, workspaces=workspaces, teams=teams)
        
        output = self.out.getvalue()
        self.assertIn("Resolving role conflicts", output)

    def test_resolve_role_conflicts_exception(self):
        """Test role conflict resolution with exception."""
        # Mock organization with members that will cause an exception
        mock_org = MagicMock()
        mock_org.members.all.side_effect = Exception("Members error")
        
        organizations = [mock_org]
        workspaces = []
        teams = []
        
        # Should handle exception gracefully
        self.command.resolve_role_conflicts(organizations=organizations, workspaces=workspaces, teams=teams)
        
        output = self.out.getvalue()
        self.assertIn("Warning: Could not resolve role conflicts", output)

    def test_get_appropriate_exchange_rate_workspace_rate(self):
        """Test getting workspace exchange rate."""
        # Mock workspace rate
        mock_ws_rate = MagicMock()
        mock_ws_rate.rate = Decimal('1.5')
        
        with patch('apps.core.management.commands.seed_data.WorkspaceExchangeRate.objects.filter') as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = mock_ws_rate
            
            rate, ws_ref, org_ref = self.command.get_appropriate_exchange_rate(
                organization=MagicMock(),
                workspace=MagicMock(),
                currency=MagicMock(),
                entry_date=date.today(),
                is_workspace_entry=True
            )
            
            self.assertEqual(rate, Decimal('1.5'))
            self.assertEqual(ws_ref, mock_ws_rate)
            self.assertIsNone(org_ref)

    def test_get_appropriate_exchange_rate_organization_rate(self):
        """Test getting organization exchange rate."""
        # Mock organization rate
        mock_org_rate = MagicMock()
        mock_org_rate.rate = Decimal('1.2')
        
        with patch('apps.core.management.commands.seed_data.OrganizationExchangeRate.objects.filter') as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = mock_org_rate
            
            rate, ws_ref, org_ref = self.command.get_appropriate_exchange_rate(
                organization=MagicMock(),
                workspace=None,
                currency=MagicMock(),
                entry_date=date.today(),
                is_workspace_entry=False
            )
            
            self.assertEqual(rate, Decimal('1.2'))
            self.assertIsNone(ws_ref)
            self.assertEqual(org_ref, mock_org_rate)

    def test_get_appropriate_exchange_rate_no_rate(self):
        """Test when no exchange rate is found."""
        with patch('apps.core.management.commands.seed_data.WorkspaceExchangeRate.objects.filter') as mock_ws_filter, \
             patch('apps.core.management.commands.seed_data.OrganizationExchangeRate.objects.filter') as mock_org_filter:
            
            mock_ws_filter.return_value.order_by.return_value.first.return_value = None
            mock_org_filter.return_value.order_by.return_value.first.return_value = None
            
            rate, ws_ref, org_ref = self.command.get_appropriate_exchange_rate(
                organization=MagicMock(),
                workspace=MagicMock(),
                currency=MagicMock(),
                entry_date=date.today(),
                is_workspace_entry=True
            )
            
            self.assertIsNone(rate)
            self.assertIsNone(ws_ref)
            self.assertIsNone(org_ref)

    @patch('apps.core.management.commands.seed_data.Entry.all_objects')
    @patch('apps.core.management.commands.seed_data.WorkspaceTeam.objects')
    @patch('apps.core.management.commands.seed_data.WorkspaceExchangeRate.all_objects')
    @patch('apps.core.management.commands.seed_data.OrganizationExchangeRate.all_objects')
    @patch('apps.core.management.commands.seed_data.Workspace.objects')
    @patch('apps.core.management.commands.seed_data.TeamMember.all_objects')
    @patch('apps.core.management.commands.seed_data.Team.objects')
    @patch('apps.core.management.commands.seed_data.OrganizationMember.all_objects')
    @patch('apps.core.management.commands.seed_data.Organization.all_objects')
    @patch('apps.core.management.commands.seed_data.CustomUser.objects')
    @patch('apps.core.management.commands.seed_data.Currency.all_objects')
    @patch('django.db.models.signals.post_delete')
    def test_clear_existing_data_success(
        self, mock_post_delete, mock_currency_objects, mock_user_objects,
        mock_org_objects, mock_org_member_objects, mock_team_objects,
        mock_team_member_objects, mock_workspace_objects, mock_org_rate_objects,
        mock_ws_rate_objects, mock_ws_team_objects, mock_entry_objects
    ):
        """Test successful data clearing."""
        # Mock counts
        mock_entry_objects.count.return_value = 10
        mock_entry_objects.all.return_value.hard_delete.return_value = None
        mock_ws_team_objects.count.return_value = 5
        mock_ws_team_objects.all.return_value.delete.return_value = None
        mock_ws_rate_objects.count.return_value = 3
        mock_ws_rate_objects.all.return_value.hard_delete.return_value = None
        mock_org_rate_objects.count.return_value = 2
        mock_org_rate_objects.all.return_value.hard_delete.return_value = None
        mock_workspace_objects.count.return_value = 1
        mock_workspace_objects.all.return_value.delete.return_value = None
        mock_team_member_objects.count.return_value = 4
        mock_team_member_objects.all.return_value.hard_delete.return_value = None
        mock_team_objects.count.return_value = 2
        mock_team_objects.all.return_value.delete.return_value = None
        mock_org_member_objects.count.return_value = 3
        mock_org_member_objects.all.return_value.hard_delete.return_value = None
        mock_org_objects.count.return_value = 1
        mock_org_objects.all.return_value.hard_delete.return_value = None
        mock_user_objects.filter.return_value.count.return_value = 2
        mock_user_objects.filter.return_value.delete.return_value = None
        mock_currency_objects.count.return_value = 8
        mock_currency_objects.all.return_value.hard_delete.return_value = None
        
        # Mock workspace filter for problem check - return empty queryset
        mock_workspace_filter = MagicMock()
        mock_workspace_filter.exists.return_value = False
        mock_workspace_objects.filter.return_value = mock_workspace_filter
        
        # Mock the specific filter call that checks for linked exchange rates
        mock_workspace_objects.filter.return_value.distinct.return_value = mock_workspace_filter
        
        with patch('apps.core.management.commands.seed_data.transaction.atomic'):
            self.command.clear_existing_data()
        
        output = self.out.getvalue()
        self.assertIn("Database cleared successfully", output)

    @patch('django.db.models.signals.post_delete')
    def test_clear_existing_data_exception(self, mock_post_delete):
        """Test data clearing with exception."""
        with patch('apps.core.management.commands.seed_data.transaction.atomic', side_effect=Exception("Clear error")):
            with self.assertRaises(Exception):
                self.command.clear_existing_data()
        
        output = self.out.getvalue()
        self.assertIn("Error clearing database: Clear error", output)

    def test_create_workspace_expense_entries(self):
        """Test workspace expense entry creation."""
        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.workspace_admin = MagicMock()
        mock_workspace.start_date = date.today() - timedelta(days=30)
        mock_workspace.end_date = date.today()
        
        # Mock currencies
        mock_currency = MagicMock()
        currencies = [mock_currency]
        entry_statuses = [EntryStatus.PENDING]
        
        with patch.object(self.command, 'get_appropriate_exchange_rate', return_value=(Decimal('1.0'), None, None)):
            with patch('apps.core.management.commands.seed_data.Entry.objects.create') as mock_create:
                self.command.create_workspace_expense_entries(
                    workspace=mock_workspace,
                    currencies=currencies,
                    entry_statuses=entry_statuses,
                    count=2
                )
                
                # Should create entries
                mock_create.assert_called()

    def test_create_organization_expense_entries(self):
        """Test organization expense entry creation."""
        # Mock workspace and organization
        mock_workspace = MagicMock()
        mock_org = MagicMock()
        mock_org.owner = MagicMock()
        mock_workspace.organization = mock_org
        mock_workspace.start_date = date.today() - timedelta(days=30)
        mock_workspace.end_date = date.today()
        
        # Mock currencies
        mock_currency = MagicMock()
        currencies = [mock_currency]
        entry_statuses = [EntryStatus.PENDING]
        
        with patch.object(self.command, 'get_appropriate_exchange_rate', return_value=(Decimal('1.0'), None, None)):
            with patch('apps.core.management.commands.seed_data.Entry.objects.create') as mock_create:
                self.command.create_organization_expense_entries(
                    workspace=mock_workspace,
                    currencies=currencies,
                    entry_statuses=entry_statuses,
                    count=2
                )
                
                # Should create entries
                mock_create.assert_called()



class SeedDataCommandIntegrationTest(TestCase):
    """Integration tests for the seed_data command."""

    def test_command_arguments_parsing(self):
        """Test that command arguments are parsed correctly."""
        from django.core.management import CommandParser
        parser = CommandParser()
        self.command = Command()
        self.command.add_arguments(parser)
        
        # Test parsing with various options
        parsed_args = parser.parse_args([
            '--organizations', '2',
            '--workspaces-per-org', '3',
            '--teams-per-org', '4',
            '--users-per-org', '15',
            '--entries-per-workspace', '75',
            '--clear-existing'
        ])
        
        self.assertEqual(parsed_args.organizations, 2)
        self.assertEqual(parsed_args.workspaces_per_org, 3)
        self.assertEqual(parsed_args.teams_per_org, 4)
        self.assertEqual(parsed_args.users_per_org, 15)
        self.assertEqual(parsed_args.entries_per_workspace, 75)
        self.assertTrue(parsed_args.clear_existing)

    def test_command_default_arguments(self):
        """Test command with default arguments."""
        from django.core.management import CommandParser
        parser = CommandParser()
        self.command = Command()
        self.command.add_arguments(parser)
        
        # Test parsing with no arguments (defaults)
        parsed_args = parser.parse_args([])
        
        self.assertEqual(parsed_args.organizations, 3)
        self.assertEqual(parsed_args.workspaces_per_org, 2)
        self.assertEqual(parsed_args.teams_per_org, 3)
        self.assertEqual(parsed_args.users_per_org, 20)
        self.assertEqual(parsed_args.entries_per_workspace, 100)
        self.assertFalse(parsed_args.clear_existing)
