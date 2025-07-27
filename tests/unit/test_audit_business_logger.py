"""
Unit tests for audit business logger.

Following the test plan: AuditLog App (apps.auditlog)
- Business logger tests
- Manual audit logging tests
- Request metadata extraction tests
- Permission change logging tests
- Data export logging tests
- Bulk operation logging tests
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.auditlog.constants import AuditActionType
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestBusinessAuditLoggerValidation(TestCase):
    """Test BusinessAuditLogger validation methods."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    def test_validate_request_and_user_valid(self):
        """Test validation with valid authenticated user."""
        request = self.factory.post("/test/")
        request.user = self.user

        # Should not raise exception
        try:
            BusinessAuditLogger._validate_request_and_user(request, self.user)
        except ValueError:
            self.fail("_validate_request_and_user raised ValueError unexpectedly")

    def test_validate_request_and_user_none_user(self):
        """Test validation with None user."""
        request = self.factory.post("/test/")

        with self.assertRaises(ValueError) as context:
            BusinessAuditLogger._validate_request_and_user(request, None)

        self.assertIn("Valid authenticated user required", str(context.exception))

    def test_validate_request_and_user_unauthenticated(self):
        """Test validation with unauthenticated user."""
        request = self.factory.post("/test/")
        user = Mock()
        user.is_authenticated = False

        with self.assertRaises(ValueError) as context:
            BusinessAuditLogger._validate_request_and_user(request, user)

        self.assertIn("Valid authenticated user required", str(context.exception))

    def test_extract_request_metadata_with_request(self):
        """Test extracting metadata from valid request."""
        request = self.factory.post("/test/path/")
        request.META = {
            "REMOTE_ADDR": "192.168.1.100",
            "HTTP_USER_AGENT": "Mozilla/5.0 Test Browser",
        }
        request.session = Mock()
        request.session.session_key = "test_session_key"

        metadata = BusinessAuditLogger._extract_request_metadata(request)

        self.assertEqual(metadata["ip_address"], "192.168.1.100")
        self.assertEqual(metadata["user_agent"], "Mozilla/5.0 Test Browser")
        self.assertEqual(metadata["http_method"], "POST")
        self.assertEqual(metadata["request_path"], "/test/path/")
        self.assertEqual(metadata["session_key"], "test_session_key")
        self.assertEqual(metadata["source"], "web_request")

    def test_extract_request_metadata_none_request(self):
        """Test extracting metadata from None request."""
        metadata = BusinessAuditLogger._extract_request_metadata(None)

        self.assertEqual(metadata["ip_address"], "unknown")
        self.assertEqual(metadata["user_agent"], "unknown")
        self.assertEqual(metadata["http_method"], "unknown")
        self.assertEqual(metadata["request_path"], "unknown")
        self.assertIsNone(metadata["session_key"])
        self.assertEqual(metadata["source"], "service_call")

    def test_extract_request_metadata_missing_meta(self):
        """Test extracting metadata from request with missing META fields."""
        request = self.factory.get("/test/")
        request.META = {}  # Empty META
        request.session = Mock()
        request.session.session_key = None

        metadata = BusinessAuditLogger._extract_request_metadata(request)

        self.assertEqual(metadata["ip_address"], "unknown")
        self.assertEqual(metadata["user_agent"], "unknown")
        self.assertEqual(metadata["http_method"], "GET")
        self.assertEqual(metadata["request_path"], "/test/")
        self.assertIsNone(metadata["session_key"])
        self.assertEqual(metadata["source"], "web_request")


