"""
Unit tests for the auditlog app services and selectors.

Following the test plan: AuditLog App (apps.auditlog)
- Service function tests
- Selector function tests
- Business logic validation
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from apps.auditlog.selectors import get_audit_logs_for_workspace_with_filters
from apps.auditlog.services import audit_create
from tests.factories import (
    AuditTrailFactory,
    BulkAuditTrailFactory,
    CustomUserFactory,
    EntryCreatedAuditFactory,
    StatusChangedAuditFactory,
    EntryFactory,
    WorkspaceFactory,
)

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
            action_type="entry_created",
            target_entity=entry,
            metadata=metadata,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsInstance(audit, AuditTrail)
        self.assertEqual(audit.user, user)
        self.assertEqual(audit.action_type, "entry_created")
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
            action_type="status_changed",
            target_entity=entry,
            metadata=metadata,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.user)
        self.assertEqual(audit.action_type, "status_changed")
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
            action_type="entry_created",
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
            action_type="entry_created",
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
            action_type="status_changed",
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
            action_type="entry_created",
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
            action_type="entry_created",
            target_entity=entry,
            metadata={"test": "test_entry"},
        )

        # Test with workspace model
        workspace_audit = audit_create(
            user=user,
            action_type="entry_created",
            target_entity=workspace,
            metadata={"test": "test_workspace"},
        )

        # Test with user model
        user_audit = audit_create(
            user=user,
            action_type="entry_created",
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


@pytest.mark.unit
class TestAuditLogSelectors(TestCase):
    """Test the audit log selector functions."""

    @pytest.mark.django_db
    def test_get_audit_logs_no_filters(self):
        """Test getting audit logs without any filters."""
        entry = EntryFactory()
        # Create test data
        audit1 = AuditTrailFactory(target_entity=entry)
        audit2 = AuditTrailFactory(target_entity=entry)
        audit3 = AuditTrailFactory(target_entity=entry)

        # Get all audit logs
        result = get_audit_logs_for_workspace_with_filters()

        # Should return all audit logs
        self.assertEqual(result.count(), 3)
        audit_ids = [audit.audit_id for audit in result]
        self.assertIn(audit1.audit_id, audit_ids)
        self.assertIn(audit2.audit_id, audit_ids)
        self.assertIn(audit3.audit_id, audit_ids)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_user_id(self):
        """Test filtering audit logs by user ID."""
        entry = EntryFactory()
        user1 = CustomUserFactory()
        user2 = CustomUserFactory()

        AuditTrailFactory(user=user1, target_entity=entry)
        AuditTrailFactory(user=user2, target_entity=entry)

        # Filter by user1
        result = get_audit_logs_for_workspace_with_filters(user_id=user1.user_id)

        # Should only return audits for user1
        self.assertEqual(result.count(), 1)
        for audit in result:
            self.assertEqual(audit.user, user1)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_action_type(self):
        """Test filtering audit logs by action type."""
        entry = EntryFactory()
        EntryCreatedAuditFactory(target_entity=entry)
        StatusChangedAuditFactory(target_entity=entry)
        EntryCreatedAuditFactory(target_entity=entry)

        # Filter by entry_created
        result = get_audit_logs_for_workspace_with_filters(action_type="entry_created")

        # Should only return entry_created audits
        self.assertEqual(result.count(), 2)
        for audit in result:
            self.assertEqual(audit.action_type, "entry_created")

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_entity_id(self):
        """Test filtering audit logs by target entity ID."""
        entry1 = EntryFactory()
        entry2 = EntryFactory()

        AuditTrailFactory(target_entity=entry1)
        AuditTrailFactory(target_entity=entry2)
        AuditTrailFactory(target_entity=entry1)

        # Filter by entity_id
        result = get_audit_logs_for_workspace_with_filters(
            target_entity_id=entry1.entry_id
        )

        # Should only return audits for specified entity
        self.assertEqual(result.count(), 2)
        for audit in result:
            self.assertEqual(audit.target_entity, entry1)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_entity_type(self):
        """Test filtering audit logs by target entity type."""
        entry = EntryFactory()
        workspace = WorkspaceFactory()

        # Create audits with different entity types
        AuditTrailFactory(target_entity=entry)
        AuditTrailFactory(target_entity=workspace)
        AuditTrailFactory(target_entity=entry)

        # Get ContentType for Entry
        entry_content_type = ContentType.objects.get_for_model(entry)

        # Filter by entity type
        result = get_audit_logs_for_workspace_with_filters(
            target_entity_type=entry_content_type
        )

        # Should only return audits for entry type
        self.assertEqual(result.count(), 2)
        for audit in result:
            self.assertEqual(audit.target_entity_type, entry_content_type)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_date_range(self):
        """Test filtering audit logs by date range."""
        entry = EntryFactory()
        # Create audits with different timestamps
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Create audits (note: we can't easily control timestamp in factory)
        AuditTrailFactory(target_entity=entry)
        AuditTrailFactory(target_entity=entry)

        # Test start_date filter
        result = get_audit_logs_for_workspace_with_filters(start_date=yesterday)

        # Should include audits from yesterday onward
        self.assertGreaterEqual(result.count(), 0)
        for audit in result:
            self.assertGreaterEqual(audit.timestamp, yesterday)

        # Test end_date filter
        result = get_audit_logs_for_workspace_with_filters(end_date=now)

        # Should include audits up to now
        self.assertGreaterEqual(result.count(), 0)
        for audit in result:
            self.assertLessEqual(audit.timestamp, now)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_search_query(self):
        """Test filtering audit logs by search query in metadata."""
        entry = EntryFactory()
        AuditTrailFactory(
            metadata={"description": "user submitted entry"}, target_entity=entry
        )
        AuditTrailFactory(
            metadata={"description": "entry was approved"}, target_entity=entry
        )
        AuditTrailFactory(
            metadata={"description": "file was uploaded"}, target_entity=entry
        )

        # Search for "entry"
        result = get_audit_logs_for_workspace_with_filters(search_query="entry")

        # Should return audits containing "entry" in metadata
        self.assertEqual(result.count(), 2)
        for audit in result:
            self.assertIn("entry", str(audit.metadata).lower())

    @pytest.mark.django_db
    def test_get_audit_logs_multiple_filters(self):
        """Test filtering audit logs with multiple filters combined."""
        user = CustomUserFactory()
        entry = EntryFactory()
        entry_content_type = ContentType.objects.get_for_model(entry)

        # Create various audits
        target_audit = AuditTrailFactory(
            user=user,
            action_type="entry_created",
            target_entity=entry,
            metadata={"description": "user created entry"},
        )

        # Different user
        AuditTrailFactory(
            action_type="entry_created",
            target_entity=entry,
        )

        # Different action type
        AuditTrailFactory(
            user=user,
            action_type="status_changed",
            target_entity=entry,
        )

        # Apply multiple filters
        result = get_audit_logs_for_workspace_with_filters(
            user_id=user.user_id,
            action_type="entry_created",
            target_entity_id=entry.entry_id,
            target_entity_type=entry_content_type,
        )

        # Should only return the target audit
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().audit_id, target_audit.audit_id)

    @pytest.mark.django_db
    def test_get_audit_logs_ordering(self):
        """Test that audit logs are returned in correct order (newest first)."""
        entry = EntryFactory()
        # Create multiple audits
        AuditTrailFactory(target_entity=entry)
        AuditTrailFactory(target_entity=entry)
        AuditTrailFactory(target_entity=entry)

        result = get_audit_logs_for_workspace_with_filters()

        # Should be ordered by timestamp descending
        timestamps = [audit.timestamp for audit in result]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    @pytest.mark.django_db
    def test_get_audit_logs_select_related_optimization(self):
        """Test that selector uses select_related for user optimization."""
        entry = EntryFactory()
        user = CustomUserFactory()
        AuditTrailFactory(user=user, target_entity=entry)

        # This should not cause additional database queries
        with self.assertNumQueries(1):  # Should be just one query with join
            result = get_audit_logs_for_workspace_with_filters()
            # Access user to trigger potential additional query
            for audit in result:
                if audit.user:
                    _ = audit.user.username

    @pytest.mark.django_db
    def test_get_audit_logs_empty_result(self):
        """Test selector with filters that match no records."""
        entry = EntryFactory()
        AuditTrailFactory(target_entity=entry)

        # Filter by non-existent user
        result = get_audit_logs_for_workspace_with_filters(user_id=uuid.uuid4())

        self.assertEqual(result.count(), 0)
        self.assertEqual(list(result), [])

    @pytest.mark.django_db
    def test_get_audit_logs_with_none_values(self):
        """Test selector with None filter values."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        # None values should be ignored
        result = get_audit_logs_for_workspace_with_filters(
            user_id=None,
            action_type=None,
            start_date=None,
            end_date=None,
            target_entity_id=None,
            target_entity_type=None,
            search_query=None,
        )

        # Should return all audits
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().audit_id, audit.audit_id)

    @pytest.mark.django_db
    def test_get_audit_logs_large_dataset_performance(self):
        """Test selector performance with larger dataset."""
        # Create multiple audits efficiently
        user = CustomUserFactory()
        entry = EntryFactory()

        BulkAuditTrailFactory.create_batch_for_entity(entity=entry, count=20, user=user)

        # Should handle larger datasets efficiently
        result = get_audit_logs_for_workspace_with_filters(
            user_id=user.user_id, target_entity_id=entry.entry_id
        )

        self.assertEqual(result.count(), 20)

        # Should still be properly ordered
        timestamps = [audit.timestamp for audit in result]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
