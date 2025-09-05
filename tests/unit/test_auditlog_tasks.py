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
    def test_audit_create_async_target_entity_dictionary_format(self, mock_audit_create):
        """Test async audit creation with target entity in dictionary format."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        entry = EntryFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity={
                "model": "apps.entries.models.Entry",
                "pk": entry.entry_id,
            },
            metadata={},
        )

        # Should call audit_create with resolved entry instance
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_workspace_dictionary_format(self, mock_audit_create):
        """Test async audit creation with workspace in dictionary format."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        workspace = WorkspaceFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace={
                "pk": workspace.workspace_id,
            },
            metadata={},
        )

        # Should call audit_create with resolved workspace instance
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=workspace,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_invalid_workspace(self, mock_audit_create):
        """Test async audit creation with invalid workspace."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        # This should raise an exception due to invalid UUID, so audit_create won't be called
        with self.assertLogs("apps.auditlog.tasks", level="WARNING") as log:
            result = audit_create_async(
                user_id=user.user_id,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=None,
                workspace={
                    "pk": "invalid-uuid",
                },
                metadata={},
            )

        # Should return audit ID despite workspace validation error
        self.assertIsNotNone(result)
        
        # Should log the warning
        self.assertIn("WARNING", log.output[0])
        self.assertIn("Workspace not found", log.output[0])

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_target_entity_key_error(self, mock_audit_create):
        """Test async audit creation with target entity missing required keys."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity={
                "invalid_key": "value",
            },
            metadata={},
        )

        # Should call audit_create with target_entity=None when key error occurs
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_workspace_key_error(self, mock_audit_create):
        """Test async audit creation with workspace missing required keys."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace={
                "invalid_key": "value",
            },
            metadata={},
        )

        # Should call audit_create with workspace=None when key error occurs
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_target_entity_lookup_error(self, mock_audit_create):
        """Test async audit creation with target entity LookupError."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity={
                "model": "invalid.app.Model",
                "pk": "some-id",
            },
            metadata={},
        )

        # Should call audit_create with target_entity=None when LookupError occurs
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_target_entity_attribute_error(self, mock_audit_create):
        """Test async audit creation with target entity AttributeError."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        # Create a mock object that doesn't have _meta attribute but is subscriptable
        class MockObjectWithoutMeta:
            def __getitem__(self, key):
                return "value"

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=MockObjectWithoutMeta(),
            metadata={},
        )

        # Should call audit_create with target_entity=None when AttributeError occurs
        mock_audit_create.assert_called_once_with(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=None,
            metadata={},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create")
    def test_audit_create_async_workspace_attribute_error(self, mock_audit_create):
        """Test async audit creation with workspace AttributeError."""
        from apps.auditlog.tasks import audit_create_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_audit_create.return_value = mock_audit

        # Create a mock object that doesn't have _meta attribute but is subscriptable
        class MockObjectWithoutMeta:
            def __getitem__(self, key):
                return "invalid-uuid"

        audit_create_async(
            user_id=user.user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=None,
            workspace=MockObjectWithoutMeta(),
            metadata={},
        )

        # Should call audit_create with workspace=None when AttributeError occurs
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

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_audit_creation_returns_none(self, mock_auth_event):
        """Test async authentication event when audit creation returns None."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_auth_event.return_value = None

        with self.assertLogs("apps.auditlog.tasks", level="WARNING") as log:
            result = audit_create_authentication_event_async(
                user_id=user.user_id,
                action_type=AuditActionType.LOGIN_SUCCESS,
                metadata={"ip_address": "192.168.1.1"},
            )

        self.assertIsNone(result)
        self.assertIn("WARNING", log.output[0])
        self.assertIn("Authentication audit creation returned None", log.output[0])


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

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_target_entity_dictionary_format(self, mock_security_event):
        """Test async security event with target entity in dictionary format."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        entry = EntryFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity={
                "model": "apps.entries.models.Entry",
                "pk": entry.entry_id,
            },
            metadata={"permission": "admin_access"},
        )

        # Should call audit_create_security_event with resolved entry instance
        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=entry,
            metadata={"permission": "admin_access"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_invalid_target_entity(self, mock_security_event):
        """Test async security event with invalid target entity."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity={
                "model": "entries.Entry",
                "pk": 99999,
            },
            metadata={"permission": "admin_access"},
        )

        # Should call audit_create_security_event with target_entity=None when entity not found
        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=None,
            metadata={"permission": "admin_access"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_target_entity_key_error(self, mock_security_event):
        """Test async security event with target entity missing required keys."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity={
                "invalid_key": "value",
            },
            metadata={"permission": "admin_access"},
        )

        # Should call audit_create_security_event with target_entity=None when key error occurs
        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=None,
            metadata={"permission": "admin_access"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_audit_creation_returns_none(self, mock_security_event):
        """Test async security event when audit creation returns None."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_security_event.return_value = None

        with self.assertLogs("apps.auditlog.tasks", level="WARNING") as log:
            result = audit_create_security_event_async(
                user_id=user.user_id,
                action_type=AuditActionType.PERMISSION_GRANTED,
                metadata={"permission": "admin_access"},
            )

        self.assertIsNone(result)
        self.assertIn("WARNING", log.output[0])
        self.assertIn("Security audit creation returned None", log.output[0])

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_target_entity_lookup_error(self, mock_security_event):
        """Test async security event with target entity LookupError."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity={
                "model": "invalid.Model",
                "pk": 1,
            },
            metadata={"permission": "admin_access"},
        )

        # Should call audit_create_security_event with target_entity=None when LookupError occurs
        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=None,
            metadata={"permission": "admin_access"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_security_event")
    def test_security_event_async_target_entity_attribute_error(self, mock_security_event):
        """Test async security event with target entity AttributeError."""
        from apps.auditlog.tasks import audit_create_security_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_security_event.return_value = mock_audit

        # Create a mock object that doesn't have _meta attribute but is subscriptable
        class MockObjectWithoutMeta:
            def __getitem__(self, key):
                return "value"

        audit_create_security_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=MockObjectWithoutMeta(),
            metadata={"permission": "admin_access"},
        )

        # Should call audit_create_security_event with target_entity=None when AttributeError occurs
        mock_security_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            target_entity=None,
            metadata={"permission": "admin_access"},
        )


@pytest.mark.unit
class TestAuditCreateAuthenticationEventAsync(TestCase):
    """Test audit_create_authentication_event_async Celery task."""

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_lookup_error(self, mock_auth_event):
        """Test async authentication event with LookupError."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_auth_event.return_value = mock_audit

        audit_create_authentication_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

        # Should call audit_create_authentication_event
        mock_auth_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_attribute_error(self, mock_auth_event):
        """Test async authentication event with AttributeError."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_auth_event.return_value = mock_audit

        audit_create_authentication_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

        # Should call audit_create_authentication_event
        mock_auth_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_audit_creation_returns_none(self, mock_auth_event):
        """Test async authentication event when audit creation returns None."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_auth_event.return_value = None

        with self.assertLogs("apps.auditlog.tasks", level="WARNING") as log:
            result = audit_create_authentication_event_async(
                user_id=user.user_id,
                action_type=AuditActionType.LOGIN_SUCCESS,
                metadata={"ip_address": "192.168.1.1"},
            )

        self.assertIsNone(result)
        self.assertIn("WARNING", log.output[0])
        self.assertIn("Authentication audit creation returned None", log.output[0])

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_target_entity_lookup_error(self, mock_auth_event):
        """Test async authentication event with target entity LookupError."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_auth_event.return_value = mock_audit

        audit_create_authentication_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

        # Should call audit_create_authentication_event
        mock_auth_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_authentication_event")
    def test_authentication_event_async_target_entity_attribute_error(self, mock_auth_event):
        """Test async authentication event with target entity AttributeError."""
        from apps.auditlog.tasks import audit_create_authentication_event_async

        user = CustomUserFactory()
        mock_audit = AuditTrailFactory.build()
        mock_auth_event.return_value = mock_audit

        # Create a mock object that doesn't have _meta attribute but is subscriptable
        class MockObjectWithoutMeta:
            def __getitem__(self, key):
                return "value"

        audit_create_authentication_event_async(
            user_id=user.user_id,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

        # Should call audit_create_authentication_event
        mock_auth_event.assert_called_once_with(
            user=user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )


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


@pytest.mark.unit
class TestAuditCreateBulkAsync(TestCase):
    """Test audit_create_bulk_async Celery task."""

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_async.apply_async")
    def test_bulk_audit_creation_success(self, mock_apply_async):
        """Test successful bulk audit creation."""
        from apps.auditlog.tasks import audit_create_bulk_async

        # Mock successful audit creation
        mock_apply_async.return_value.get.return_value = "audit-id-123"

        audit_entries = [
            {
                "user_id": "user-1",
                "action_type": AuditActionType.ENTRY_CREATED,
                "target_entity": None,
                "metadata": {"test": "entry1"},
            },
            {
                "user_id": "user-2",
                "action_type": AuditActionType.ENTRY_UPDATED,
                "target_entity": None,
                "metadata": {"test": "entry2"},
            },
        ]

        result = audit_create_bulk_async(audit_entries)

        # Verify result structure
        self.assertEqual(result["success_count"], 2)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(len(result["audit_ids"]), 2)
        self.assertEqual(result["total_processed"], 2)
        self.assertIn("audit-id-123", result["audit_ids"])

        # Verify apply_async was called for each entry
        self.assertEqual(mock_apply_async.call_count, 2)

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_async.apply_async")
    def test_bulk_audit_creation_mixed_results(self, mock_apply_async):
        """Test bulk audit creation with mixed success and failure."""
        from apps.auditlog.tasks import audit_create_bulk_async

        # Mock mixed results - first call succeeds, second fails
        mock_result1 = type("MockResult", (), {"get": lambda *args, **kwargs: "audit-id-1"})()
        mock_result2 = type("MockResult", (), {"get": lambda *args, **kwargs: None})()
        
        mock_apply_async.side_effect = [mock_result1, mock_result2]

        audit_entries = [
            {
                "user_id": "user-1",
                "action_type": AuditActionType.ENTRY_CREATED,
                "target_entity": None,
                "metadata": {"test": "entry1"},
            },
            {
                "user_id": "user-2",
                "action_type": AuditActionType.ENTRY_UPDATED,
                "target_entity": None,
                "metadata": {"test": "entry2"},
            },
        ]

        result = audit_create_bulk_async(audit_entries)

        # Verify mixed results
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(len(result["audit_ids"]), 1)
        self.assertEqual(result["total_processed"], 2)

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_async.apply_async")
    def test_bulk_audit_creation_exception_handling(self, mock_apply_async):
        """Test bulk audit creation with exception handling."""
        from apps.auditlog.tasks import audit_create_bulk_async

        # Mock exception during processing
        mock_apply_async.side_effect = Exception("Task processing error")

        audit_entries = [
            {
                "user_id": "user-1",
                "action_type": AuditActionType.ENTRY_CREATED,
                "target_entity": None,
                "metadata": {"test": "entry1"},
            },
        ]

        with self.assertLogs("apps.auditlog.tasks", level="ERROR") as log:
            result = audit_create_bulk_async(audit_entries)

        # Verify error handling
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(len(result["audit_ids"]), 0)
        self.assertEqual(result["total_processed"], 1)

        # Verify error was logged
        self.assertIn("ERROR", log.output[0])
        self.assertIn("Task processing error", log.output[0])

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_async.apply_async")
    def test_bulk_audit_creation_timeout_handling(self, mock_apply_async):
        """Test bulk audit creation with timeout handling."""
        from apps.auditlog.tasks import audit_create_bulk_async

        # Mock timeout exception
        mock_apply_async.return_value.get.side_effect = Exception("Task timeout")

        audit_entries = [
            {
                "user_id": "user-1",
                "action_type": AuditActionType.ENTRY_CREATED,
                "target_entity": None,
                "metadata": {"test": "entry1"},
            },
        ]

        with self.assertLogs("apps.auditlog.tasks", level="ERROR") as log:
            result = audit_create_bulk_async(audit_entries)

        # Verify timeout handling
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(len(result["audit_ids"]), 0)

        # Verify timeout was logged
        self.assertIn("ERROR", log.output[0])
        self.assertIn("Task timeout", log.output[0])

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_async.apply_async")
    def test_bulk_audit_creation_empty_entries(self, mock_apply_async):
        """Test bulk audit creation with empty entries list."""
        from apps.auditlog.tasks import audit_create_bulk_async

        result = audit_create_bulk_async([])

        # Verify empty result
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(len(result["audit_ids"]), 0)
        self.assertEqual(result["total_processed"], 0)

        # Verify no async calls were made
        mock_apply_async.assert_not_called()

    @pytest.mark.django_db
    @patch("apps.auditlog.tasks.audit_create_async.apply_async")
    def test_bulk_audit_creation_large_batch(self, mock_apply_async):
        """Test bulk audit creation with large batch."""
        from apps.auditlog.tasks import audit_create_bulk_async

        # Mock successful audit creation
        mock_apply_async.return_value.get.return_value = "audit-id-123"

        # Create large batch of audit entries
        audit_entries = []
        for i in range(100):
            audit_entries.append({
                "user_id": f"user-{i}",
                "action_type": AuditActionType.ENTRY_CREATED,
                "target_entity": None,
                "metadata": {"batch_index": i},
            })

        result = audit_create_bulk_async(audit_entries)

        # Verify large batch processing
        self.assertEqual(result["success_count"], 100)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(len(result["audit_ids"]), 100)
        self.assertEqual(result["total_processed"], 100)

        # Verify apply_async was called for each entry
        self.assertEqual(mock_apply_async.call_count, 100)
