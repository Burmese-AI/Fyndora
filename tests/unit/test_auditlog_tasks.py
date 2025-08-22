from unittest.mock import patch

import pytest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from tests.factories.auditlog_factories import AuditTrailFactory
from tests.factories.entry_factories import EntryFactory
from tests.factories.user_factories import CustomUserFactory
from tests.factories.workspace_factories import WorkspaceFactory


@pytest.mark.unit
class TestAuditCreateAsync(TestCase):
    """Test audit_create_async Celery task."""

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_basic(self, mock_audit_create):
        """Test basic async audit creation."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        entry = EntryFactory()

        # Mock the audit_create service
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        # Call the async task
        result = audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata={"async": True},
        )

        # Verify audit_create was called with correct parameters
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            workspace=None,
            metadata={"async": True},
        )

        # Verify task returns audit ID
        self.assertEqual(result, str(mock_audit.audit_id))

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_no_user(self, mock_audit_create):
        """Test async audit creation without user (system action)."""
        from apps.auditlog.tasks import audit_create_async

        entry = EntryFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        result = audit_create_async(
            user_id=None,
            action_type=AuditActionType.SYSTEM_ERROR,
            target_entity=entry,
            metadata={"system_action": True},
        )

        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.SYSTEM_ERROR,
            target_entity=entry,
            workspace=None,
            metadata={"system_action": True},
        )

        self.assertEqual(result, str(mock_audit.audit_id))

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_invalid_user(self, mock_audit_create):
        """Test async audit creation with invalid user ID."""
        from apps.auditlog.tasks import audit_create_async

        entry = EntryFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        # Use non-existent user ID
        audit_create_async(
            user_id=99999,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata={},
        )

        # Should call audit_create with user=None when user not found
        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_invalid_target_entity(self, mock_audit_create):
        """Test async audit creation with invalid target entity."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity={
                "model": "entries.Entry",
                "pk": 99999,
            },
            metadata={},
        )

        # Should call audit_create with target_entity=None when entity not found
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_workspace_target(self, mock_audit_create):
        """Test async audit creation with workspace as target entity."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        workspace = WorkspaceFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.WORKSPACE_CREATED,
            target_entity=workspace,
            metadata={"workspace_title": workspace.title},
        )

        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.WORKSPACE_CREATED,
            target_entity=workspace,
            workspace=None,
            metadata={"workspace_title": workspace.title},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_exception_handling(self, mock_audit_create):
        """Test async audit creation exception handling."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        entry = EntryFactory()

        # Mock audit_create to raise an exception
        mock_audit_create.side_effect = Exception("Database error")

        # Task should handle the exception gracefully
        with self.assertLogs("apps.auditlog.tasks", level="ERROR") as log:
            result = audit_create_async(
                user_id=user.user_id,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=entry,
                metadata={},
            )

        # Should return None on error
        self.assertIsNone(result)

        # Should log the error
        self.assertIn("ERROR", log.output[0])
        self.assertIn("Database error", log.output[0])


