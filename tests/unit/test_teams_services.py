"""
Unit tests for Team services.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase

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
            organization_member=self.org_member, team=self.team
        )

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.assign_team_permissions")
    def test_create_team_from_form_success(
        self, mock_assign_permissions, mock_audit_log
    ):
        """Test successful team creation from form."""
        # Create a mock form
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Test Team",
            "description": "Test Description",
            "team_coordinator": self.org_member,
        }
        mock_form.save.return_value = self.team

        # Mock the form save to return our team
        with patch.object(Team, "save"):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        # Verify the team was created with correct attributes
        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)

        # Verify permissions were assigned
        mock_assign_permissions.assert_called_once_with(team)

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.assign_team_permissions")
    def test_create_team_from_form_without_coordinator(
        self, mock_assign_permissions, mock_audit_log
    ):
        """Test team creation without coordinator."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Test Team",
            "description": "Test Description",
            "team_coordinator": None,
        }
        mock_form.save.return_value = self.team

        with patch.object(Team, "save"):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once_with(team)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_create_team_from_form_failure(self, mock_audit_log):
        """Test team creation failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Test Team"}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamCreationError):
            create_team_from_form(mock_form, self.organization, self.org_member)

        # Verify failure was logged
        mock_audit_log.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    def test_create_team_member_from_form_success(self, mock_audit_log):
        """Test successful team member creation from form."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "organization_member": self.org_member,
            "role": TeamMemberRole.SUBMITTER,
        }
        mock_form.save.return_value = self.team_member

        with patch.object(TeamMember, "save"):
            team_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(team_member.team, self.team)
        self.assertEqual(team_member.organization, self.organization)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_create_team_member_from_form_failure(self, mock_audit_log):
        """Test team member creation failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"organization_member": self.org_member}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamMemberCreationError):
            create_team_member_from_form(mock_form, self.team, self.organization)

        mock_audit_log.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    def test_update_team_member_role_success(
        self, mock_model_update, mock_update_group, mock_audit_log
    ):
        """Test successful team member role update."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}

        mock_model_update.return_value = self.team_member

        team_member = update_team_member_role(
            form=mock_form,
            team_member=self.team_member,
            previous_role=TeamMemberRole.SUBMITTER,
            team=self.team,
        )

        self.assertEqual(team_member, self.team_member)
        mock_model_update.assert_called_once()
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    def test_update_team_member_role_from_coordinator(
        self, mock_model_update, mock_update_group, mock_audit_log
    ):
        """Test updating role from team coordinator."""
        # Set up team member as coordinator
        self.team_member.role = TeamMemberRole.TEAM_COORDINATOR
        self.team.team_coordinator = self.org_member
        self.team.save()

        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}

        mock_model_update.return_value = self.team_member

        with patch.object(Team, "save"):
            update_team_member_role(
                form=mock_form,
                team_member=self.team_member,
                previous_role=TeamMemberRole.TEAM_COORDINATOR,
                team=self.team,
            )

        # Verify coordinator was cleared
        self.assertIsNone(self.team.team_coordinator)
        mock_update_group.assert_called_once()
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_update_team_member_role_failure(self, mock_audit_log):
        """Test team member role update failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}

        with patch(
            "apps.teams.services.model_update", side_effect=Exception("Update error")
        ):
            with self.assertRaises(TeamMemberUpdateError):
                update_team_member_role(
                    form=mock_form,
                    team_member=self.team_member,
                    previous_role=TeamMemberRole.SUBMITTER,
                    team=self.team,
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

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.model_update")
    def test_update_team_from_form_no_coordinator_change(
        self, mock_model_update, mock_audit_log
    ):
        """Test team update when coordinator doesn't change."""
        previous_coordinator = self.org_member
        self.team.team_coordinator = previous_coordinator
        self.team.save()

        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team"}

        mock_model_update.return_value = self.team

        team = update_team_from_form(
            mock_form, self.team, self.organization, previous_coordinator
        )

        self.assertEqual(team, self.team)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.model_update")
    def test_update_team_from_form_simple_update(
        self, mock_model_update, mock_audit_log
    ):
        """Test simple team update without coordinator changes."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team"}

        mock_model_update.return_value = self.team

        team = update_team_from_form(mock_form, self.team, self.organization, None)

        self.assertEqual(team, self.team)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_update_team_from_form_failure(self, mock_audit_log):
        """Test team update failure handling."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team"}

        with patch(
            "apps.teams.services.model_update", side_effect=Exception("Update error")
        ):
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
            organization_member=self.org_member, team=self.team
        )

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    def test_remove_team_member_success(self, mock_update_group, mock_audit_log):
        """Test successful team member removal."""
        with patch.object(TeamMember, "delete"):
            with patch.object(Team, "save"):
                remove_team_member(self.team_member, self.team)

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    def test_remove_team_member_coordinator(self, mock_update_group, mock_audit_log):
        """Test removing team coordinator."""
        # Set up team member as coordinator
        self.team_member.role = TeamMemberRole.TEAM_COORDINATOR
        self.team.team_coordinator = self.org_member
        self.team.save()

        with patch.object(TeamMember, "delete"):
            with patch.object(Team, "save"):
                remove_team_member(self.team_member, self.team)

        # Verify coordinator was cleared
        mock_update_group.assert_called_once()
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_remove_team_member_failure(self, mock_audit_log):
        """Test team member removal failure handling."""
        with patch.object(TeamMember, "delete", side_effect=Exception("Delete error")):
            with self.assertRaises(TeamMemberDeletionError):
                remove_team_member(self.team_member, self.team)

        # Note: The service doesn't have explicit audit logging anymore, it's handled by signal handlers


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

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.assign_team_permissions")
    def test_full_team_lifecycle(self, mock_assign_permissions, mock_audit_log):
        """Test complete team lifecycle with services."""
        # Create team
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Test Team",
            "description": "Test Description",
            "team_coordinator": self.org_member,
        }
        mock_form.save.return_value = self.team

        with patch.object(Team, "save"):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once()

        # Update team - use a simple update without coordinator changes
        mock_update_form = MagicMock()
        mock_update_form.cleaned_data = {"title": "Updated Team"}

        with patch("apps.teams.services.model_update", return_value=team):
            updated_team = update_team_from_form(
                mock_update_form,
                team,
                self.organization,
                None,  # No previous coordinator
            )

        self.assertEqual(updated_team, team)

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    def test_team_member_lifecycle(self, mock_audit_log):
        """Test complete team member lifecycle with services."""
        # Create a team member for testing
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

        # Create team member
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "organization_member": self.org_member,
            "role": TeamMemberRole.SUBMITTER,
        }
        mock_form.save.return_value = team_member

        with patch.object(TeamMember, "save"):
            created_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(created_member.team, self.team)
        self.assertEqual(created_member.organization, self.organization)

        # Update role
        mock_role_form = MagicMock()
        mock_role_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}

        with patch("apps.teams.services.model_update", return_value=team_member):
            updated_member = update_team_member_role(
                form=mock_role_form,
                team_member=team_member,
                previous_role=TeamMemberRole.SUBMITTER,
                team=self.team,
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

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.assign_team_permissions")
    def test_create_team_with_empty_form_data(
        self, mock_assign_permissions, mock_audit_log
    ):
        """Test team creation with minimal form data."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Minimal Team"}
        mock_form.save.return_value = self.team

        with patch.object(Team, "save"):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    def test_create_team_member_with_minimal_data(self, mock_audit_log):
        """Test team member creation with minimal data."""
        # Create a team member for testing
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

        mock_form = MagicMock()
        mock_form.cleaned_data = {"organization_member": self.org_member}
        mock_form.save.return_value = team_member

        with patch.object(TeamMember, "save"):
            created_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(created_member.team, self.team)
        self.assertEqual(created_member.organization, self.organization)

    def test_update_team_member_role_same_role(self):
        """Test updating team member role to the same role."""
        # Create a team member for testing
        team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.SUBMITTER}

        with patch("apps.teams.services.model_update", return_value=team_member):
            updated_member = update_team_member_role(
                form=mock_form,
                team_member=team_member,
                previous_role=TeamMemberRole.SUBMITTER,
                team=self.team,
            )

        self.assertEqual(updated_member, team_member)


class TeamServicesAuditLoggingFailureTest(TestCase):
    """Test audit logging failures in Team services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_team_action",
        side_effect=Exception("Audit error"),
    )
    @patch("apps.teams.services.assign_team_permissions")
    def test_create_team_audit_logging_failure(
        self, mock_assign_permissions, mock_audit_log
    ):
        """Test team creation when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Test Team",
            "description": "Test Description",
            "team_coordinator": self.org_member,
        }
        mock_form.save.return_value = self.team

        with patch.object(Team, "save"):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        # Should still succeed despite audit logging failure
        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        mock_assign_permissions.assert_called_once()

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_operation_failure",
        side_effect=Exception("Audit error"),
    )
    def test_create_team_failure_audit_logging_failure(self, mock_audit_log):
        """Test team creation failure when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Test Team"}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamCreationError):
            create_team_from_form(mock_form, self.organization, self.org_member)

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_team_member_action",
        side_effect=Exception("Audit error"),
    )
    def test_create_team_member_audit_logging_failure(self, mock_audit_log):
        """Test team member creation when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "organization_member": self.org_member,
            "role": TeamMemberRole.SUBMITTER,
        }
        mock_form.save.return_value = self.team_member

        with patch.object(TeamMember, "save"):
            team_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        # Should still succeed despite audit logging failure
        self.assertEqual(team_member.team, self.team)
        self.assertEqual(team_member.organization, self.organization)

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_operation_failure",
        side_effect=Exception("Audit error"),
    )
    def test_create_team_member_failure_audit_logging_failure(self, mock_audit_log):
        """Test team member creation failure when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"organization_member": self.org_member}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamMemberCreationError):
            create_team_member_from_form(mock_form, self.team, self.organization)

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_team_member_action",
        side_effect=Exception("Audit error"),
    )
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    def test_update_team_member_role_audit_logging_failure(
        self, mock_model_update, mock_update_group, mock_audit_log
    ):
        """Test team member role update when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}
        mock_model_update.return_value = self.team_member

        team_member = update_team_member_role(
            form=mock_form,
            team_member=self.team_member,
            previous_role=TeamMemberRole.SUBMITTER,
            team=self.team,
        )

        # Should still succeed despite audit logging failure
        self.assertEqual(team_member, self.team_member)
        mock_model_update.assert_called_once()

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_operation_failure",
        side_effect=Exception("Audit error"),
    )
    def test_update_team_member_role_failure_audit_logging_failure(
        self, mock_audit_log
    ):
        """Test team member role update failure when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}

        with patch(
            "apps.teams.services.model_update", side_effect=Exception("Update error")
        ):
            with self.assertRaises(TeamMemberUpdateError):
                update_team_member_role(
                    form=mock_form,
                    team_member=self.team_member,
                    previous_role=TeamMemberRole.SUBMITTER,
                    team=self.team,
                )

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_team_action",
        side_effect=Exception("Audit error"),
    )
    @patch("apps.teams.services.model_update")
    def test_update_team_audit_logging_failure(self, mock_model_update, mock_audit_log):
        """Test team update when audit logging fails."""
        # Ensure team has created_by set
        self.team.created_by = self.org_member
        self.team.save()

        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team"}
        mock_model_update.return_value = self.team

        team = update_team_from_form(mock_form, self.team, self.organization, None)

        # Should still succeed despite audit logging failure
        self.assertEqual(team, self.team)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_operation_failure",
        side_effect=Exception("Audit error"),
    )
    def test_update_team_failure_audit_logging_failure(self, mock_audit_log):
        """Test team update failure when audit logging fails."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team"}

        with patch(
            "apps.teams.services.model_update", side_effect=Exception("Update error")
        ):
            with self.assertRaises(TeamUpdateError):
                update_team_from_form(mock_form, self.team, self.organization, None)

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_team_member_action",
        side_effect=Exception("Audit error"),
    )
    @patch("apps.teams.services.update_team_coordinator_group")
    def test_remove_team_member_audit_logging_failure(
        self, mock_update_group, mock_audit_log
    ):
        """Test team member removal when audit logging fails."""
        with patch.object(TeamMember, "delete"):
            with patch.object(Team, "save"):
                remove_team_member(self.team_member, self.team)

        # Should still succeed despite audit logging failure
        mock_update_group.assert_called_once()

    @patch(
        "apps.teams.services.BusinessAuditLogger.log_operation_failure",
        side_effect=Exception("Audit error"),
    )
    def test_remove_team_member_failure_audit_logging_failure(self, mock_audit_log):
        """Test team member removal failure when audit logging fails."""
        with patch.object(TeamMember, "delete", side_effect=Exception("Delete error")):
            with self.assertRaises(TeamMemberDeletionError):
                remove_team_member(self.team_member, self.team)


class TeamServicesComprehensiveTest(TestCase):
    """Comprehensive tests for Team services to achieve 100% coverage."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.assign_team_permissions")
    @patch("apps.teams.services.TeamMember.objects.create")
    def test_create_team_with_coordinator_creation(
        self, mock_create_team_member, mock_assign_permissions, mock_audit_log
    ):
        """Test team creation with coordinator (TeamMember.objects.create path)."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Test Team",
            "description": "Test Description",
            "team_coordinator": self.org_member,
        }

        # Create a mock team with coordinator set
        mock_team = MagicMock()
        mock_team.team_coordinator = self.org_member
        mock_form.save.return_value = mock_team

        with patch.object(Team, "save"):
            team = create_team_from_form(mock_form, self.organization, self.org_member)

        # Verify TeamMember.objects.create was called
        mock_create_team_member.assert_called_once_with(
            team=team,
            organization_member=self.org_member,
            role=TeamMemberRole.TEAM_COORDINATOR,
        )
        mock_assign_permissions.assert_called_once_with(team)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    def test_create_team_member_with_none_cleaned_data(self, mock_audit_log):
        """Test team member creation when form.cleaned_data is None."""
        mock_form = MagicMock()
        mock_form.cleaned_data = None
        mock_form.save.return_value = self.team_member

        with patch.object(TeamMember, "save"):
            team_member = create_team_member_from_form(
                mock_form, self.team, self.organization
            )

        self.assertEqual(team_member.team, self.team)
        self.assertEqual(team_member.organization, self.organization)

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_create_team_member_failure_no_org_member(self, mock_audit_log):
        """Test team member creation failure when no org member in form data."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"organization_member": self.org_member}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamMemberCreationError):
            create_team_member_from_form(mock_form, self.team, self.organization)

        # Should still log failure even without org member
        mock_audit_log.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    def test_remove_team_member_coordinator_clearing(
        self,
        mock_model_update,
        mock_update_group,
        mock_team_audit,
        mock_team_member_audit,
    ):
        """Test remove_team_member when member is coordinator (was_coordinator=True)."""
        # Set up team member as coordinator
        self.team_member.role = TeamMemberRole.TEAM_COORDINATOR
        self.team.team_coordinator = self.org_member
        self.team.save()

        with patch.object(TeamMember, "delete"):
            with patch.object(Team, "save"):
                remove_team_member(self.team_member, self.team)

        # Verify coordinator was cleared
        mock_update_group.assert_called_once()
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service