@pytest.mark.unit
class TestBusinessAuditLoggerEntryActions(TestCase):
    """Test BusinessAuditLogger entry action logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_entry_action_submit(self, mock_audit_create):
        """Test logging entry submit action."""
        request = self.factory.post("/entries/submit/")
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="submit", request=request
        )

        # Verify audit_create was called
        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["user"], self.user)
        self.assertEqual(call_args[1]["action_type"], AuditActionType.ENTRY_SUBMITTED)
        self.assertEqual(call_args[1]["target_entity"], self.entry)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["action"], "submit")
        self.assertTrue(metadata["manual_logging"])
        self.assertEqual(metadata["entry_id"], str(self.entry.entry_id))

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_entry_action_approve_with_notes(self, mock_audit_create):
        """Test logging entry approve action with approval notes."""
        request = self.factory.post(
            "/entries/approve/", {"notes": "All requirements met", "level": "manager"}
        )
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="approve", request=request
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["action_type"], AuditActionType.ENTRY_APPROVED)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["action"], "approve")
        self.assertEqual(metadata["approver_id"], str(self.user.user_id))
        self.assertEqual(metadata["approver_email"], self.user.email)
        self.assertEqual(metadata["approval_notes"], "All requirements met")
        self.assertEqual(metadata["approval_level"], "manager")
        self.assertIn("approval_timestamp", metadata)

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_entry_action_reject_with_reason(self, mock_audit_create):
        """Test logging entry reject action with rejection reason."""
        request = self.factory.post(
            "/entries/reject/",
            {
                "reason": "Missing documentation",
                "notes": "Please provide receipts",
                "can_resubmit": "true",
            },
        )
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="reject", request=request
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["action_type"], AuditActionType.ENTRY_REJECTED)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["action"], "reject")
        self.assertEqual(metadata["rejector_id"], str(self.user.user_id))
        self.assertEqual(metadata["rejection_reason"], "Missing documentation")
        self.assertEqual(metadata["rejection_notes"], "Please provide receipts")
        self.assertEqual(metadata["can_resubmit"], "true")
        self.assertIn("rejection_timestamp", metadata)

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_entry_action_flag_with_severity(self, mock_audit_create):
        """Test logging entry flag action with severity."""
        request = self.factory.post(
            "/entries/flag/",
            {
                "reason": "Suspicious amount",
                "notes": "Requires investigation",
                "severity": "high",
            },
        )
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="flag", request=request
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["action_type"], AuditActionType.ENTRY_FLAGGED)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["action"], "flag")
        self.assertEqual(metadata["flag_reason"], "Suspicious amount")
        self.assertEqual(metadata["flag_notes"], "Requires investigation")
        self.assertEqual(metadata["flag_severity"], "high")

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_entry_action_without_request(self, mock_audit_create):
        """Test logging entry action without request (service call)."""
        BusinessAuditLogger.log_entry_action(
            user=self.user,
            entry=self.entry,
            action="approve",
            request=None,
            notes="Service approval",
            level="automatic",
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["source"], "service_call")
        self.assertEqual(metadata["approval_notes"], "Service approval")
        self.assertEqual(metadata["approval_level"], "automatic")

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.logger")
    def test_log_entry_action_unknown_action(self, mock_logger):
        """Test logging unknown entry action."""
        request = self.factory.post("/entries/unknown/")
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="unknown_action", request=request
        )

        # Should log warning and return early
        mock_logger.warning.assert_called_once()
        self.assertIn(
            "Unknown entry workflow action", mock_logger.warning.call_args[0][0]
        )


@pytest.mark.unit
class TestBusinessAuditLoggerPermissionChanges(TestCase):
    """Test BusinessAuditLogger permission change logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.target_user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create_security_event")
    def test_log_permission_change_grant(self, mock_audit_create):
        """Test logging permission grant."""
        request = self.factory.post(
            "/permissions/grant/",
            {
                "reason": "Promotion to manager",
                "effective_date": "2024-01-01T00:00:00Z",
            },
        )
        request.user = self.user

        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=self.target_user,
            permission="admin_access",
            action="grant",
            request=request,
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["user"], self.user)
        self.assertEqual(
            call_args[1]["action_type"], AuditActionType.PERMISSION_GRANTED
        )
        self.assertEqual(call_args[1]["target_entity"], self.target_user)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["target_user_id"], str(self.target_user.user_id))
        self.assertEqual(metadata["permission"], "admin_access")
        self.assertEqual(metadata["action"], "grant")
        self.assertEqual(metadata["change_reason"], "Promotion to manager")

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create_security_event")
    def test_log_permission_change_revoke(self, mock_audit_create):
        """Test logging permission revoke."""
        request = self.factory.post("/permissions/revoke/", {"reason": "Role change"})
        request.user = self.user

        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=self.target_user,
            permission="admin_access",
            action="revoke",
            request=request,
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(
            call_args[1]["action_type"], AuditActionType.PERMISSION_REVOKED
        )

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["action"], "revoke")
        self.assertEqual(metadata["change_reason"], "Role change")

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.logger")
    def test_log_permission_change_unknown_action(self, mock_logger):
        """Test logging unknown permission action."""
        request = self.factory.post("/permissions/unknown/")
        request.user = self.user

        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=self.target_user,
            permission="admin_access",
            action="unknown",
            request=request,
        )

        mock_logger.warning.assert_called_once()
        self.assertIn("Unknown permission action", mock_logger.warning.call_args[0][0])


