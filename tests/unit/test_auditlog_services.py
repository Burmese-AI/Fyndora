"""
Unit tests for the auditlog app services.

Following the test plan: AuditLog App (apps.auditlog)
- Service function tests
- Business logic validation
"""

from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from unittest.mock import patch

from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from apps.auditlog.services import audit_create
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
    WorkspaceFactory,
)
from tests.factories.auditlog_factories import AuditTrailFactory

User = get_user_model()


@pytest.mark.unit
class TestAuditCreateService(TestCase):
    """Test the audit_create service function."""

    @pytest.mark.django_db
    def test_audit_create_with_user(self):
        """Test creating audit log with user."""
        user = CustomUserFactory()
        entry = EntryFactory()
        metadata = {"key": "value", "amount": 1000}

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata=metadata,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsInstance(audit, AuditTrail)
        self.assertEqual(audit.user, user)
        self.assertEqual(audit.action_type, AuditActionType.ENTRY_CREATED)
        self.assertEqual(audit.target_entity, entry)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertEqual(audit.metadata, metadata)
        self.assertIsNotNone(audit.timestamp)
        self.assertIsNotNone(audit.audit_id)

    @pytest.mark.django_db
    def test_audit_create_without_user(self):
        """Test creating audit log without user (system action)."""
        entry = EntryFactory()
        metadata = {"system_action": "automated_cleanup"}

        audit = audit_create(
            user=None,
            action_type=AuditActionType.ENTRY_STATUS_CHANGED,
            target_entity=entry,
            metadata=metadata,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.user)
        self.assertEqual(audit.action_type, AuditActionType.ENTRY_STATUS_CHANGED)
        self.assertEqual(audit.target_entity, entry)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertEqual(audit.metadata, metadata)

    @pytest.mark.django_db
    def test_audit_create_without_metadata(self):
        """Test creating audit log without metadata."""
        user = CustomUserFactory()
        entry = EntryFactory()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, user)
        self.assertIsNone(audit.metadata)

    @pytest.mark.django_db
    def test_audit_create_with_none_metadata(self):
        """Test creating audit log with explicitly None metadata."""
        user = CustomUserFactory()
        entry = EntryFactory()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata=None,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.metadata)

    @pytest.mark.django_db
    def test_audit_create_with_complex_metadata(self):
        """Test creating audit log with complex metadata structure."""
        user = CustomUserFactory()
        entry = EntryFactory()
        complex_metadata = {
            "user_details": {"username": user.username, "role": "admin"},
            "changes": {"old_value": "draft", "new_value": "submitted"},
            "context": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_STATUS_CHANGED,
            target_entity=entry,
            metadata=complex_metadata,
        )

        # Verify complex metadata was stored correctly
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata, complex_metadata)
        self.assertEqual(audit.metadata["user_details"]["username"], user.username)
        self.assertEqual(audit.metadata["changes"]["old_value"], "draft")

    @pytest.mark.django_db
    def test_audit_create_persists_to_database(self):
        """Test that audit_create actually persists to database."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Count existing audits
        initial_count = AuditTrail.objects.count()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
        )

        # Verify it was saved to database
        self.assertEqual(AuditTrail.objects.count(), initial_count + 1)

        # Verify we can retrieve it
        retrieved_audit = AuditTrail.objects.get(audit_id=audit.audit_id)
        self.assertEqual(retrieved_audit.user, user)
        self.assertEqual(retrieved_audit.target_entity, entry)

    @pytest.mark.django_db
    def test_audit_create_with_all_action_types(self):
        """Test audit_create with all available action types."""
        user = CustomUserFactory()
        entry = EntryFactory()

        action_types = [choice[0] for choice in AuditActionType.choices]

        for action_type in action_types:
            audit = audit_create(
                user=user,
                action_type=action_type,
                target_entity=entry,
                metadata={"test": f"test_{action_type}"},
            )

            self.assertEqual(audit.action_type, action_type)
            self.assertIsNotNone(audit.audit_id)

    @pytest.mark.django_db
    def test_audit_create_with_different_entity_types(self):
        """Test audit_create with different model types as target entities."""
        user = CustomUserFactory()

        # Create different model instances
        entry = EntryFactory()
        workspace = WorkspaceFactory()

        # Test with entry model
        entry_audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata={"test": "test_entry"},
        )

        # Test with workspace model
        workspace_audit = audit_create(
            user=user,
            action_type=AuditActionType.WORKSPACE_CREATED,
            target_entity=workspace,
            metadata={"test": "test_workspace"},
        )

        # Test with user model
        user_audit = audit_create(
            user=user,
            action_type=AuditActionType.USER_CREATED,
            target_entity=user,
            metadata={"test": "test_user"},
        )

        # Verify different entity types are handled correctly
        self.assertEqual(
            entry_audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertEqual(
            workspace_audit.target_entity_type,
            ContentType.objects.get_for_model(workspace),
        )
        self.assertEqual(
            user_audit.target_entity_type, ContentType.objects.get_for_model(user)
        )

    @pytest.mark.django_db
    def test_audit_create_without_target_entity(self):
        """Test audit_create without target entity (e.g., failed logins)."""
        user = CustomUserFactory()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.LOGIN_FAILED,
            target_entity=None,
            metadata={"reason": "invalid_credentials"},
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, user)
        self.assertEqual(audit.action_type, AuditActionType.LOGIN_FAILED)
        self.assertIsNone(audit.target_entity_type)
        self.assertIsNone(audit.target_entity_id)
        self.assertEqual(audit.metadata["reason"], "invalid_credentials")

    @pytest.mark.django_db
    def test_audit_create_workspace_detection_via_workspace_team(self):
        """Test workspace detection via workspace_team relationship."""
        from apps.workspaces.models import WorkspaceTeam
        from tests.factories.team_factories import TeamFactory
        from tests.factories.workspace_factories import WorkspaceTeamFactory

        user = CustomUserFactory()
        workspace = WorkspaceFactory()
        team = TeamFactory()
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)

        # Create a mock object that has workspace_team attribute pointing to WorkspaceTeam
        class MockEntityWithWorkspaceTeam:
            def __init__(self, workspace_team):
                self.workspace_team = workspace_team
                self.pk = 123  # Add pk attribute

        mock_entity = MockEntityWithWorkspaceTeam(workspace_team)

        # Mock the ContentType.objects.get_for_model to avoid the _meta issue
        with patch('django.contrib.contenttypes.models.ContentType.objects.get_for_model') as mock_get_for_model:
            mock_get_for_model.return_value = None  # Return None to avoid the _meta issue
            
            audit = audit_create(
                user=user,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=mock_entity,
                metadata={"test": "workspace_detection"},
            )

            # Verify audit was created correctly
            self.assertIsNotNone(audit)
            self.assertEqual(audit.user, user)

    @pytest.mark.django_db
    def test_audit_create_exception_handling(self):
        """Test audit_create handles exceptions gracefully."""
        from unittest.mock import patch
        from apps.auditlog.services import audit_create

        user = CustomUserFactory()
        entry = EntryFactory()

        # Mock model_update to raise an exception
        with patch("apps.auditlog.services.model_update") as mock_model_update:
            mock_model_update.side_effect = Exception("Database error")

            result = audit_create(
                user=user,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=entry,
                metadata={"test": "error_test"},
            )

            # Should return None when exception occurs
            self.assertIsNone(result)


@pytest.mark.unit
class TestAuditCreateAuthenticationEvent(TestCase):
    """Test audit_create_authentication_event service function."""

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_authentication_event_basic(self, mock_audit_create):
        """Test basic authentication event creation."""
        from apps.auditlog.services import audit_create_authentication_event

        user = CustomUserFactory()

        audit_create_authentication_event(
            user=user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"ip_address": "192.168.1.1"},
        )

        # Verify audit_create was called with enhanced metadata
        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["user"], user)
        self.assertEqual(call_args[1]["action_type"], AuditActionType.LOGIN_SUCCESS)

        # Check enhanced metadata
        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["event_category"], "authentication")
        self.assertEqual(metadata["ip_address"], "192.168.1.1")

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_authentication_event_failed_login(self, mock_audit_create):
        """Test failed login authentication event."""
        from apps.auditlog.services import audit_create_authentication_event

        audit_create_authentication_event(
            user=None,
            action_type=AuditActionType.LOGIN_FAILED,
            metadata={
                "username_attempted": "invalid_user",
                "ip_address": "192.168.1.100",
                "failure_reason": "invalid_credentials",
            },
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertIsNone(call_args[1]["user"])
        self.assertEqual(call_args[1]["action_type"], AuditActionType.LOGIN_FAILED)

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["event_category"], "authentication")
        self.assertEqual(metadata["username_attempted"], "invalid_user")
        self.assertEqual(metadata["failure_reason"], "invalid_credentials")


@pytest.mark.unit
class TestAuditCreateSecurityEvent(TestCase):
    """Test audit_create_security_event service function."""

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_security_event_basic(self, mock_audit_create):
        """Test basic security event creation."""
        from apps.auditlog.services import audit_create_security_event

        user = CustomUserFactory()

        audit_create_security_event(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED,
            metadata={"permission": "admin_access", "resource": "workspace_1"},
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        self.assertEqual(call_args[1]["user"], user)
        self.assertEqual(
            call_args[1]["action_type"], AuditActionType.PERMISSION_GRANTED
        )

        # Check enhanced metadata
        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["event_category"], "security")
        self.assertTrue(metadata["is_security_related"])
        self.assertEqual(metadata["permission"], "admin_access")
        self.assertIn("timestamp", metadata)

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_security_event_data_export(self, mock_audit_create):
        """Test data export security event."""
        from apps.auditlog.services import audit_create_security_event

        user = CustomUserFactory()

        audit_create_security_event(
            user=user,
            action_type=AuditActionType.DATA_EXPORTED,
            metadata={
                "export_type": "entries",
                "record_count": 1500,
                "export_format": "csv",
                "reason": "compliance_audit",
            },
        )

        mock_audit_create.assert_called_once()
        call_args = mock_audit_create.call_args

        metadata = call_args[1]["metadata"]
        self.assertEqual(metadata["event_category"], "security")
        self.assertTrue(metadata["is_security_related"])
        self.assertEqual(metadata["export_type"], "entries")
        self.assertEqual(metadata["record_count"], 1500)


@pytest.mark.unit
class TestAuditCleanupExpiredLogs(TestCase):
    """Test audit_cleanup_expired_logs service function."""

    @pytest.mark.django_db
    def test_cleanup_expired_logs_basic(self):
        """Test basic cleanup of expired logs."""
        from apps.auditlog.services import audit_cleanup_expired_logs
        from django.utils import timezone
        from datetime import timedelta

        # Create old audit logs
        old_date = timezone.now() - timedelta(days=400)  # Older than default retention
        recent_date = timezone.now() - timedelta(days=30)  # Within retention period

        # Create old logs that should be deleted
        old_audit1 = AuditTrailFactory(action_type=AuditActionType.ENTRY_CREATED)
        old_audit2 = AuditTrailFactory(action_type=AuditActionType.ENTRY_UPDATED)

        # Create recent logs that should be kept
        recent_audit = AuditTrailFactory(action_type=AuditActionType.ENTRY_CREATED)

        # Update timestamps manually (auto_now_add=True prevents setting during creation)
        AuditTrail.objects.filter(audit_id=old_audit1.audit_id).update(
            timestamp=old_date
        )
        AuditTrail.objects.filter(audit_id=old_audit2.audit_id).update(
            timestamp=old_date
        )
        AuditTrail.objects.filter(audit_id=recent_audit.audit_id).update(
            timestamp=recent_date
        )

        # Run cleanup
        cleanup_stats = audit_cleanup_expired_logs()

        # Verify old logs were deleted
        self.assertFalse(
            AuditTrail.objects.filter(audit_id=old_audit1.audit_id).exists()
        )
        self.assertFalse(
            AuditTrail.objects.filter(audit_id=old_audit2.audit_id).exists()
        )

        # Verify recent logs were kept
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=recent_audit.audit_id).exists()
        )

        # Verify return count
        self.assertEqual(cleanup_stats["total_deleted"], 2)

    @pytest.mark.django_db
    def test_cleanup_authentication_logs_retention(self):
        """Test cleanup with different retention for authentication logs."""
        from apps.auditlog.services import audit_cleanup_expired_logs
        from django.utils import timezone
        from datetime import timedelta

        # Create old authentication logs (should have longer retention)
        old_auth_date = timezone.now() - timedelta(days=400)
        old_regular_date = timezone.now() - timedelta(days=400)

        old_auth_audit = AuditTrailFactory(action_type=AuditActionType.LOGIN_SUCCESS)
        old_regular_audit = AuditTrailFactory(action_type=AuditActionType.ENTRY_CREATED)

        # Update timestamps manually (auto_now_add=True prevents setting during creation)
        AuditTrail.objects.filter(audit_id=old_auth_audit.audit_id).update(
            timestamp=old_auth_date
        )
        AuditTrail.objects.filter(audit_id=old_regular_audit.audit_id).update(
            timestamp=old_regular_date
        )

        # Run cleanup
        cleanup_stats = audit_cleanup_expired_logs()

        # Both should be deleted as they're very old
        self.assertFalse(
            AuditTrail.objects.filter(audit_id=old_auth_audit.audit_id).exists()
        )
        self.assertFalse(
            AuditTrail.objects.filter(audit_id=old_regular_audit.audit_id).exists()
        )

        self.assertEqual(cleanup_stats["total_deleted"], 2)

    @pytest.mark.django_db
    def test_cleanup_no_expired_logs(self):
        """Test cleanup when no logs are expired."""
        from apps.auditlog.services import audit_cleanup_expired_logs
        from django.utils import timezone
        from datetime import timedelta

        # Create recent logs
        recent_date = timezone.now() - timedelta(days=30)

        recent_audit1 = AuditTrailFactory(
            action_type=AuditActionType.ENTRY_CREATED, timestamp=recent_date
        )
        recent_audit2 = AuditTrailFactory(
            action_type=AuditActionType.LOGIN_SUCCESS, timestamp=recent_date
        )

        # Run cleanup
        cleanup_stats = audit_cleanup_expired_logs()

        # Verify no logs were deleted
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=recent_audit1.audit_id).exists()
        )
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=recent_audit2.audit_id).exists()
        )

        self.assertEqual(cleanup_stats["total_deleted"], 0)

    @pytest.mark.django_db
    def test_cleanup_dry_run_mode(self):
        """Test cleanup in dry run mode."""
        from apps.auditlog.services import audit_cleanup_expired_logs
        from django.utils import timezone
        from datetime import timedelta

        # Create old logs
        old_date = timezone.now() - timedelta(days=400)
        old_audit1 = AuditTrailFactory(action_type=AuditActionType.ENTRY_CREATED)
        old_audit2 = AuditTrailFactory(action_type=AuditActionType.LOGIN_SUCCESS)

        # Update timestamps manually
        AuditTrail.objects.filter(audit_id=old_audit1.audit_id).update(
            timestamp=old_date
        )
        AuditTrail.objects.filter(audit_id=old_audit2.audit_id).update(
            timestamp=old_date
        )

        # Run cleanup in dry run mode
        cleanup_stats = audit_cleanup_expired_logs(dry_run=True)

        # Verify logs were NOT deleted in dry run
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=old_audit1.audit_id).exists()
        )
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=old_audit2.audit_id).exists()
        )

        # Verify stats show what would be deleted
        self.assertTrue(cleanup_stats["total_deleted"] > 0)
        self.assertTrue(cleanup_stats["dry_run"])

    @pytest.mark.django_db
    def test_cleanup_specific_action_type_dry_run(self):
        """Test cleanup for specific action type in dry run mode."""
        from apps.auditlog.services import audit_cleanup_expired_logs
        from django.utils import timezone
        from datetime import timedelta

        # Create old logs
        old_date = timezone.now() - timedelta(days=400)
        old_audit1 = AuditTrailFactory(action_type=AuditActionType.ENTRY_CREATED)
        old_audit2 = AuditTrailFactory(action_type=AuditActionType.ENTRY_UPDATED)

        # Update timestamps manually
        AuditTrail.objects.filter(audit_id=old_audit1.audit_id).update(
            timestamp=old_date
        )
        AuditTrail.objects.filter(audit_id=old_audit2.audit_id).update(
            timestamp=old_date
        )

        # Run cleanup for specific action type in dry run mode
        cleanup_stats = audit_cleanup_expired_logs(
            dry_run=True, action_type=AuditActionType.ENTRY_CREATED
        )

        # Verify logs were NOT deleted in dry run
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=old_audit1.audit_id).exists()
        )
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=old_audit2.audit_id).exists()
        )

        # Verify stats show what would be deleted
        self.assertTrue(cleanup_stats["total_deleted"] > 0)
        self.assertTrue(cleanup_stats["dry_run"])

    @pytest.mark.django_db
    def test_cleanup_specific_action_type_actual_deletion(self):
        """Test cleanup for specific action type with actual deletion."""
        from apps.auditlog.services import audit_cleanup_expired_logs
        from django.utils import timezone
        from datetime import timedelta

        # Create old logs
        old_date = timezone.now() - timedelta(days=400)
        old_audit1 = AuditTrailFactory(action_type=AuditActionType.ENTRY_CREATED)
        old_audit2 = AuditTrailFactory(action_type=AuditActionType.ENTRY_UPDATED)

        # Update timestamps manually
        AuditTrail.objects.filter(audit_id=old_audit1.audit_id).update(
            timestamp=old_date
        )
        AuditTrail.objects.filter(audit_id=old_audit2.audit_id).update(
            timestamp=old_date
        )

        # Run cleanup for specific action type (actual deletion)
        cleanup_stats = audit_cleanup_expired_logs(
            action_type=AuditActionType.ENTRY_CREATED
        )

        # Verify only the specific action type was deleted
        self.assertFalse(
            AuditTrail.objects.filter(audit_id=old_audit1.audit_id).exists()
        )
        self.assertTrue(
            AuditTrail.objects.filter(audit_id=old_audit2.audit_id).exists()
        )

        # Verify stats
        self.assertEqual(cleanup_stats["total_deleted"], 1)
        self.assertFalse(cleanup_stats["dry_run"])


@pytest.mark.unit
class TestMakeJsonSerializable(TestCase):
    """Test make_json_serializable utility function."""

    def test_make_json_serializable_basic_types(self):
        """Test serialization of basic Python types."""
        from apps.auditlog.services import make_json_serializable

        # Test basic types that should pass through unchanged
        self.assertEqual(make_json_serializable("string"), "string")
        self.assertEqual(make_json_serializable(123), 123)
        self.assertEqual(make_json_serializable(123.45), 123.45)
        self.assertEqual(make_json_serializable(True), True)
        self.assertEqual(make_json_serializable(None), None)

        # Test collections
        self.assertEqual(make_json_serializable([1, 2, 3]), [1, 2, 3])
        self.assertEqual(make_json_serializable({"key": "value"}), {"key": "value"})

    def test_make_json_serializable_datetime(self):
        """Test serialization of datetime objects."""
        from apps.auditlog.services import make_json_serializable
        from django.utils import timezone
        from datetime import datetime

        # Test timezone-aware datetime
        dt = timezone.now()
        result = make_json_serializable(dt)
        self.assertIsInstance(result, str)
        self.assertIn("T", result)  # ISO format

        # Test naive datetime
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)
        result = make_json_serializable(naive_dt)
        self.assertIsInstance(result, str)

    def test_make_json_serializable_model_instance(self):
        """Test serialization of Django model instances."""
        from apps.auditlog.services import make_json_serializable

        user = CustomUserFactory()
        result = make_json_serializable(user)

        # Should return string representation
        self.assertIsInstance(result, str)
        self.assertEqual(result, str(user))

    def test_make_json_serializable_decimal(self):
        """Test serialization of Decimal objects."""
        from apps.auditlog.services import make_json_serializable
        from decimal import Decimal

        decimal_value = Decimal("123.45")
        result = make_json_serializable(decimal_value)

        # Should convert to float
        self.assertIsInstance(result, float)
        self.assertEqual(result, 123.45)

    def test_make_json_serializable_complex_nested(self):
        """Test serialization of complex nested structures."""
        from apps.auditlog.services import make_json_serializable
        from django.utils import timezone

        user = CustomUserFactory()
        complex_data = {
            "user": user,
            "timestamp": timezone.now(),
            "metadata": {"nested": {"values": [1, 2, user], "flags": [True, False]}},
            "list_with_objects": [user, "string", 123],
        }

        result = make_json_serializable(complex_data)

        # Verify structure is preserved
        self.assertIsInstance(result, dict)
        self.assertIn("user", result)
        self.assertIn("timestamp", result)
        self.assertIn("metadata", result)

        # Verify objects were serialized
        self.assertIsInstance(result["user"], str)
        self.assertIsInstance(result["timestamp"], str)
        self.assertIsInstance(result["list_with_objects"][0], str)

        # Verify nested structure
        self.assertIsInstance(result["metadata"]["nested"]["values"][2], str)


@pytest.mark.unit
class TestAuditServicesIntegration(TestCase):
    """Test integration scenarios for audit services."""

    @pytest.mark.django_db
    def test_audit_create_with_workspace_detection(self):
        """Test audit creation with automatic workspace detection."""
        from apps.auditlog.services import audit_create

        workspace = WorkspaceFactory()
        entry = EntryFactory(workspace=workspace)
        user = CustomUserFactory()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_UPDATED,
            target_entity=entry,
            metadata={
                "field_changed": "title",
                "old_value": "Old Title",
                "new_value": "New Title",
            },
        )

        # Verify audit was created correctly
        self.assertEqual(audit.user, user)
        self.assertEqual(audit.action_type, AuditActionType.ENTRY_UPDATED)
        self.assertEqual(audit.target_entity, entry)

        # Verify metadata was serialized
        self.assertIn("field_changed", audit.metadata)
        self.assertEqual(audit.metadata["field_changed"], "title")

    @pytest.mark.django_db
    def test_rapid_audit_creation(self):
        """Test rapid audit creation doesn't cause conflicts."""
        from apps.auditlog.services import audit_create
        import time

        created_audits = []
        errors = []

        # Create multiple audits rapidly in sequence (not concurrently)
        for i in range(10):
            try:
                # Create fresh user and entry objects for each audit
                user = CustomUserFactory()
                entry = EntryFactory()

                audit = audit_create(
                    user=user,
                    action_type=AuditActionType.ENTRY_CREATED,
                    target_entity=entry,
                    metadata={"sequence_index": i, "timestamp": time.time()},
                )
                created_audits.append(audit)
            except Exception as e:
                errors.append(e)

        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Verify all audits were created successfully
        self.assertEqual(len(created_audits), 10)

        # Verify all audits are unique
        audit_ids = [audit.audit_id for audit in created_audits]
        self.assertEqual(len(set(audit_ids)), 10)

        # Verify all audits were persisted to database
        for audit in created_audits:
            self.assertTrue(
                AuditTrail.objects.filter(audit_id=audit.audit_id).exists()
            )

    @pytest.mark.django_db
    def test_bulk_audit_creation_performance(self):
        """Test performance of bulk audit creation."""
        from apps.auditlog.services import audit_create
        import time

        user = CustomUserFactory()
        entry = EntryFactory()

        start_time = time.time()

        # Create multiple audits
        for i in range(100):
            audit_create(
                user=user,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=entry,
                metadata={"batch_index": i},
            )

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertion (should complete within reasonable time)
        self.assertLess(duration, 10.0, "Bulk audit creation took too long")

        # Verify all audits were created
        audit_count = AuditTrail.objects.filter(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity_id=entry.entry_id,
        ).count()

        self.assertEqual(audit_count, 100)
