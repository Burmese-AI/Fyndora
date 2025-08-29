"""
Unit tests for Team services.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.teams.services import (
    create_team_from_form,
    create_team_member_from_form,
    update_team_member_role,
    update_team_from_form,
    remove_team_member,
)
from apps.teams.models import Team, TeamMember
from apps.teams.constants import TeamMemberRole
from apps.teams.exceptions import (
    TeamCreationError,
    TeamMemberCreationError,
    TeamMemberUpdateError,
    TeamUpdateError,
    TeamMemberDeletionError,
)
from apps.workspaces.models import WorkspaceTeam
from tests.factories.organization_factories import (
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory


class TeamServicesTest(TestCase):
    """Test cases for Team services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team
        )

    @patch('apps.teams.services.BusinessAuditLogger.log_team_action')
    @patch('apps.teams.services.assign_team_permissions')
    def test_create_team_from_form_success(self, mock_assign_permissions, mock_audit_log):
        """Test successful team creation from form."""
        # Create a mock form
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            'title': 'Test Team',
            'description': 'Test Description',
            'team_coordinator': self.org_member
        }
        mock_form.save.return_value = self.team

        # Mock the form save to return our team
        with patch.object(Team, 'save'):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        # Verify the team was created with correct attributes
        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        
        # Verify permissions were assigned
        mock_assign_permissions.assert_called_once_with(team)
        
        # Verify audit logging was called
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_action')
    @patch('apps.teams.services.assign_team_permissions')
    def test_create_team_from_form_without_coordinator(self, mock_assign_permissions, mock_audit_log):
        """Test team creation without coordinator."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            'title': 'Test Team',
            'description': 'Test Description',
            'team_coordinator': None
        }
        mock_form.save.return_value = self.team

        with patch.object(Team, 'save'):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once_with(team)
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_operation_failure')
    def test_create_team_from_form_failure(self, mock_audit_log):
        """Test team creation failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'title': 'Test Team'}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamCreationError):
            create_team_from_form(mock_form, self.organization, self.org_member)

        # Verify failure was logged
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    def test_create_team_member_from_form_success(self, mock_audit_log):
        """Test successful team member creation from form."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            'organization_member': self.org_member,
            'role': TeamMemberRole.SUBMITTER
        }
        mock_form.save.return_value = self.team_member

        with patch.object(TeamMember, 'save'):
            team_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(team_member.team, self.team)
        self.assertEqual(team_member.organization, self.organization)
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_operation_failure')
    def test_create_team_member_from_form_failure(self, mock_audit_log):
        """Test team member creation failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'organization_member': self.org_member}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamMemberCreationError):
            create_team_member_from_form(mock_form, self.team, self.organization)

        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    @patch('apps.teams.services.update_team_coordinator_group')
    @patch('apps.teams.services.model_update')
    def test_update_team_member_role_success(self, mock_model_update, mock_update_group, mock_audit_log):
        """Test successful team member role update."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'role': TeamMemberRole.AUDITOR}
        
        mock_model_update.return_value = self.team_member

        team_member = update_team_member_role(
            form=mock_form,
            team_member=self.team_member,
            previous_role=TeamMemberRole.SUBMITTER,
            team=self.team
        )

        self.assertEqual(team_member, self.team_member)
        mock_model_update.assert_called_once()
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    @patch('apps.teams.services.update_team_coordinator_group')
    @patch('apps.teams.services.model_update')
    def test_update_team_member_role_from_coordinator(self, mock_model_update, mock_update_group, mock_audit_log):
        """Test updating role from team coordinator."""
        # Set up team member as coordinator
        self.team_member.role = TeamMemberRole.TEAM_COORDINATOR
        self.team.team_coordinator = self.org_member
        self.team.save()

        mock_form = MagicMock()
        mock_form.cleaned_data = {'role': TeamMemberRole.AUDITOR}
        
        mock_model_update.return_value = self.team_member

        with patch.object(Team, 'save'):
            team_member = update_team_member_role(
                form=mock_form,
                team_member=self.team_member,
                previous_role=TeamMemberRole.TEAM_COORDINATOR,
                team=self.team
            )

        # Verify coordinator was cleared
        self.assertIsNone(self.team.team_coordinator)
        mock_update_group.assert_called_once()
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_operation_failure')
    def test_update_team_member_role_failure(self, mock_audit_log):
        """Test team member role update failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'role': TeamMemberRole.AUDITOR}
        
        with patch('apps.teams.services.model_update', side_effect=Exception("Update error")):
            with self.assertRaises(TeamMemberUpdateError):
                update_team_member_role(
                    form=mock_form,
                    team_member=self.team_member,
                    previous_role=TeamMemberRole.SUBMITTER,
                    team=self.team
                )

        mock_audit_log.assert_called_once()


class TeamUpdateServiceTest(TestCase):
    """Test cases for team update service."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        # Ensure team has created_by set
        self.team.created_by = self.org_member
        self.team.save()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_action')
    @patch('apps.teams.services.model_update')
    def test_update_team_from_form_no_coordinator_change(self, mock_model_update, mock_audit_log):
        """Test team update when coordinator doesn't change."""
        previous_coordinator = self.org_member
        self.team.team_coordinator = previous_coordinator
        self.team.save()

        mock_form = MagicMock()
        mock_form.cleaned_data = {'title': 'Updated Team'}
        
        mock_model_update.return_value = self.team

        team = update_team_from_form(mock_form, self.team, self.organization, previous_coordinator)

        self.assertEqual(team, self.team)
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_action')
    @patch('apps.teams.services.model_update')
    def test_update_team_from_form_simple_update(self, mock_model_update, mock_audit_log):
        """Test simple team update without coordinator changes."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'title': 'Updated Team'}
        
        mock_model_update.return_value = self.team

        team = update_team_from_form(mock_form, self.team, self.organization, None)

        self.assertEqual(team, self.team)
        mock_audit_log.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_operation_failure')
    def test_update_team_from_form_failure(self, mock_audit_log):
        """Test team update failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'title': 'Updated Team'}
        
        with patch('apps.teams.services.model_update', side_effect=Exception("Update error")):
            with self.assertRaises(TeamUpdateError):
                update_team_from_form(mock_form, self.team, self.organization, None)

        mock_audit_log.assert_called_once()


