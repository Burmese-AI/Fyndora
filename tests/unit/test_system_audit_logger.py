"""Tests for SystemAuditLogger."""

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.system_logger import SystemAuditLogger


class TestSystemAuditLogger(TestCase):
    """Test cases for SystemAuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = SystemAuditLogger()
        self.mock_user = Mock(spec=User)
        self.mock_user.user_id = "test-user-123"
        self.mock_user.email = "test@example.com"
        self.mock_user.is_authenticated = True
        self.mock_user.pk = "test-user-123"

        self.mock_request = Mock(spec=HttpRequest)
        self.mock_request.method = "POST"
        self.mock_request.path = "/test/"
        self.mock_request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "Test Browser",
        }

        self.mock_target_user = Mock(spec=User)
        self.mock_target_user.user_id = "target-user-456"
        self.mock_target_user.email = "target@example.com"
        self.mock_target_user.is_authenticated = True
        self.mock_target_user.pk = "target-user-456"
        self.mock_target_user.workspace = None
        self.mock_target_user.__class__.__module__ = "django.contrib.auth.models"
        self.mock_target_user.__class__.__name__ = "User"

        self.mock_file = Mock()
        self.mock_file.name = "test_file.txt"
        self.mock_file.size = 1024
        self.mock_file.pk = "file-123"
        self.mock_file.__class__.__module__ = "apps.attachments.models"
        self.mock_file.__class__.__name__ = "File"
        self.mock_file.content_type = "application/pdf"

    def test_get_supported_actions(self):
        """Test that logger returns correct supported actions."""
        expected_actions = {
            "permission_grant",
            "permission_revoke",
            "permission_change",
            "bulk_operation",
            "data_export",
            "file_upload",
            "file_download",
            "file_delete",
            "operation_failure",
        }
        self.assertEqual(set(self.logger.get_supported_actions()), expected_actions)

    def test_get_logger_name(self):
        """Test that logger returns correct name."""
        self.assertEqual(self.logger.get_logger_name(), "system_logger")

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_log_permission_change_granted(self, mock_finalize_audit):
        """Test log_permission_change for permission granted."""
        # Call method
        self.logger.log_permission_change(
            request=self.mock_request,
            user=self.mock_user,
            target_user=self.mock_target_user,
            permission_type="read",
            action="grant",
        )

        # Verify calls
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments (positional: user, action_type, metadata, target_entity, workspace)
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.PERMISSION_GRANTED
        )  # action_type
        self.assertEqual(call_args[3], self.mock_target_user)  # target_entity

        # Verify metadata contains permission details
        metadata = call_args[2]  # metadata
        self.assertEqual(metadata["target_user_id"], "target-user-456")
        self.assertEqual(metadata["target_user_email"], "target@example.com")
        self.assertEqual(metadata["permission_type"], "read")

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_log_permission_change_revoked(self, mock_finalize_audit):
        """Test log_permission_change for permission revoked."""

        # Call method
        self.logger.log_permission_change(
            request=self.mock_request,
            user=self.mock_user,
            target_user=self.mock_target_user,
            permission_type="write",
            action="revoke",
            resource_type="organization",
            resource_id="org-456",
            reason="Security policy update",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.PERMISSION_REVOKED)

        # Verify reason is included in metadata
        metadata = call_args[2]
        self.assertEqual(metadata["revoke_reason"], "Security policy update")

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_log_permission_change_changed(self, mock_finalize_audit):
        """Test log_permission_change for permission changed."""

        # Call method
        self.logger.log_permission_change(
            request=self.mock_request,
            user=self.mock_user,
            target_user=self.mock_target_user,
            permission_type="admin",
            action="change",
            resource_type="team",
            resource_id="team-789",
            previous_permissions=["member"],
            new_permissions=["admin"],
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.PERMISSION_CHANGED)

        # Verify permission change details in metadata
        metadata = call_args[2]
        self.assertEqual(metadata["previous_permissions"], ["member"])
        self.assertEqual(metadata["new_permissions"], ["admin"])

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_log_data_export(self, mock_finalize_audit):
        """Test log_data_export method."""

        # Call method
        self.logger.log_data_export(
            request=self.mock_request,
            user=self.mock_user,
            export_type="user_data",
            data_scope="organization",
            scope_id="org-123",
            file_format="csv",
            record_count=1500,
            file_size=2048,
        )

        # Verify calls
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.DATA_EXPORTED)

        # Verify export metadata
        metadata = call_args[2]
        self.assertEqual(metadata["export_type"], "user_data")
        self.assertEqual(metadata["data_scope"], "organization")
        self.assertEqual(metadata["scope_id"], "org-123")
        self.assertEqual(metadata["file_format"], "csv")
        self.assertEqual(metadata["record_count"], 1500)
        self.assertEqual(metadata["file_size"], 2048)

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_log_bulk_operation(self, mock_finalize_audit):
        """Test log_bulk_operation method."""

        # Call method
        affected_entities = [Mock(pk=i) for i in range(1, 251)]
        self.logger.log_bulk_operation(
            request=self.mock_request,
            user=self.mock_user,
            operation_type="bulk_update",
            affected_entities=affected_entities,
            target_entity="entries",
            affected_count=250,
            success_count=245,
            failure_count=5,
            criteria={"status": "draft", "workspace_id": "workspace-123"},
            changes={"status": "submitted"},
        )

        # Verify calls
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.BULK_OPERATION)

        # Verify bulk operation metadata
        metadata = call_args[2]
        self.assertEqual(metadata["operation_type"], "bulk_update")
        self.assertEqual(metadata["target_entity"], "entries")
        self.assertEqual(metadata["affected_count"], 250)
        self.assertEqual(metadata["success_count"], 245)
        self.assertEqual(metadata["failure_count"], 5)
        self.assertEqual(
            metadata["criteria"], {"status": "draft", "workspace_id": "workspace-123"}
        )
        self.assertEqual(metadata["changes"], {"status": "submitted"})

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.metadata_builders.FileMetadataBuilder.build_file_metadata"
    )
    def test_log_file_operation_upload(self, mock_file_metadata, mock_finalize_audit):
        """Test log_file_operation for file upload."""
        # Setup mocks
        mock_file_metadata.return_value = {
            "file_name": "test_file.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
        }

        # Call method
        self.logger.log_file_operation(
            request=self.mock_request,
            user=self.mock_user,
            action="upload",
            file_obj=self.mock_file,
            file_category="document",
            target_entity="entry",
            target_id="entry-123",
        )

        # Verify calls
        mock_file_metadata.assert_called_once_with(
            self.mock_file,
            "upload",
            self.mock_user,
            file_category="document",
            target_entity="entry",
            target_id="entry-123",
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.FILE_UPLOADED)

        # Verify file operation metadata
        metadata = call_args[2]
        self.assertEqual(metadata["target_entity"], "entry")
        self.assertEqual(metadata["target_id"], "entry-123")

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.metadata_builders.FileMetadataBuilder.build_file_metadata"
    )
    def test_log_file_operation_download(self, mock_file_metadata, mock_finalize_audit):
        """Test log_file_operation for file download."""
        # Setup mocks
        mock_file_metadata.return_value = {"file_name": "test_file.pdf"}

        # Call method
        self.logger.log_file_operation(
            request=self.mock_request,
            user=self.mock_user,
            action="download",
            file_obj=self.mock_file,
            file_category="attachment",
        )

        # Verify calls
        mock_file_metadata.assert_called_once_with(
            self.mock_file, "download", self.mock_user, file_category="attachment"
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.FILE_DOWNLOADED)

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.metadata_builders.FileMetadataBuilder.build_file_metadata"
    )
    def test_log_file_operation_delete(self, mock_file_metadata, mock_finalize_audit):
        """Test log_file_operation for file delete."""
        # Setup mocks
        mock_file_metadata.return_value = {"file_name": "test_file.pdf"}

        # Call method
        self.logger.log_file_operation(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            file_obj=self.mock_file,
            file_category="temporary",
            reason="Cleanup expired files",
        )

        # Verify calls
        mock_file_metadata.assert_called_once_with(
            self.mock_file,
            "delete",
            self.mock_user,
            file_category="temporary",
            reason="Cleanup expired files",
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.FILE_DELETED)

        # Verify reason is included in metadata
        metadata = call_args[2]
        self.assertEqual(metadata["reason"], "Cleanup expired files")

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_log_operation_failure(self, mock_finalize_audit):
        """Test log_operation_failure method."""

        # Call method
        self.logger.log_operation_failure(
            request=self.mock_request,
            user=self.mock_user,
            operation="data_import",
            error_details={
                "error_message": "Invalid file format",
                "error_code": "INVALID_FORMAT",
                "error_type": "validation_error",
                "affected_component": "data_importer",
                "severity": "high",
            },
            affected_entity="entries",
            entity_id="import-batch-456",
        )

        # Verify calls
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[1], AuditActionType.OPERATION_FAILED)

        # Verify failure metadata
        metadata = call_args[2]
        self.assertEqual(metadata["operation"], "data_import")
        self.assertEqual(metadata["error_code"], "INVALID_FORMAT")
        self.assertEqual(metadata["error_message"], "Invalid file format")
        self.assertEqual(metadata["error_type"], "validation_error")
        self.assertEqual(metadata["affected_component"], "data_importer")
        self.assertEqual(metadata["severity"], "high")
        # These come from **kwargs
        self.assertEqual(metadata["affected_entity"], "entries")
        self.assertEqual(metadata["entity_id"], "import-batch-456")

    def test_log_permission_change_invalid_action(self):
        """Test log_permission_change with invalid action logs warning and returns early."""
        with self.assertLogs(
            "apps.auditlog.loggers.system_logger", level="WARNING"
        ) as log:
            self.logger.log_permission_change(
                request=self.mock_request,
                user=self.mock_user,
                target_user=self.mock_target_user,
                permission_type="read",
                action="invalid_action",
                resource_type="workspace",
                resource_id="workspace-123",
            )

        self.assertIn("Unknown permission action: invalid_action", log.output[0])

    def test_log_file_operation_invalid_operation(self):
        """Test log_file_operation with invalid operation logs warning and returns early."""
        with self.assertLogs(
            "apps.auditlog.loggers.system_logger", level="WARNING"
        ) as log:
            self.logger.log_file_operation(
                request=self.mock_request,
                user=self.mock_user,
                action="invalid_operation",
                file_obj=self.mock_file,
            )

        self.assertIn("Unknown file operation action: invalid_operation", log.output[0])

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._validate_request_and_user"
    )
    def test_validation_methods_called(self, mock_validate):
        """Test that validation method is called during logging."""
        with patch(
            "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
        ):
            self.logger.log_permission_change(
                request=self.mock_request,
                user=self.mock_user,
                target_user=self.mock_target_user,
                permission_type="read",
                action="grant",
            )

        # Verify validation method was called
        mock_validate.assert_called_once_with(self.mock_request, self.mock_user)

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_metadata_combination_complex(self, mock_finalize_audit):
        """Test complex metadata combination in bulk operation."""
        affected_entities = [Mock(pk=i) for i in range(1, 101)]
        self.logger.log_bulk_operation(
            request=self.mock_request,
            user=self.mock_user,
            operation_type="bulk_delete",
            affected_entities=affected_entities,
            target_entity="entries",
            affected_count=100,
            success_count=95,
            failure_count=5,
            criteria={"status": "draft", "created_before": "2023-01-01"},
            changes={"deleted": True},
            execution_time=15.5,
        )

        # Verify combined metadata
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]
        self.assertEqual(metadata["operation_type"], "bulk_delete")
        self.assertEqual(metadata["execution_time"], 15.5)
        self.assertEqual(
            metadata["criteria"],
            {"status": "draft", "created_before": "2023-01-01"},
        )
        self.assertEqual(metadata["affected_count"], 100)

    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger._finalize_and_create_audit"
    )
    def test_optional_parameters_handling(self, mock_finalize_audit):
        """Test handling of optional parameters in various methods."""
        # Test minimal parameters for data export
        self.logger.log_data_export(
            request=self.mock_request,
            user=self.mock_user,
            export_type="basic_export",
            data_scope="workspace",
            scope_id="workspace-123",
        )

        # Verify call was successful
        self.assertTrue(mock_finalize_audit.called)

        # Test with all optional parameters
        self.logger.log_data_export(
            request=self.mock_request,
            user=self.mock_user,
            export_type="detailed_export",
            data_scope="organization",
            scope_id="org-456",
            file_format="json",
            record_count=5000,
            file_size=10240,
            filters={"date_range": "last_month"},
            columns=["id", "title", "status"],
        )

        # Verify second call was successful
        self.assertEqual(mock_finalize_audit.call_count, 2)