@pytest.mark.unit
class TestAuditCreateAuthenticationEventAsync(TestCase):
    """Test audit_create_authentication_event_async Celery task."""

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_login_success(self, mock_auth_event):
        """Test async authentication event for successful login."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_auth_event.return_value = mock_audit

        result = audit_create_authentication_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"},
        )

        mock_auth_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"},
        )

        self.assertEqual(result, str(mock_audit.audit_id))

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_login_failed(self, mock_auth_event):
        """Test async authentication event for failed login."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        mock_audit = AuditTrailFactory.build()
        mock_auth_event.return_value = mock_audit

        audit_create_authentication_event_async(
            user_id=None,
            action_type=AuditActionType.LOGIN_FAILED,
            metadata={
                "username_attempted": "invalid_user",
                "ip_address": "192.168.1.100",
                "failure_reason": "invalid_credentials",
            },
        )

        mock_auth_event.assert_called_once_with(
            user=None,
            action_type=AuditActionType.LOGIN_FAILED,
            metadata={
                "username_attempted": "invalid_user",
                "ip_address": "192.168.1.100",
                "failure_reason": "invalid_credentials",
            },
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_exception_handling(self, mock_auth_event):
        """Test async authentication event exception handling."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_auth_event.side_effect = Exception("Service error")

        with self.assertLogs("apps.auditlog.tasks", level="ERROR") as log:
            result = audit_create_authentication_event_async(
                user_id=user.user_id,
                action_type=AuditActionType.LOGIN_SUCCESS,
                metadata={"ip_address": "192.168.1.1"},
            )

        self.assertIsNone(result)
        self.assertIn("ERROR", log.output[0])
        self.assertIn("Service error", log.output[0])


@pytest.mark.unit
class TestAuditCreateSecurityEventAsync(TestCase):
    """Test audit_create_security_event_async Celery task."""

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_permission_granted(self, mock_security_event):
        """Test async security event for permission granted."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        result = audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.PERMISSION_GRANTED,
            metadata={
                "permission": "admin_access",
                "resource": "workspace_1",
                "granted_by": "system_admin",
            },
        )

        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=None,
            metadata={
                "permission": "admin_access",
                "resource": "workspace_1",
                "granted_by": "system_admin",
            },
        )

        self.assertEqual(result, str(mock_audit.audit_id))

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_data_export(self, mock_security_event):
        """Test async security event for data export."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.DATA_EXPORTED,
            metadata={
                "export_type": "entries",
                "record_count": 1500,
                "export_format": "csv",
                "reason": "compliance_audit",
            },
        )

        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.DATA_EXPORTED,
            target_entity=None,
            metadata={
                "export_type": "entries",
                "record_count": 1500,
                "export_format": "csv",
                "reason": "compliance_audit",
            },
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_exception_handling(self, mock_security_event):
        """Test async security event exception handling."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_security_event.side_effect = Exception("Security service error")

        with self.assertLogs("apps.auditlog.tasks", level="ERROR") as log:
            result = audit_create_security_event_async(
                user_id=user.user_id,
                action_type=AuditActionType.PERMISSION_GRANTED,
                metadata={"permission": "admin_access"},
            )

        self.assertIsNone(result)
        self.assertIn("ERROR", log.output[0])
        self.assertIn("Security service error", log.output[0])


@pytest.mark.unit
class TestAuditTasksIntegration(TestCase):
    """Test integration scenarios for audit tasks."""

    @pytest.mark.django_db
    def test_task_entity_resolution_performance(self):
        """Test performance of entity resolution in tasks."""
        import time

        from apps.auditlog.tasks import audit_create_async

        # Create test data
        users = [CustomUserFactory() for _ in range(10)]
        entries = [EntryFactory() for _ in range(10)]

        start_time = time.time()

        # Simulate multiple async task calls
        with patch("apps.auditlog.tasks.audit_create") as mock_audit_create:
            mock_audit_create.return_value = AuditTrailFactory.build()

            for i in range(50):
                user = users[i % len(users)]
                entry = entries[i % len(entries)]

                audit_create_async(
                    user_id=user.user_id,
                    action_type=AuditActionType.ENTRY_CREATED,
                    target_entity=entry,
                    metadata={"batch_index": i},
                )

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertion
        self.assertLess(duration, 5.0, "Task entity resolution took too long")

        # Verify all calls were made
        self.assertEqual(mock_audit_create.call_count, 50)

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_task_metadata_serialization(self, mock_audit_create):
        """Test that complex metadata is properly handled in tasks."""
        from django.utils import timezone

        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        entry = EntryFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        complex_metadata = {
            "timestamp": timezone.now().isoformat(),
            "nested_data": {
                "user_info": {"id": user.user_id, "username": user.username},
                "entry_info": {"id": entry.entry_id, "description": entry.description},
            },
            "list_data": [1, 2, 3, "string", True],
            "boolean_flags": {"is_critical": True, "requires_approval": False},
        }

        result = audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_UPDATED,
            target_entity=entry,
            metadata=complex_metadata,
        )

        # Verify the task completed successfully
        self.assertEqual(result, str(mock_audit.audit_id))

        # Verify audit_create was called with the complex metadata
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_UPDATED,
            target_entity=entry,
            workspace=None,
            metadata=complex_metadata,
        )
        call_args = mock_audit_create.call_args
        passed_metadata = call_args[1]["metadata"]

        # Verify metadata structure is preserved
        self.assertIn("nested_data", passed_metadata)
        self.assertIn("list_data", passed_metadata)
        self.assertIn("boolean_flags", passed_metadata)
        self.assertEqual(
            passed_metadata["nested_data"]["user_info"]["id"], user.user_id
        )
