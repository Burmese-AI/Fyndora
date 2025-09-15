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


@pytest.mark.unit
class TestBusinessAuditLoggerEntryActions(TestCase):
    """Test BusinessAuditLogger entry action logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.entry_logger.EntryAuditLogger.log_entry_action")
    def test_log_entry_action_submit(self, mock_log_entry_action):
        """Test logging entry submit action."""
        request = self.factory.post("/entries/submit/")
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="submit", request=request
        )

        # Verify the entry logger method was called
        mock_log_entry_action.assert_called_once_with(
            self.user, self.entry, "submit", request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.entry_logger.EntryAuditLogger.log_entry_action")
    def test_log_entry_action_approve_with_notes(self, mock_log_entry_action):
        """Test logging entry approve action with approval notes."""
        request = self.factory.post(
            "/entries/approve/", {"notes": "All requirements met", "level": "manager"}
        )
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="approve", request=request
        )

        # Verify the entry logger method was called
        mock_log_entry_action.assert_called_once_with(
            self.user, self.entry, "approve", request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.entry_logger.EntryAuditLogger.log_entry_action")
    def test_log_entry_action_reject_with_reason(self, mock_log_entry_action):
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

        # Verify the entry logger method was called
        mock_log_entry_action.assert_called_once_with(
            self.user, self.entry, "reject", request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.entry_logger.EntryAuditLogger.log_entry_action")
    def test_log_entry_action_flag_with_severity(self, mock_log_entry_action):
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

        # Verify the entry logger method was called
        mock_log_entry_action.assert_called_once_with(
            self.user, self.entry, "flag", request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.entry_logger.EntryAuditLogger.log_entry_action")
    def test_log_entry_action_without_request(self, mock_log_entry_action):
        """Test logging entry action without request (service call)."""
        BusinessAuditLogger.log_entry_action(
            user=self.user,
            entry=self.entry,
            action="approve",
            request=None,
            notes="Service approval",
            level="automatic",
        )

        # Verify the entry logger method was called
        mock_log_entry_action.assert_called_once_with(
            self.user,
            self.entry,
            "approve",
            None,
            notes="Service approval",
            level="automatic",
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.base_logger.logger")
    def test_log_entry_action_unknown_action(self, mock_logger):
        """Test logging unknown entry action."""
        request = self.factory.post("/entries/unknown/")
        request.user = self.user

        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=self.entry, action="unknown_action", request=request
        )

        # Should log warning and return early
        mock_logger.warning.assert_called_once()
        self.assertIn("Unknown action", mock_logger.warning.call_args[0][0])


@pytest.mark.unit
class TestBusinessAuditLoggerPermissionChanges(TestCase):
    """Test BusinessAuditLogger permission change logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.target_user = CustomUserFactory()

    @pytest.mark.django_db
    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger.log_permission_change"
    )
    def test_log_permission_change_grant(self, mock_log_permission_change):
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
            permission_type="admin_access",
            action="grant",
            request=request,
        )

        # Verify the system logger method was called
        mock_log_permission_change.assert_called_once_with(
            self.user, self.target_user, "admin_access", "grant", request
        )

    @pytest.mark.django_db
    @patch(
        "apps.auditlog.loggers.system_logger.SystemAuditLogger.log_permission_change"
    )
    def test_log_permission_change_revoke(self, mock_log_permission_change):
        """Test logging permission revoke."""
        request = self.factory.post("/permissions/revoke/", {"reason": "Role change"})
        request.user = self.user

        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=self.target_user,
            permission_type="admin_access",
            action="revoke",
            request=request,
        )

        # Verify the system logger method was called
        mock_log_permission_change.assert_called_once_with(
            self.user, self.target_user, "admin_access", "revoke", request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.logger")
    def test_log_permission_change_unknown_action(self, mock_logger):
        """Test logging unknown permission action."""
        request = self.factory.post("/permissions/unknown/")
        request.user = self.user

        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=self.target_user,
            permission_type="admin_access",
            action="unknown",
            request=request,
        )

        # Should log warning and return early
        mock_logger.warning.assert_called_once()
        self.assertIn("Unknown permission action", mock_logger.warning.call_args[0][0])


