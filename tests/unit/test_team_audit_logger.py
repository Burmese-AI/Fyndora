"""Tests for TeamAuditLogger."""

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.team_logger import TeamAuditLogger


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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    @patch(
        "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
    )
    def test_log_team_action_create(
        self, mock_team_metadata, mock_finalize_audit
    ):
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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
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
        mock_team_metadata.assert_called_once_with(
            self.mock_team
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.TEAM_UPDATED)

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    def test_log_team_member_action_add(
        self, mock_finalize_audit
    ):
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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    def test_log_team_member_action_remove(
        self, mock_finalize_audit
    ):
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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    def test_log_team_member_action_role_change(
        self, mock_finalize_audit
    ):
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
        self.assertEqual(
            call_args[1], AuditActionType.TEAM_MEMBER_ROLE_CHANGED
        )

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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    def test_validation_methods_called(self, mock_finalize_audit):
        """Test that audit logging completes successfully."""
        # The validation is handled by the @safe_audit_log decorator
        with patch(
            "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
        ):
            self.logger.log_team_action(
                request=self.mock_request,
                user=self.mock_user,
                action="create",
                team=self.mock_team,
            )

        # Verify audit log was created
        mock_finalize_audit.assert_called_once()

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    def test_metadata_combination(self, mock_finalize_audit):
        """Test that metadata from different builders is properly combined."""
        with patch(
            "apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata"
        ) as mock_team_meta:
            with patch(
                "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ) as mock_crud_meta:
                # Setup return values
                mock_team_meta.return_value = {
                    "team_id": "team-123",
                    "team_name": "Test Team",
                }
                mock_crud_meta.return_value = {
                    "creator_id": "test-user-123",
                    "creation_timestamp": "2024-01-01T00:00:00Z",
                }

                self.logger.log_team_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    team=self.mock_team,
                )

                # Verify combined metadata
                call_args = mock_finalize_audit.call_args[0]
                metadata = call_args[2]
                self.assertEqual(metadata["team_id"], "team-123")
                self.assertEqual(metadata["team_name"], "Test Team")
                self.assertEqual(metadata["creator_id"], "test-user-123")
                self.assertEqual(metadata["creation_timestamp"], "2024-01-01T00:00:00Z")

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    def test_team_member_metadata_combination(self, mock_finalize_audit):
        """Test metadata combination in team member actions."""
        self.logger.log_team_member_action(
            request=self.mock_request,
            user=self.mock_user,
            action="add",
            team=self.mock_team,
            member=self.mock_member,
            assigned_role="translator",
        )

        # Verify combined metadata
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]
        self.assertIn("team_id", metadata)
        self.assertIn("member_id", metadata)
        self.assertIn("assigned_role", metadata)
        self.assertEqual(metadata["assigned_role"], "translator")

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    @patch("apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata")
    @patch(
        "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    def test_optional_parameters_handling(self, mock_crud_metadata, mock_team_metadata, mock_finalize_audit):
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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
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

    @patch("apps.auditlog.loggers.team_logger.TeamAuditLogger._finalize_and_create_audit")
    @patch("apps.auditlog.loggers.team_logger.EntityMetadataBuilder.build_team_metadata")
    @patch(
        "apps.auditlog.loggers.team_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    def test_team_action_with_team_settings(self, mock_crud_metadata, mock_team_metadata, mock_finalize_audit):
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
