"""Tests for TeamAuditLogger."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.team_logger import TeamAuditLogger
from tests.factories.organization_factories import OrganizationMemberFactory
from tests.factories.team_factories import TeamMemberFactory
from tests.factories.user_factories import CustomUserFactory


@patch("apps.auditlog.utils.safe_audit_log", lambda func: func)
class TestTeamAuditLogger(TestCase):
    """Test cases for TeamAuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = TeamAuditLogger()
        self.mock_user = Mock(spec=User)
        self.mock_user.user_id = "test-user-123"
        self.mock_user.email = "test@example.com"
        self.mock_user.is_authenticated = True

        self.mock_request = Mock(spec=HttpRequest)
        self.mock_request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "Test Browser",
        }


@pytest.mark.unit
class TestTeamAuditLoggerComprehensiveScenarios(TestCase):
    """Comprehensive test scenarios for team audit logging."""

    def setUp(self):
        """Set up test fixtures."""
        from tests.factories.organization_factories import (
            OrganizationFactory,
            OrganizationMemberFactory,
        )
        from tests.factories.team_factories import TeamFactory, TeamMemberFactory
        from tests.factories.user_factories import CustomUserFactory
        from tests.factories.workspace_factories import WorkspaceFactory

        self.logger = TeamAuditLogger()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            team=self.team, organization_member=self.org_member
        )

        # Add mock objects for tests that need them
        self.mock_request = Mock(spec=HttpRequest)
        self.mock_request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "Test Browser",
        }

        self.mock_user = Mock(spec=User)
        self.mock_user.user_id = "test-user-123"
        self.mock_user.email = "test@example.com"
        self.mock_user.is_authenticated = True

        self.mock_team = Mock()
        self.mock_team.id = "test-team-123"
        self.mock_team.name = "Test Team"

        self.mock_member = Mock()
        self.mock_member.id = "test-member-123"
        self.mock_member.user = self.mock_user

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_team_member_addition_with_foreign_key_relationships(
        self, mock_finalize_audit
    ):
        """Test team member addition with comprehensive foreign key relationships."""

        # Log team member addition
        self.logger.log_team_member_action(
            user=self.user,
            team=self.team,
            member=self.team_member,
            action="add",
            invitation_sent=True,
        )

        # Verify audit log creation with foreign key metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]  # metadata is the third argument

        self.assertIn("team_id", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("member_email", metadata)
        self.assertIn("invitation_sent", metadata)
        self.assertTrue(metadata["invitation_sent"])

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_team_member_role_change_comprehensive_metadata(self, mock_finalize_audit):
        """Test team member role change with comprehensive metadata tracking."""

        # Log role change
        self.logger.log_team_member_action(
            user=self.user,
            team=self.team,
            member=self.team_member,
            action="role_change",
            previous_role="submitter",
            new_role="coordinator",
            reason="Promotion based on performance",
            effective_date="2024-01-15",
        )

        # Verify comprehensive metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertEqual(metadata["previous_role"], "submitter")
        self.assertEqual(metadata["new_role"], "coordinator")
        self.assertEqual(
            metadata["role_change_reason"], "Promotion based on performance"
        )
        self.assertEqual(metadata["effective_date"], "2024-01-15")

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_team_member_removal_with_context(self, mock_finalize_audit):
        """Test team member removal with contextual information."""

        # Log member removal
        self.logger.log_team_member_action(
            user=self.user,
            team=self.team,
            member=self.team_member,
            action="remove",
            reason="Performance issues",
            removed_by_role="team_coordinator",
            final_contribution_count=45,
            exit_interview_completed=True,
        )

        # Verify contextual metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertEqual(metadata["reason"], "Performance issues")
        self.assertEqual(metadata["removed_by_role"], "team_coordinator")
        self.assertEqual(metadata["final_contribution_count"], 45)
        self.assertTrue(metadata["exit_interview_completed"])

    def test_audit_factory_integration_team_member_added(self):
        """Test integration with TeamMemberAddedAuditFactory."""
        from tests.factories.auditlog_factories import TeamMemberAddedAuditFactory

        # Create audit log using factory
        audit_log = TeamMemberAddedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.TEAM_MEMBER_ADDED)
        self.assertIn("team_id", audit_log.metadata)
        self.assertIn("organization_id", audit_log.metadata)
        self.assertIn("member_email", audit_log.metadata)

    def test_audit_factory_integration_team_member_removed(self):
        """Test integration with TeamMemberRemovedAuditFactory."""
        from tests.factories.auditlog_factories import TeamMemberRemovedAuditFactory

        # Create audit log using factory
        audit_log = TeamMemberRemovedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.TEAM_MEMBER_REMOVED)
        self.assertIn("removed_by", audit_log.metadata)
        self.assertEqual(audit_log.metadata["removed_by"], self.user.username)

    def test_audit_factory_integration_role_changed(self):
        """Test integration with TeamMemberRoleChangedAuditFactory."""
        from tests.factories.auditlog_factories import TeamMemberRoleChangedAuditFactory

        # Create audit log using factory
        audit_log = TeamMemberRoleChangedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(
            audit_log.action_type, AuditActionType.TEAM_MEMBER_ROLE_CHANGED
        )
        self.assertIn("old_role", audit_log.metadata)
        self.assertIn("new_role", audit_log.metadata)
        self.assertIn("changed_by", audit_log.metadata)

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_bulk_team_member_operations_performance(self, mock_finalize_audit):
        """Test performance of bulk team member operations."""
        import time

        # Create multiple team members
        team_members = []
        for i in range(10):
            member = TeamMemberFactory(
                team=self.team,
                organization_member=OrganizationMemberFactory(
                    organization=self.organization, user=CustomUserFactory()
                ),
            )
            team_members.append(member)

        start_time = time.time()

        # Log multiple team member additions
        for member in team_members:
            self.logger.log_team_member_action(
                user=self.user,
                team=self.team,
                member=member,
                action="add",
                bulk_operation=True,
            )

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete within reasonable time
        self.assertLess(execution_time, 2.0, "Bulk team operations took too long")
        self.assertEqual(mock_finalize_audit.call_count, 10)

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_team_audit_with_workspace_context(self, mock_finalize_audit):
        """Test team audit logging with workspace context."""

        # Set workspace on team
        self.team.workspace = self.workspace

        # Log team action
        self.logger.log_team_action(
            user=self.user,
            team=self.team,
            action="create",
            workspace_integration=True,
        )

        # Verify workspace context is included
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args
        workspace_arg = call_args[0][4]  # workspace is the 5th argument

        self.assertEqual(workspace_arg, self.workspace)

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_team_audit_metadata_validation(self, mock_finalize_audit):
        """Test validation of team audit metadata structure."""

        # Log team member action with complex metadata
        complex_metadata = {
            "nested_data": {
                "permissions": ["read", "write", "admin"],
                "settings": {"notifications": True, "auto_assign": False},
            },
            "timestamps": {
                "created": "2024-01-15T10:30:00Z",
                "last_active": "2024-01-20T15:45:00Z",
            },
        }

        self.logger.log_team_member_action(
            user=self.user,
            team=self.team,
            member=self.team_member,
            action="add",
            **complex_metadata,
        )

        # Verify complex metadata is preserved
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertIn("nested_data", metadata)
        self.assertIn("timestamps", metadata)
        self.assertEqual(
            metadata["nested_data"]["permissions"], ["read", "write", "admin"]
        )
        self.assertTrue(metadata["nested_data"]["settings"]["notifications"])
        self.mock_request.method = "POST"
        self.mock_request.path = "/test/path"
        self.mock_request.session = Mock()
        self.mock_request.session.session_key = "test-session-key"

        self.mock_team = Mock()
        self.mock_team.team_id = "team-123"
        self.mock_team.name = "Test Team"
        self.mock_team.description = "Test team description"
        self.mock_team.team_type = "translation"
        self.mock_team.status = "active"
        self.mock_team.pk = "team-123"
        self.mock_team.__class__.__name__ = "Team"
        self.mock_team.__class__.__module__ = "apps.teams.models"
        self.mock_team._meta = Mock()
        self.mock_team._meta.pk = Mock()
        self.mock_team._meta.pk.name = "pk"
        self.mock_team.workspace = Mock()
        self.mock_team.workspace.pk = "workspace-123"

        self.mock_member = Mock()
        self.mock_member.user_id = "member-456"
        self.mock_member.email = "member@example.com"
        self.mock_member.first_name = "John"
        self.mock_member.last_name = "Doe"
        self.mock_member.pk = "member-456"
        self.mock_member.__class__.__name__ = "User"
        self.mock_member.__class__.__module__ = "django.contrib.auth.models"
        self.mock_member._meta = Mock()
        self.mock_member._meta.pk = Mock()
        self.mock_member._meta.pk.name = "pk"

    def test_get_supported_actions(self):
        """Test that get_supported_actions returns correct actions."""
        expected_actions = {"create", "update", "delete"}
        self.assertEqual(set(self.logger.get_supported_actions()), expected_actions)

    def test_get_logger_name(self):
        """Test that get_logger_name returns correct name."""
        self.assertEqual(self.logger.get_logger_name(), "team_logger")

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
    )
    def test_log_team_action_create(self, mock_team_metadata, mock_finalize_audit):
        """Test log_team_action for create action."""
        # Setup mocks
        mock_team_metadata.return_value = {
            "team_id": "team-123",
            "team_name": "Test Team",
            "team_type": "translation",
        }

        # Call method
        self.logger.log_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            team=self.mock_team,
        )

        # Verify calls
        mock_team_metadata.assert_called_once_with(self.mock_team)
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.TEAM_CREATED)  # action_type
        self.assertIsInstance(call_args[2], dict)  # metadata
        self.assertEqual(call_args[3], self.mock_team)  # target_entity
        # workspace is call_args[4]

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    def test_log_team_action_update(
        self, mock_crud_metadata, mock_team_metadata, mock_finalize_audit
    ):
        """Test log_team_action for update action."""
        # Setup mocks
        mock_team_metadata.return_value = {
            "team_id": "team-123",
            "team_name": "Test Team",
        }
        mock_crud_metadata.return_value = {"action_metadata": "update_data"}

        # Call method
        self.logger.log_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            team=self.mock_team,
            updated_fields=["name", "description"],
        )

        # Verify calls
        mock_team_metadata.assert_called_once_with(self.mock_team)

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.TEAM_UPDATED)

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    def test_log_team_action_delete(
        self, mock_crud_metadata, mock_team_metadata, mock_finalize_audit
    ):
        """Test log_team_action for delete action."""
        # Setup mocks
        mock_team_metadata.return_value = {"team_id": "team-123"}
        mock_crud_metadata.return_value = {"action_metadata": "delete_data"}

        # Call method
        self.logger.log_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            team=self.mock_team,
            soft_delete=True,
            reason="Team restructuring",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.TEAM_DELETED)

        # Verify reason is included in metadata
        metadata = call_args[2]
        self.assertEqual(metadata["reason"], "Team restructuring")

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_log_team_member_action_add(self, mock_finalize_audit):
        """Test log_team_member_action for add action."""
        # Call method
        self.logger.log_team_member_action(
            request=self.mock_request,
            user=self.mock_user,
            action="add",
            team=self.mock_team,
            member=self.mock_member,
            assigned_role="member",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.TEAM_MEMBER_ADDED)

        # Verify metadata contains expected team member fields
        metadata = call_args[2]
        self.assertIn("team_id", metadata)
        self.assertIn("member_id", metadata)
        self.assertIn("assigned_role", metadata)  # action_type
        self.assertIsInstance(call_args[2], dict)  # metadata
        self.assertEqual(call_args[3], self.mock_team)  # target_entity

        # Verify member role metadata
        metadata = call_args[2]
        self.assertEqual(metadata["assigned_role"], "member")

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_log_team_member_action_remove(self, mock_finalize_audit):
        """Test log_team_member_action for remove action."""
        # Call method
        self.logger.log_team_member_action(
            request=self.mock_request,
            user=self.mock_user,
            action="remove",
            team=self.mock_team,
            member=self.mock_member,
            reason="Performance issues",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.TEAM_MEMBER_REMOVED)

        # Verify metadata contains expected fields
        metadata = call_args[2]
        self.assertIn("team_id", metadata)
        self.assertIn("member_id", metadata)
        self.assertEqual(metadata["reason"], "Performance issues")

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_log_team_member_action_role_change(self, mock_finalize_audit):
        """Test log_team_member_action for role_change action."""
        # Call method
        self.logger.log_team_member_action(
            request=self.mock_request,
            user=self.mock_user,
            action="role_change",
            team=self.mock_team,
            member=self.mock_member,
            old_role="translator",
            new_role="reviewer",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.TEAM_MEMBER_ROLE_CHANGED)

        # Verify role change metadata
        metadata = call_args[2]
        self.assertIn("team_id", metadata)
        self.assertIn("member_id", metadata)
        self.assertEqual(metadata["old_role"], "translator")
        self.assertEqual(metadata["new_role"], "reviewer")

    @patch("apps.auditlog.loggers.base_logger.logger")
    def test_log_team_action_invalid_action(self, mock_logger):
        """Test log_team_action with invalid action."""
        # Invalid actions are logged as warnings, not raised as exceptions
        self.logger.log_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            team=self.mock_team,
        )
        # Verify warning was logged
        mock_logger.warning.assert_called_once()

    @patch("apps.auditlog.loggers.team_logger.logger")
    def test_log_team_member_action_invalid_action(self, mock_logger):
        """Test log_team_member_action with invalid action."""
        # Invalid actions are logged as warnings, not raised as exceptions
        self.logger.log_team_member_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            team=self.mock_team,
            member=self.mock_member,
        )
        # Verify warning was logged
        mock_logger.warning.assert_called_once()

    # Removed test_validation_methods_called - covered by comprehensive tests

    # Removed test_metadata_combination - covered by comprehensive tests

    # Removed test_team_member_metadata_combination - covered by comprehensive tests

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    def test_optional_parameters_handling(
        self, mock_crud_metadata, mock_team_metadata, mock_finalize_audit
    ):
        """Test handling of optional parameters in team actions."""
        # Setup mock
        mock_team_metadata.return_value = {"team_id": "team-123"}
        mock_crud_metadata.return_value = {"action_metadata": "update_data"}
        mock_crud_metadata.return_value = {"action_metadata": "update_data"}

        # Test with optional parameters
        self.logger.log_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            team=self.mock_team,
            updated_fields=["name", "description"],
            old_values={"name": "Old Team Name"},
            new_values={"name": "New Team Name"},
            reason="Rebranding",
        )

        # Verify optional parameters are included in metadata
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]
        self.assertEqual(metadata["old_values"], {"name": "Old Team Name"})
        self.assertEqual(metadata["new_values"], {"name": "New Team Name"})
        self.assertEqual(metadata["reason"], "Rebranding")

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    def test_team_member_action_with_additional_metadata(self, mock_finalize_audit):
        """Test team member action with additional metadata."""
        # Test with additional metadata
        self.logger.log_team_member_action(
            request=self.mock_request,
            user=self.mock_user,
            action="add",
            team=self.mock_team,
            member=self.mock_member,
            assigned_role="translator",
            start_date="2024-01-01",
            hourly_rate=25.00,
        )

        # Verify additional metadata is included
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]
        self.assertEqual(metadata["assigned_role"], "translator")
        self.assertEqual(metadata["start_date"], "2024-01-01")
        self.assertEqual(metadata["hourly_rate"], 25.00)

    @patch(
        "apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
    )
    @patch(
        "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    def test_team_action_with_team_settings(
        self, mock_crud_metadata, mock_team_metadata, mock_finalize_audit
    ):
        """Test team action with team settings metadata."""
        # Setup mock
        mock_team_metadata.return_value = {"team_id": "team-123"}
        mock_crud_metadata.return_value = {"action_metadata": "update_data"}

        # Test with team settings
        self.logger.log_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            team=self.mock_team,
            updated_fields=["settings"],
            team_settings={
                "auto_assign": True,
                "notification_enabled": False,
                "max_members": 10,
            },
        )

        # Verify team settings are included in metadata
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]
        expected_settings = {
            "auto_assign": True,
            "notification_enabled": False,
            "max_members": 10,
        }
        self.assertEqual(metadata["team_settings"], expected_settings)