class TeamMemberRemovalServiceTest(TestCase):
    """Test cases for team member removal service."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team
        )

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    @patch('apps.teams.services.update_team_coordinator_group')
    def test_remove_team_member_success(self, mock_update_group, mock_audit_log):
        """Test successful team member removal."""
        with patch.object(TeamMember, 'delete'):
            with patch.object(Team, 'save'):
                remove_team_member(self.team_member, self.team)

        # Verify audit logging was called
        mock_audit_log.assert_called()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    @patch('apps.teams.services.update_team_coordinator_group')
    def test_remove_team_member_coordinator(self, mock_update_group, mock_audit_log):
        """Test removing team coordinator."""
        # Set up team member as coordinator
        self.team_member.role = TeamMemberRole.TEAM_COORDINATOR
        self.team.team_coordinator = self.org_member
        self.team.save()

        with patch.object(TeamMember, 'delete'):
            with patch.object(Team, 'save'):
                remove_team_member(self.team_member, self.team)

        # Verify coordinator was cleared
        mock_update_group.assert_called_once()
        mock_audit_log.assert_called()

    @patch('apps.teams.services.BusinessAuditLogger.log_operation_failure')
    def test_remove_team_member_failure(self, mock_audit_log):
        """Test team member removal failure handling."""
        with patch.object(TeamMember, 'delete', side_effect=Exception("Delete error")):
            with self.assertRaises(TeamMemberDeletionError):
                remove_team_member(self.team_member, self.team)

        mock_audit_log.assert_called_once()


class TeamServicesIntegrationTest(TestCase):
    """Integration tests for Team services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        # Ensure team has created_by set
        self.team.created_by = self.org_member
        self.team.save()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_action')
    @patch('apps.teams.services.assign_team_permissions')
    def test_full_team_lifecycle(self, mock_assign_permissions, mock_audit_log):
        """Test complete team lifecycle with services."""
        # Create team
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            'title': 'Test Team',
            'description': 'Test Description',
            'team_coordinator': self.org_member
        }
        mock_form.save.return_value = self.team

        with patch.object(Team, 'save'):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once()

        # Update team - use a simple update without coordinator changes
        mock_update_form = MagicMock()
        mock_update_form.cleaned_data = {'title': 'Updated Team'}
        
        with patch('apps.teams.services.model_update', return_value=team):
            updated_team = update_team_from_form(
                mock_update_form, team, self.organization, None  # No previous coordinator
            )

        self.assertEqual(updated_team, team)

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    def test_team_member_lifecycle(self, mock_audit_log):
        """Test complete team member lifecycle with services."""
        # Create a team member for testing
        team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team
        )
        
        # Create team member
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            'organization_member': self.org_member,
            'role': TeamMemberRole.SUBMITTER
        }
        mock_form.save.return_value = team_member

        with patch.object(TeamMember, 'save'):
            created_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(created_member.team, self.team)
        self.assertEqual(created_member.organization, self.organization)

        # Update role
        mock_role_form = MagicMock()
        mock_role_form.cleaned_data = {'role': TeamMemberRole.AUDITOR}
        
        with patch('apps.teams.services.model_update', return_value=team_member):
            updated_member = update_team_member_role(
                form=mock_role_form,
                team_member=team_member,
                previous_role=TeamMemberRole.SUBMITTER,
                team=self.team
            )

        self.assertEqual(updated_member, team_member)

        mock_audit_log.assert_called()


class TeamServicesEdgeCasesTest(TestCase):
    """Test edge cases for Team services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

    @patch('apps.teams.services.BusinessAuditLogger.log_team_action')
    @patch('apps.teams.services.assign_team_permissions')
    def test_create_team_with_empty_form_data(self, mock_assign_permissions, mock_audit_log):
        """Test team creation with minimal form data."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {'title': 'Minimal Team'}
        mock_form.save.return_value = self.team

        with patch.object(Team, 'save'):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once()

    @patch('apps.teams.services.BusinessAuditLogger.log_team_member_action')
    def test_create_team_member_with_minimal_data(self, mock_audit_log):
        """Test team member creation with minimal data."""
        # Create a team member for testing
        team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team
        )
        
        mock_form = MagicMock()
        mock_form.cleaned_data = {'organization_member': self.org_member}
        mock_form.save.return_value = team_member

        with patch.object(TeamMember, 'save'):
            created_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(created_member.team, self.team)
        self.assertEqual(created_member.organization, self.organization)

    def test_update_team_member_role_same_role(self):
        """Test updating team member role to the same role."""
        # Create a team member for testing
        team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team
        )
        
        mock_form = MagicMock()
        mock_form.cleaned_data = {'role': TeamMemberRole.SUBMITTER}

        with patch('apps.teams.services.model_update', return_value=team_member):
            updated_member = update_team_member_role(
                form=mock_form,
                team_member=team_member,
                previous_role=TeamMemberRole.SUBMITTER,
                team=self.team
            )

        self.assertEqual(updated_member, team_member)