@pytest.mark.unit
class TestBusinessAuditLoggerDataExport(TestCase):
    """Test BusinessAuditLogger data export logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.SystemAuditLogger.log_data_export")
    def test_log_data_export_with_request(self, mock_log_data_export):
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

        # Verify the system logger method was called
        mock_log_data_export.assert_called_once_with(
            self.user, "entries", request, filters=filters, result_count=150
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.SystemAuditLogger.log_data_export")
    def test_log_data_export_without_request(self, mock_log_data_export):
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

        # Verify the system logger method was called
        mock_log_data_export.assert_called_once_with(
            self.user,
            "audit_logs",
            None,
            filters=filters,
            result_count=50,
            format="csv",
            reason="compliance_audit",
        )


@pytest.mark.unit
class TestBusinessAuditLoggerBulkOperations(TestCase):
    """Test BusinessAuditLogger bulk operation logging."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.SystemAuditLogger.log_bulk_operation")
    def test_log_bulk_operation_small_batch(self, mock_log_bulk_operation):
        """Test logging small bulk operation (under threshold)."""
        request = self.factory.post("/bulk/approve/")
        request.user = self.user

        # Create 5 entries (under threshold)
        entries = [EntryFactory() for _ in range(5)]

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_approve",
            affected_entities=entries,
            request=request,
        )

        # Verify the system logger method was called
        mock_log_bulk_operation.assert_called_once_with(
            self.user, "bulk_approve", entries, request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.SystemAuditLogger.log_bulk_operation")
    def test_log_bulk_operation_large_batch(self, mock_log_bulk_operation):
        """Test logging large bulk operation (over threshold)."""
        request = self.factory.post("/bulk/delete/")
        request.user = self.user

        # Create 10 entries (over threshold of 5)
        entries = [EntryFactory() for _ in range(10)]

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_delete",
            affected_entities=entries,
            request=request,
        )

        # Verify the system logger method was called
        mock_log_bulk_operation.assert_called_once_with(
            self.user, "bulk_delete", entries, request
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.SystemAuditLogger.log_bulk_operation")
    def test_log_bulk_operation_without_request(self, mock_log_bulk_operation):
        """Test logging bulk operation without request."""
        entries = [EntryFactory() for _ in range(3)]

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="scheduled_cleanup",
            affected_entities=entries,
            request=None,
            cleanup_reason="expired_entries",
        )

        # Verify the system logger method was called
        mock_log_bulk_operation.assert_called_once_with(
            self.user,
            "scheduled_cleanup",
            entries,
            None,
            cleanup_reason="expired_entries",
        )


@pytest.mark.unit
class TestBusinessAuditLoggerErrorHandling(TestCase):
    """Test BusinessAuditLogger error handling."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.entry_logger.logger")
    def test_log_entry_action_invalid_user(self, mock_logger):
        """Test entry action logging with invalid user."""
        request = self.factory.post("/entries/submit/")

        with self.assertRaises(ValueError):
            BusinessAuditLogger.log_entry_action(
                user=None, entry=self.entry, action="submit", request=request
            )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.logger")
    def test_log_permission_change_invalid_user(self, mock_logger):
        """Test permission change logging with invalid user."""
        request = self.factory.post("/permissions/grant/")
        target_user = CustomUserFactory()

        with self.assertRaises(ValueError):
            BusinessAuditLogger.log_permission_change(
                user=None,
                target_user=target_user,
                permission_type="admin",
                action="grant",
                request=request,
            )

    @pytest.mark.django_db
    @patch("apps.auditlog.loggers.system_logger.logger")
    def test_log_data_export_invalid_user(self, mock_logger):
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