@pytest.mark.unit
class TestBusinessAuditLoggerDataExport(TestCase):
    """Test BusinessAuditLogger data export logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_data_export_with_request(self, mock_audit_create):
        """Test logging data export with request."""
        request = self.factory.get("/export/?format=xlsx")
        request.user = self.user
        request.POST = {"reason": "Monthly report"}

        filters = {"date_range": "2024-01-01 to 2024-01-31", "status": "approved"}

        BusinessAuditLogger.log_data_export(
            user=self.user,
            export_type="entries",
            filters=filters,
            result_count=150,
            request=request,
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["user"], self.user)
        self.assertEqual(call_args[1]["action_type"], AuditActionType.DATA_EXPORTED)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["export_type"], "entries")
        self.assertEqual(metadata["export_filters"], filters)
        self.assertEqual(metadata["result_count"], 150)
        self.assertEqual(metadata["export_format"], "xlsx")
        self.assertEqual(metadata["export_reason"], "Monthly report")
        self.assertEqual(metadata["file_size_estimate"], "15000B")
        self.assertTrue(metadata["manual_logging"])

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_data_export_without_request(self, mock_audit_create):
        """Test logging data export without request (service call)."""
        filters = {"workspace_id": 123}

        BusinessAuditLogger.log_data_export(
            user=self.user,
            export_type="audit_logs",
            filters=filters,
            result_count=50,
            request=None,
            format="csv",
            reason="compliance_audit",
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["export_format"], "csv")
        self.assertEqual(metadata["export_reason"], "compliance_audit")
        self.assertEqual(metadata["source"], "service_call")


@pytest.mark.unit
class TestBusinessAuditLoggerBulkOperations(TestCase):
    """Test BusinessAuditLogger bulk operation logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    @patch("apps.auditlog.business_logger.AuditConfig.BULK_OPERATION_THRESHOLD", 10)
    def test_log_bulk_operation_small_batch(self, mock_audit_create):
        """Test logging small bulk operation (under threshold)."""
        request = self.factory.post("/bulk/approve/")
        request.user = self.user

        # Create 5 entries (under threshold)
        entries = [EntryFactory() for _ in range(5)]

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_approve",
            affected_objects=entries,
            request=request,
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["action_type"], AuditActionType.BULK_OPERATION)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["operation_type"], "bulk_approve")
        self.assertEqual(metadata["total_objects"], 5)
        self.assertEqual(len(metadata["object_ids"]), 5)
        # All object IDs should be included for small operations
        expected_ids = [str(entry.entry_id) for entry in entries]
        self.assertEqual(metadata["object_ids"], expected_ids)

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    @patch("apps.auditlog.business_logger.AuditConfig.BULK_OPERATION_THRESHOLD", 5)
    @patch("apps.auditlog.business_logger.AuditConfig.BULK_SAMPLE_SIZE", 3)
    def test_log_bulk_operation_large_batch(self, mock_audit_create):
        """Test logging large bulk operation (over threshold)."""
        request = self.factory.post("/bulk/delete/")
        request.user = self.user

        # Create 10 entries (over threshold of 5)
        entries = [EntryFactory() for _ in range(10)]

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_delete",
            affected_objects=entries,
            request=request,
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["operation_type"], "bulk_delete")
        self.assertEqual(metadata["total_objects"], 10)
        # Only sample should be included for large operations
        self.assertEqual(len(metadata["object_ids"]), 3)
        # Should be first 3 entries
        expected_sample_ids = [str(entry.entry_id) for entry in entries[:3]]
        self.assertEqual(metadata["object_ids"], expected_sample_ids)

    @pytest.mark.django_db
    @patch("apps.auditlog.business_logger.audit_create")
    def test_log_bulk_operation_without_request(self, mock_audit_create):
        """Test logging bulk operation without request."""
        entries = [EntryFactory() for _ in range(3)]

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="scheduled_cleanup",
            affected_objects=entries,
            request=None,
            cleanup_reason="expired_entries",
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["source"], "service_call")
        self.assertEqual(metadata["cleanup_reason"], "expired_entries")


@pytest.mark.unit
class TestBusinessAuditLoggerErrorHandling(TestCase):
    """Test BusinessAuditLogger error handling."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()

    @pytest.mark.django_db
    def test_log_entry_action_invalid_user(self):
        """Test entry action logging with invalid user."""
        request = self.factory.post("/entries/submit/")

        with self.assertRaises(ValueError):
            BusinessAuditLogger.log_entry_action(
                user=None, entry=self.entry, action="submit", request=request
            )

    @pytest.mark.django_db
    def test_log_permission_change_invalid_user(self):
        """Test permission change logging with invalid user."""
        request = self.factory.post("/permissions/grant/")
        target_user = CustomUserFactory()

        with self.assertRaises(ValueError):
            BusinessAuditLogger.log_permission_change(
                user=None,
                target_user=target_user,
                permission="admin",
                action="grant",
                request=request,
            )

    @pytest.mark.django_db
    def test_log_data_export_invalid_user(self):
        """Test data export logging with invalid user."""
        request = self.factory.get("/export/")

        with self.assertRaises(ValueError):
            BusinessAuditLogger.log_data_export(
                user=None,
                export_type="entries",
                filters={},
                result_count=100,
                request=request,
            )