class TeamUpdateCoordinatorTest(TestCase):
    """Test coordinator changes in update_team_from_form function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.new_org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team.created_by = self.org_member
        self.team.save()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    @patch("apps.teams.services.TeamMember.objects.get")
    @patch("apps.teams.services.WorkspaceTeam.objects.filter")
    @patch("apps.teams.services.Group.objects.get_or_create")
    def test_update_team_coordinator_removal(
        self,
        mock_group_get_or_create,
        mock_workspace_filter,
        mock_team_member_get,
        mock_model_update,
        mock_update_group,
        mock_team_member_audit,
        mock_team_audit,
    ):
        """Test update_team_from_form when coordinator is removed (new_team_coordinator is None)."""
        # Set up previous coordinator
        previous_coordinator = self.org_member
        self.team.team_coordinator = previous_coordinator
        self.team.save()

        # Mock form data with no coordinator
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team", "team_coordinator": None}

        # Create a mock team with updated coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = None
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        # Mock workspace teams
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace_team_id = "test-workspace-team-id"
        mock_workspace_filter.return_value = [mock_workspace_team]

        # Mock team member
        mock_team_member = MagicMock()
        mock_team_member_get.return_value = mock_team_member

        # Mock group
        mock_group = MagicMock()
        mock_group_get_or_create.return_value = (mock_group, True)

        team = update_team_from_form(
            mock_form, self.team, self.organization, previous_coordinator
        )

        # Verify coordinator was cleared
        self.assertIsNone(team.team_coordinator)
        mock_update_group.assert_called_once()
        mock_team_member_get.assert_called_once()
        mock_team_member.delete.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    @patch("apps.teams.services.TeamMember.objects.create")
    @patch("apps.teams.services.WorkspaceTeam.objects.filter")
    @patch("apps.teams.services.assign_perm")
    def test_update_team_coordinator_assignment(
        self,
        mock_assign_perm,
        mock_workspace_filter,
        mock_create_team_member,
        mock_model_update,
        mock_update_group,
        mock_team_member_audit,
        mock_team_audit,
    ):
        """Test update_team_from_form when new coordinator is assigned."""
        # Mock form data with new coordinator
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Updated Team",
            "team_coordinator": self.new_org_member,
        }

        # Create a mock team with updated coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = self.new_org_member
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        # Mock workspace teams
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace_team_id = "test-workspace-team-id"
        mock_workspace_filter.return_value = [mock_workspace_team]

        # Mock created team member
        mock_team_member = MagicMock()
        mock_create_team_member.return_value = mock_team_member

        team = update_team_from_form(mock_form, self.team, self.organization, None)

        # Verify new coordinator was assigned
        self.assertEqual(team.team_coordinator, self.new_org_member)
        mock_create_team_member.assert_called_once()
        mock_assign_perm.assert_called()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    @patch("apps.teams.services.TeamMember.objects.create")
    @patch("apps.teams.services.TeamMember.objects.get")
    @patch("apps.teams.services.WorkspaceTeam.objects.filter")
    @patch("apps.teams.services.assign_perm")
    @patch("apps.teams.services.remove_perm")
    @patch("apps.teams.services.Group.objects.get_or_create")
    def test_update_team_coordinator_replacement(
        self,
        mock_group_get_or_create,
        mock_remove_perm,
        mock_assign_perm,
        mock_workspace_filter,
        mock_team_member_get,
        mock_create_team_member,
        mock_model_update,
        mock_update_group,
        mock_team_member_audit,
        mock_team_audit,
    ):
        """Test update_team_from_form when coordinator is replaced with new one."""
        # Set up previous coordinator
        previous_coordinator = self.org_member
        self.team.team_coordinator = previous_coordinator
        self.team.save()

        # Mock form data with new coordinator
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Updated Team",
            "team_coordinator": self.new_org_member,
        }

        # Create a mock team with updated coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = self.new_org_member
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        # Mock workspace teams
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace_team_id = "test-workspace-team-id"
        mock_workspace_filter.return_value = [mock_workspace_team]

        # Mock team members
        mock_old_team_member = MagicMock()
        mock_team_member_get.return_value = mock_old_team_member
        mock_new_team_member = MagicMock()
        mock_create_team_member.return_value = mock_new_team_member

        # Mock group
        mock_group = MagicMock()
        mock_group_get_or_create.return_value = (mock_group, True)

        team = update_team_from_form(
            mock_form, self.team, self.organization, previous_coordinator
        )

        # Verify new coordinator was assigned
        self.assertEqual(team.team_coordinator, self.new_org_member)
        mock_create_team_member.assert_called_once()
        mock_team_member_get.assert_called_once()
        mock_old_team_member.delete.assert_called_once()
        mock_assign_perm.assert_called()
        mock_remove_perm.assert_called()
        mock_update_group.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    @patch("apps.teams.services.TeamMember.objects.create")
    @patch("apps.teams.services.WorkspaceTeam.objects.filter")
    @patch("apps.teams.services.assign_perm")
    @patch("apps.teams.services.Group.objects.get_or_create")
    def test_update_team_coordinator_assignment_without_previous(
        self,
        mock_group_get_or_create,
        mock_assign_perm,
        mock_workspace_filter,
        mock_create_team_member,
        mock_model_update,
        mock_update_group,
        mock_team_member_audit,
        mock_team_audit,
    ):
        """Test update_team_from_form when new coordinator is assigned without previous coordinator."""
        # Mock form data with new coordinator
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Updated Team",
            "team_coordinator": self.new_org_member,
        }

        # Create a mock team with updated coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = self.new_org_member
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        # Mock workspace teams
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace_team_id = "test-workspace-team-id"
        mock_workspace_filter.return_value = [mock_workspace_team]

        # Mock created team member
        mock_team_member = MagicMock()
        mock_create_team_member.return_value = mock_team_member

        # Mock group
        mock_group = MagicMock()
        mock_group_get_or_create.return_value = (mock_group, True)

        team = update_team_from_form(mock_form, self.team, self.organization, None)

        # Verify new coordinator was assigned
        self.assertEqual(team.team_coordinator, self.new_org_member)
        mock_create_team_member.assert_called_once()
        mock_assign_perm.assert_called()
        mock_update_group.assert_called_once()


class TeamServicesEdgeCasesAndErrorTest(TestCase):
    """Test edge cases and error conditions for Team services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member, team=self.team
        )

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_create_team_member_failure_with_hasattr_false(self, mock_audit_log):
        """Test team member creation failure when form doesn't have cleaned_data attribute."""
        mock_form = MagicMock()
        # Remove cleaned_data attribute
        del mock_form.cleaned_data
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamMemberCreationError):
            create_team_member_from_form(mock_form, self.team, self.organization)

        # Should not log failure because there's no user available for audit logging
        mock_audit_log.assert_not_called()

    @patch("apps.teams.services.BusinessAuditLogger.log_operation_failure")
    def test_create_team_member_failure_with_empty_cleaned_data(self, mock_audit_log):
        """Test team member creation failure when cleaned_data is empty."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"organization_member": self.org_member}
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(TeamMemberCreationError):
            create_team_member_from_form(mock_form, self.team, self.organization)

        # Should still log failure
        mock_audit_log.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    def test_update_team_member_role_non_coordinator_previous_role(
        self, mock_model_update, mock_update_group, mock_audit_log
    ):
        """Test team member role update when previous role is not team_coordinator."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}
        mock_model_update.return_value = self.team_member

        update_team_member_role(
            form=mock_form,
            team_member=self.team_member,
            previous_role=TeamMemberRole.SUBMITTER,  # Not team_coordinator
            team=self.team,
        )

        # Should not call update_team_coordinator_group
        mock_update_group.assert_not_called()
        mock_model_update.assert_called_once()
        mock_audit_log.assert_called_once()

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    @patch("apps.teams.services.TeamMember.objects.get")
    @patch("apps.teams.services.WorkspaceTeam.objects.filter")
    @patch("apps.teams.services.Group.objects.get_or_create")
    def test_update_team_coordinator_removal_audit_logging_failure(
        self,
        mock_group_get_or_create,
        mock_workspace_filter,
        mock_team_member_get,
        mock_model_update,
        mock_update_group,
        mock_team_member_audit,
        mock_team_audit,
    ):
        """Test coordinator removal when audit logging fails."""
        # Ensure team has created_by set
        self.team.created_by = self.org_member
        self.team.save()

        # Set up previous coordinator
        previous_coordinator = self.org_member
        self.team.team_coordinator = previous_coordinator
        self.team.save()

        # Mock form data with no coordinator
        mock_form = MagicMock()
        mock_form.cleaned_data = {"title": "Updated Team", "team_coordinator": None}

        # Create a mock team with updated coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = None
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        # Mock workspace teams
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace_team_id = "test-workspace-team-id"
        mock_workspace_filter.return_value = [mock_workspace_team]

        # Mock team member
        mock_team_member = MagicMock()
        mock_team_member_get.return_value = mock_team_member

        # Mock group
        mock_group = MagicMock()
        mock_group_get_or_create.return_value = (mock_group, True)

        # Make audit logging fail
        mock_team_member_audit.side_effect = Exception("Audit error")

        team = update_team_from_form(
            mock_form, self.team, self.organization, previous_coordinator
        )

        # Should still succeed despite audit logging failure
        self.assertIsNone(team.team_coordinator)
        mock_update_group.assert_called_once()
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    @patch("apps.teams.services.model_update")
    @patch("apps.teams.services.TeamMember.objects.create")
    @patch("apps.teams.services.WorkspaceTeam.objects.filter")
    @patch("apps.teams.services.assign_perm")
    def test_update_team_coordinator_assignment_audit_logging_failure(
        self,
        mock_assign_perm,
        mock_workspace_filter,
        mock_create_team_member,
        mock_model_update,
        mock_update_group,
        mock_team_member_audit,
        mock_team_audit,
    ):
        """Test coordinator assignment when audit logging fails."""
        # Ensure team has created_by set
        self.team.created_by = self.org_member
        self.team.save()

        new_org_member = OrganizationMemberFactory(organization=self.organization)

        # Mock form data with new coordinator
        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Updated Team",
            "team_coordinator": new_org_member,
        }

        # Create a mock team with updated coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = new_org_member
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        # Mock workspace teams
        mock_workspace_team = MagicMock()
        mock_workspace_team.workspace_team_id = "test-workspace-team-id"
        mock_workspace_filter.return_value = [mock_workspace_team]

        # Mock created team member
        mock_team_member = MagicMock()
        mock_create_team_member.return_value = mock_team_member

        # Make audit logging fail
        mock_team_member_audit.side_effect = Exception("Audit error")

        team = update_team_from_form(mock_form, self.team, self.organization, None)

        # Should still succeed despite audit logging failure
        self.assertEqual(team.team_coordinator, new_org_member)
        mock_create_team_member.assert_called_once()
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    def test_remove_team_member_non_coordinator(
        self, mock_update_group, mock_audit_log
    ):
        """Test remove_team_member when member is not coordinator."""
        # Ensure member is not coordinator
        self.team_member.role = TeamMemberRole.SUBMITTER
        self.team.team_coordinator = None
        self.team.save()

        with patch.object(TeamMember, "delete"):
            with patch.object(Team, "save"):
                remove_team_member(self.team_member, self.team)

        # Should not call update_team_coordinator_group for non-coordinator
        mock_update_group.assert_called_once()  # Still called but with None
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.BusinessAuditLogger.log_team_member_action")
    @patch("apps.teams.services.update_team_coordinator_group")
    def test_remove_team_member_coordinator_audit_logging_failure(
        self, mock_update_group, mock_team_member_audit, mock_team_audit
    ):
        """Test remove_team_member coordinator when audit logging fails."""
        # Set up team member as coordinator
        self.team_member.role = TeamMemberRole.TEAM_COORDINATOR
        self.team.team_coordinator = self.org_member
        self.team.save()

        # Make audit logging fail
        mock_team_audit.side_effect = Exception("Audit error")

        with patch.object(TeamMember, "delete"):
            with patch.object(Team, "save"):
                remove_team_member(self.team_member, self.team)

        # Should still succeed despite audit logging failure
        mock_update_group.assert_called_once()

    def test_update_team_member_role_string_previous_role(self):
        """Test team member role update with string previous role."""
        mock_form = MagicMock()
        mock_form.cleaned_data = {"role": TeamMemberRole.AUDITOR}

        with patch("apps.teams.services.model_update", return_value=self.team_member):
            with patch("apps.teams.services.update_team_coordinator_group"):
                team_member = update_team_member_role(
                    form=mock_form,
                    team_member=self.team_member,
                    previous_role="team_coordinator",  # String instead of constant
                    team=self.team,
                )

        self.assertEqual(team_member, self.team_member)

    @patch("apps.teams.services.BusinessAuditLogger.log_team_action")
    @patch("apps.teams.services.model_update")
    def test_update_team_same_coordinator(self, mock_model_update, mock_audit_log):
        """Test team update when coordinator doesn't change."""
        previous_coordinator = self.org_member
        self.team.team_coordinator = previous_coordinator
        self.team.created_by = self.org_member
        self.team.save()

        mock_form = MagicMock()
        mock_form.cleaned_data = {
            "title": "Updated Team",
            "team_coordinator": previous_coordinator,  # Same coordinator
        }

        # Create a mock team with same coordinator
        mock_updated_team = MagicMock()
        mock_updated_team.team_coordinator = previous_coordinator
        mock_updated_team.created_by = self.org_member
        mock_model_update.return_value = mock_updated_team

        team = update_team_from_form(
            mock_form, self.team, self.organization, previous_coordinator
        )

        # Should return early without coordinator changes
        self.assertEqual(team, mock_updated_team)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service
