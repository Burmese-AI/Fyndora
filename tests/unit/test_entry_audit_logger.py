"""Tests for EntryAuditLogger."""

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.entry_logger import EntryAuditLogger
from apps.entries.constants import EntryStatus


@patch("apps.auditlog.utils.safe_audit_log", lambda func: func)
class TestEntryAuditLogger(TestCase):
    """Test cases for EntryAuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = EntryAuditLogger()
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
        self.mock_request.POST = Mock()
        self.mock_request.POST.get = Mock(return_value=None)

        self.mock_entry = Mock()
        self.mock_entry.entry_id = "entry-123"
        self.mock_entry.description = "Test Entry"
        self.mock_entry.status = EntryStatus.PENDING
        self.mock_entry.workspace_id = "workspace-123"
        self.mock_entry.pk = "entry-123"
        self.mock_entry.__class__.__name__ = "Entry"
        self.mock_entry.__class__.__module__ = "apps.entries.models"
        self.mock_entry._meta = Mock()
        self.mock_entry._meta.pk = Mock()
        self.mock_entry._meta.pk.name = "pk"
        self.mock_entry.workspace = Mock()
        self.mock_entry.workspace.pk = "workspace-123"

    def test_get_supported_actions(self):
        """Test that get_supported_actions returns correct actions."""
        expected_actions = {
            "submit",
            "review",
            "approve",
            "reject",
            "flag",
            "unflag",
            "update",
            "delete",
        }
        self.assertEqual(set(self.logger.get_supported_actions()), expected_actions)

    def test_get_logger_name(self):
        """Test that get_logger_name returns correct name."""
        self.assertEqual(self.logger.get_logger_name(), "entry_logger")

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    @patch(
        "apps.auditlog.loggers.entry_logger.EntityMetadataBuilder.build_entry_metadata"
    )
    @patch(
        "apps.auditlog.loggers.entry_logger.WorkflowMetadataBuilder.build_workflow_metadata"
    )
    def test_log_entry_workflow_action_submit(
        self, mock_workflow_metadata, mock_entry_metadata, mock_finalize_audit
    ):
        """Test log_entry_workflow_action for submit action."""
        # Setup mocks
        mock_entry_metadata.return_value = {
            "entry_id": "entry-123",
            "entry_description": "Test Entry",
        }
        mock_workflow_metadata.return_value = {
            "workflow_stage": "submission",
            "notes": "Test submission",
        }

        # Call method
        self.logger.log_entry_workflow_action(
            request=self.mock_request,
            user=self.mock_user,
            action="submit",
            entry=self.mock_entry,
            notes="Test submission",
        )

        # Verify calls
        mock_entry_metadata.assert_called_once_with(self.mock_entry)
        mock_workflow_metadata.assert_called_once_with(
            self.mock_user,
            "submit",
            None,
            notes="Test submission",
            reason="",
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.ENTRY_SUBMITTED)  # action_type

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    @patch(
        "apps.auditlog.loggers.entry_logger.WorkflowMetadataBuilder.build_workflow_metadata"
    )
    @patch(
        "apps.auditlog.loggers.entry_logger.EntityMetadataBuilder.build_entry_metadata"
    )
    def test_log_entry_workflow_action_approve(
        self, mock_entry_metadata, mock_workflow_metadata, mock_finalize_audit
    ):
        """Test log_entry_workflow_action for approve action."""
        # Setup mocks
        mock_entry_metadata.return_value = {"entry_id": "entry-123"}
        mock_workflow_metadata.return_value = {"workflow_stage": "approval"}

        # Call method
        self.logger.log_entry_workflow_action(
            request=self.mock_request,
            user=self.mock_user,
            action="approve",
            entry=self.mock_entry,
            reason="Quality approved",
        )

        # Verify calls
        mock_entry_metadata.assert_called_once_with(self.mock_entry)
        mock_workflow_metadata.assert_called_once_with(
            self.mock_user,
            "approve",
            None,
            notes="",
            reason="Quality approved",
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.ENTRY_APPROVED)

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    @patch(
        "apps.auditlog.loggers.entry_logger.WorkflowMetadataBuilder.build_workflow_metadata"
    )
    @patch(
        "apps.auditlog.loggers.entry_logger.EntityMetadataBuilder.build_entry_metadata"
    )
    def test_log_entry_workflow_action_reject(
        self, mock_entry_metadata, mock_workflow_metadata, mock_finalize_audit
    ):
        """Test log_entry_workflow_action for reject action."""
        # Setup mocks
        mock_entry_metadata.return_value = {"entry_id": "entry-123"}
        mock_workflow_metadata.return_value = {"workflow_stage": "rejection"}

        # Call method
        self.logger.log_entry_workflow_action(
            request=self.mock_request,
            user=self.mock_user,
            action="reject",
            entry=self.mock_entry,
            reason="Needs revision",
        )

        # Verify calls
        mock_entry_metadata.assert_called_once_with(self.mock_entry)
        mock_workflow_metadata.assert_called_once_with(
            self.mock_user,
            "reject",
            None,
            notes="",
            reason="Needs revision",
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.ENTRY_REJECTED)

    @patch.object(EntryAuditLogger, "_handle_action_with_mapping")
    def test_log_entry_workflow_action_flag_unsupported(
        self, mock_handle_action
    ):
        """Test log_entry_workflow_action for unsupported flag action."""
        # Mock the method to return None (indicating unsupported action)
        mock_handle_action.return_value = None
        
        # Call method with unsupported action
        result = self.logger.log_entry_workflow_action(
            request=self.mock_request,
            user=self.mock_user,
            action="flag",
            entry=self.mock_entry,
            reason="Suspicious content",
        )

        # Verify _handle_action_with_mapping was called with correct parameters
        self.assertIsNone(result)
        mock_handle_action.assert_called_once()

    @patch.object(EntryAuditLogger, "_handle_action_with_mapping")
    def test_log_entry_workflow_action_unflag_unsupported(
        self, mock_handle_action
    ):
        """Test log_entry_workflow_action for unsupported unflag action."""
        # Mock the method to return None (indicating unsupported action)
        mock_handle_action.return_value = None
        
        # Call method with unsupported action
        result = self.logger.log_entry_workflow_action(
            request=self.mock_request,
            user=self.mock_user,
            action="unflag",
            entry=self.mock_entry,
        )

        # Verify _handle_action_with_mapping was called with correct parameters
        self.assertIsNone(result)
        mock_handle_action.assert_called_once()

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    @patch(
        "apps.auditlog.loggers.entry_logger.EntityMetadataBuilder.build_entry_metadata"
    )
    def test_log_entry_action_update(
        self, mock_entry_metadata, mock_finalize_audit
    ):
        """Test log_entry_action for update action."""
        # Setup mocks
        mock_entry_metadata.return_value = {"entry_id": "entry-123"}

        # Call method
        self.logger.log_entry_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            entry=self.mock_entry,
            updated_fields=["title", "content"],
        )

        # Verify calls
        mock_entry_metadata.assert_called_once_with(self.mock_entry)

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.ENTRY_UPDATED)

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    @patch(
        "apps.auditlog.loggers.entry_logger.EntityMetadataBuilder.build_entry_metadata"
    )
    def test_log_entry_action_delete(
        self, mock_entry_metadata, mock_finalize_audit
    ):
        """Test log_entry_action for delete action."""
        # Setup mocks
        mock_entry_metadata.return_value = {"entry_id": "entry-123"}

        # Call method
        self.logger.log_entry_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            entry=self.mock_entry,
            soft_delete=True,
        )

        # Verify calls
        mock_entry_metadata.assert_called_once_with(self.mock_entry)

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.ENTRY_DELETED)

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    def test_log_status_change(self, mock_finalize_audit):
        """Test log_status_change method."""
        # Call method
        self.logger.log_status_change(
            request=self.mock_request,
            user=self.mock_user,
            entity=self.mock_entry,
            old_status="draft",
            new_status="submitted",
            reason="Ready for review",
        )

        # Verify audit log creation
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.ENTRY_STATUS_CHANGED)  # action_type

        # Verify metadata contains status change information
        metadata = call_args[2]  # metadata is the third positional argument
        self.assertEqual(metadata["old_status"], "draft")
        self.assertEqual(metadata["new_status"], "submitted")
        self.assertEqual(metadata["reason"], "Ready for review")

    @patch.object(EntryAuditLogger, "_handle_action_with_mapping")
    def test_log_entry_workflow_action_invalid_action(self, mock_handle_action):
        """Test log_entry_workflow_action with invalid action logs warning and returns None."""
        # Mock the method to return None (indicating unsupported action)
        mock_handle_action.return_value = None
        
        result = self.logger.log_entry_workflow_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            entry=self.mock_entry,
        )

        self.assertIsNone(result)
        mock_handle_action.assert_called_once()

    @patch.object(EntryAuditLogger, "_handle_action_with_mapping")
    def test_log_entry_action_invalid_action(self, mock_handle_action):
        """Test log_entry_action with invalid action logs warning and returns None."""
        # Mock the method to return None (indicating unsupported action)
        mock_handle_action.return_value = None
        
        result = self.logger.log_entry_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            entry=self.mock_entry,
        )

        self.assertIsNone(result)
        mock_handle_action.assert_called_once()

    @patch.object(EntryAuditLogger, "_validate_request_and_user")
    def test_validation_methods_called(self, mock_validate):
        """Test that validation methods are called during logging."""
        with patch.object(EntryAuditLogger, "_finalize_and_create_audit"):
            self.logger.log_status_change(
                request=self.mock_request,
                user=self.mock_user,
                entity=self.mock_entry,
                old_status="draft",
                new_status="submitted",
            )

        # Verify validation method was called
        mock_validate.assert_called()

    @patch.object(EntryAuditLogger, "_finalize_and_create_audit")
    def test_metadata_combination(self, mock_finalize_audit):
        """Test that metadata from different builders is properly combined."""
        with patch(
            "apps.auditlog.loggers.entry_logger.EntityMetadataBuilder.build_entry_metadata"
        ) as mock_entry_meta:
            # Setup return values
            mock_entry_meta.return_value = {
                "entry_id": "entry-123",
                "entry_title": "Test",
            }

            self.logger.log_entry_action(
                request=self.mock_request,
                user=self.mock_user,
                action="update",
                entry=self.mock_entry,
                updated_fields=["title"],
            )

            # Verify combined metadata
            call_args = mock_finalize_audit.call_args[0]
            metadata = call_args[2]  # metadata is the third positional argument
            self.assertEqual(metadata["entry_id"], "entry-123")
            self.assertEqual(metadata["entry_title"], "Test")
            self.assertEqual(metadata["updated_fields"], ["title"])
