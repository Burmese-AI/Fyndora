"""Tests for WorkspaceAuditLogger."""

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.workspace_logger import WorkspaceAuditLogger


class TestWorkspaceAuditLogger(TestCase):
    """Test cases for WorkspaceAuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = WorkspaceAuditLogger()
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

        self.mock_workspace = Mock()
        self.mock_workspace.workspace_id = "workspace-123"
        self.mock_workspace.title = "Test Workspace"
        self.mock_workspace.status = "active"
        self.mock_workspace.description = "Test workspace description"
        self.mock_workspace.pk = "workspace-123"
        self.mock_workspace.__class__.__name__ = "Workspace"
        self.mock_workspace.__class__.__module__ = "apps.workspaces.models"
        self.mock_workspace._meta = Mock()
        self.mock_workspace._meta.pk = Mock()
        self.mock_workspace._meta.pk.name = "pk"

        self.mock_team = Mock()
        self.mock_team.team_id = "team-456"
        self.mock_team.name = "Test Team"
        self.mock_team.role = "translator"
        self.mock_team.pk = "team-456"
        self.mock_team.__class__.__name__ = "Team"
        self.mock_team.__class__.__module__ = "apps.teams.models"
        self.mock_team._meta = Mock()
        self.mock_team._meta.pk = Mock()
        self.mock_team._meta.pk.name = "pk"
        self.mock_team.workspace = Mock()
        self.mock_team.workspace.pk = "workspace-123"

        self.mock_exchange_rate = Mock()
        self.mock_exchange_rate.id = "rate-789"
        self.mock_exchange_rate.from_currency = "USD"
        self.mock_exchange_rate.to_currency = "EUR"
        self.mock_exchange_rate.rate = 0.85
        self.mock_exchange_rate.pk = "rate-789"
        self.mock_exchange_rate.__class__.__name__ = "ExchangeRate"
        self.mock_exchange_rate.__class__.__module__ = "apps.currencies.models"
        self.mock_exchange_rate._meta = Mock()
        self.mock_exchange_rate._meta.pk = Mock()
        self.mock_exchange_rate._meta.pk.name = "pk"
        self.mock_exchange_rate.workspace = Mock()
        self.mock_exchange_rate.workspace.pk = "workspace-123"

    def test_get_supported_actions(self):
        """Test that get_supported_actions returns correct actions."""
        expected_actions = {
            "create",
            "update",
            "delete",
            "archive",
            "activate",
            "close",
            "status_change",
        }
        self.assertEqual(set(self.logger.get_supported_actions()), expected_actions)

    def test_get_logger_name(self):
        """Test that get_logger_name returns correct name."""
        self.assertEqual(self.logger.get_logger_name(), "workspace_logger")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_create(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for create action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {
            "workspace_id": "workspace-123",
            "workspace_title": "Test Workspace",
        }

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            workspace=self.mock_workspace,
        )

        # Verify calls
        mock_workspace_metadata.assert_called_once_with(self.mock_workspace)
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_CREATED)  # action_type
        # call_args[2] is metadata, call_args[3] is workspace, call_args[4] is workspace

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_action_update(
        self, mock_finalize_audit
    ):
        """Test log_workspace_action for update action."""
        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            workspace=self.mock_workspace,
            updated_fields=["title"],
            old_title="Old Title",
            new_title="New Title",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_UPDATED)  # action_type

        # Verify title change metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_title"], "Old Title")
        self.assertEqual(metadata["new_title"], "New Title")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_action_delete(
        self, mock_finalize_audit
    ):
        """Test log_workspace_action for delete action."""
        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            workspace=self.mock_workspace,
            soft_delete=True,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_DELETED)  # action_type

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_archive(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for archive action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="archive",
            workspace=self.mock_workspace,
            reason="Project completed",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_ARCHIVED)  # action_type

        # Verify reason is included in metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["reason"], "Project completed")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_activate(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for activate action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="activate",
            workspace=self.mock_workspace,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_ACTIVATED)  # action_type

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_close(self, mock_workspace_metadata, mock_finalize_audit):
        """Test log_workspace_action for close action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="close",
            workspace=self.mock_workspace,
            reason="Budget exhausted",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_CLOSED)  # action_type

        # Verify reason is included in metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["reason"], "Budget exhausted")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_status_change(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for status_change action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="status_change",
            workspace=self.mock_workspace,
            old_status="draft",
            new_status="active",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_STATUS_CHANGED)  # action_type

        # Verify status change metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_status"], "draft")
        self.assertEqual(metadata["new_status"], "active")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_team_action_add(
        self, mock_finalize_audit
    ):
        """Test log_workspace_team_action for add action."""
        # Call method
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="add",
            workspace=self.mock_workspace,
            team=self.mock_team,
            role="translator",
        )

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_TEAM_ADDED)  # action_type

        # Verify team role metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["role"], "translator")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_team_action_remove(
        self, mock_finalize_audit
    ):
        """Test log_workspace_team_action for remove action."""
        # Call method
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="remove",
            workspace=self.mock_workspace,
            team=self.mock_team,
            reason="Team reassignment",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_TEAM_REMOVED)  # action_type

        # Verify reason is included in metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["reason"], "Team reassignment")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_team_action_remittance_rate_update(
        self, mock_finalize_audit
    ):
        """Test log_workspace_team_action for remittance_rate_update action."""
        # Call method
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="remittance_rate_update",
            workspace=self.mock_workspace,
            team=self.mock_team,
            old_rate=0.15,
            new_rate=0.18,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1],
            AuditActionType.WORKSPACE_TEAM_REMITTANCE_RATE_UPDATED,
        )  # action_type

        # Verify rate change metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_rate"], 0.15)
        self.assertEqual(metadata["new_rate"], 0.18)

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_exchange_rate_action_create(
        self, mock_finalize_audit
    ):
        """Test log_workspace_exchange_rate_action for create action."""
        # Call method
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_EXCHANGE_RATE_CREATED
        )  # action_type

        # Verify exchange rate metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["exchange_rate_id"], "rate-789")
        self.assertEqual(metadata["from_currency"], "USD")
        self.assertEqual(metadata["to_currency"], "EUR")
        self.assertEqual(metadata["rate"], "0.85")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_exchange_rate_action_update(
        self, mock_finalize_audit
    ):
        """Test log_workspace_exchange_rate_action for update action."""
        # Call method
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
            updated_fields=["rate"],
            old_rate=0.80,
            new_rate=0.85,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_EXCHANGE_RATE_UPDATED
        )  # action_type

        # Verify rate change metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_rate"], 0.80)
        self.assertEqual(metadata["new_rate"], 0.85)

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_exchange_rate_action_delete(
        self, mock_finalize_audit
    ):
        """Test log_workspace_exchange_rate_action for delete action."""
        # Call method
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_EXCHANGE_RATE_DELETED
        )  # action_type

    @patch("apps.auditlog.loggers.base_logger.logger")
    def test_log_workspace_action_invalid_action(self, mock_logger):
        """Test log_workspace_action with invalid action logs warning."""
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            workspace=self.mock_workspace,
        )

        mock_logger.warning.assert_called_once_with("Unknown action: invalid_action")

    @patch("apps.auditlog.loggers.workspace_logger.logger")
    def test_log_workspace_team_action_invalid_action(self, mock_logger):
        """Test log_workspace_team_action with invalid action logs warning."""
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            workspace=self.mock_workspace,
            team=self.mock_team,
        )

        mock_logger.warning.assert_called_once_with("Unknown workspace team action: invalid_action")

    @patch("apps.auditlog.loggers.workspace_logger.logger")
    def test_log_workspace_exchange_rate_action_invalid_action(self, mock_logger):
        """Test log_workspace_exchange_rate_action with invalid action logs warning."""
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
        )

        mock_logger.warning.assert_called_once_with("Unknown workspace exchange rate action: invalid_action")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_validation_methods_called(self, mock_finalize_audit):
        """Test that workspace action logging works correctly."""
        with patch(
            "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
        ):
            self.logger.log_workspace_action(
                request=self.mock_request,
                user=self.mock_user,
                action="activate",
                workspace=self.mock_workspace,
            )

        # Verify audit log creation
        mock_finalize_audit.assert_called_once()

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_metadata_combination(self, mock_finalize_audit):
        """Test that metadata from different builders is properly combined."""
        with patch(
            "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
        ) as mock_workspace_meta:
            with patch(
                "apps.auditlog.loggers.workspace_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ) as mock_crud_meta:
                # Setup return values
                mock_workspace_meta.return_value = {
                    "workspace_id": "workspace-123",
                    "workspace_title": "Test Workspace",
                }
                mock_crud_meta.return_value = {
                    "creator_id": "user-123",
                    "creation_timestamp": "2024-01-01T00:00:00Z",
                }

                self.logger.log_workspace_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    workspace=self.mock_workspace,
                )

                # Verify combined metadata
                call_args = mock_finalize_audit.call_args[0]
                user, action_type, metadata, target_entity, workspace = call_args
                self.assertEqual(metadata["workspace_id"], "workspace-123")
                self.assertEqual(metadata["workspace_title"], "Test Workspace")
                self.assertEqual(metadata["creator_id"], "user-123")
                self.assertEqual(metadata["creation_timestamp"], "2024-01-01T00:00:00Z")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_exchange_rate_metadata_extraction(self, mock_finalize_audit):
        """Test that exchange rate metadata is properly extracted."""
        with patch(
            "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
        ):
            with patch(
                "apps.auditlog.loggers.workspace_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ):
                # Test with exchange rate that has additional attributes
                self.mock_exchange_rate.effective_date = "2024-01-01"
                self.mock_exchange_rate.created_by = "admin-user"

                self.logger.log_workspace_exchange_rate_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    workspace=self.mock_workspace,
                    exchange_rate=self.mock_exchange_rate,
                )

                # Verify exchange rate metadata extraction
                call_args = mock_finalize_audit.call_args[0]
                user, action_type, metadata, target_entity = call_args
                self.assertEqual(metadata["exchange_rate_id"], "rate-789")
                self.assertEqual(metadata["from_currency"], "USD")
                self.assertEqual(metadata["to_currency"], "EUR")
                self.assertEqual(metadata["rate"], "0.85")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_team_action_metadata_combination(self, mock_finalize_audit):
        """Test metadata combination in workspace team actions."""
        with patch(
            "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
        ) as mock_workspace_meta:
            with patch(
                "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_team_metadata"
            ) as mock_team_meta:
                # Setup return values
                mock_workspace_meta.return_value = {
                    "workspace_id": "workspace-123",
                    "workspace_title": "Test Workspace",
                }
                mock_team_meta.return_value = {
                    "team_id": "team-456",
                    "team_name": "Test Team",
                }

                self.logger.log_workspace_team_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="add",
                    workspace=self.mock_workspace,
                    team=self.mock_team,
                    role="reviewer",
                    permissions=["read", "review"],
                )

                # Verify combined metadata
                call_args = mock_finalize_audit.call_args[0]
                user, action_type, metadata, target_entity, workspace = call_args
                self.assertEqual(metadata["workspace_id"], "workspace-123")
                self.assertEqual(metadata["team_id"], "team-456")
                self.assertEqual(metadata["role"], "reviewer")
                self.assertEqual(metadata["permissions"], ["read", "review"])
