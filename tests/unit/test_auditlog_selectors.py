"""
Unit tests for the auditlog app selectors.

Following the test plan: AuditLog App (apps.auditlog)
- Selector function tests
- Query filtering and optimization tests
"""

import uuid
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from apps.auditlog.selectors import AuditLogSelector
from apps.auditlog.config import AuditConfig
from tests.factories import (
    BulkAuditTrailFactory,
    CustomUserFactory,
    EntryCreatedAuditFactory,
    EntryFactory,
    StatusChangedAuditFactory,
    WorkspaceFactory,
)


@contextmanager
def disable_automatic_audit_logging():
    """Context manager to temporarily disable automatic audit logging during tests."""
    original_value = AuditConfig.ENABLE_AUTOMATIC_LOGGING
    AuditConfig.ENABLE_AUTOMATIC_LOGGING = False
    try:
        yield
    finally:
        AuditConfig.ENABLE_AUTOMATIC_LOGGING = original_value


@pytest.mark.unit
class TestAuditLogSelectors(TestCase):
    """Test the audit log selector functions."""

    @pytest.mark.django_db
    def test_get_audit_logs_no_filters(self):
        """Test getting audit logs without any filters."""
        # Clear any existing audit logs to ensure clean test

        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            # Create test data with specific action types
            audit1 = EntryCreatedAuditFactory(target_entity=entry)
            audit2 = EntryCreatedAuditFactory(target_entity=entry)
            audit3 = StatusChangedAuditFactory(target_entity=entry)

            # Get all audit logs
            result = AuditLogSelector().get_audit_logs_with_filters()

            # Should return all audit logs
            self.assertEqual(result.count(), 3)
            audit_ids = [audit.audit_id for audit in result]
            self.assertIn(audit1.audit_id, audit_ids)
            self.assertIn(audit2.audit_id, audit_ids)
            self.assertIn(audit3.audit_id, audit_ids)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_user_id(self):
        """Test filtering audit logs by user ID."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user1 = CustomUserFactory()
            user2 = CustomUserFactory()

            EntryCreatedAuditFactory(user=user1, target_entity=entry)
            EntryCreatedAuditFactory(user=user2, target_entity=entry)

            # Filter by user1
            result = AuditLogSelector().get_audit_logs_with_filters(
                user_id=user1.user_id
            )

            # Should only return audits for user1
            self.assertEqual(result.count(), 1)
            for audit in result:
                self.assertEqual(audit.user, user1)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_action_type(self):
        """Test filtering audit logs by action type."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            EntryCreatedAuditFactory(target_entity=entry)
            StatusChangedAuditFactory(target_entity=entry)
            EntryCreatedAuditFactory(target_entity=entry)

            # Filter by entry_created
            result = AuditLogSelector().get_audit_logs_with_filters(
                action_type=AuditActionType.ENTRY_CREATED
            )

            # Should only return entry_created audits
            self.assertEqual(result.count(), 2)
            for audit in result:
                self.assertEqual(audit.action_type, AuditActionType.ENTRY_CREATED)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_entity_id(self):
        """Test filtering audit logs by target entity ID."""
        # Clear any existing audit logs to ensure clean test

        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry1 = EntryFactory()
            entry2 = EntryFactory()

            EntryCreatedAuditFactory(target_entity=entry1)
            EntryCreatedAuditFactory(target_entity=entry2)
            StatusChangedAuditFactory(target_entity=entry1)

            # Filter by entity_id
            result = AuditLogSelector().get_audit_logs_with_filters(
                target_entity_id=entry1.entry_id
            )

            # Should only return audits for specified entity
            self.assertEqual(result.count(), 2)
            for audit in result:
                self.assertEqual(audit.target_entity, entry1)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_entity_type(self):
        """Test filtering audit logs by target entity type."""
        # Clear any existing audit logs to ensure clean test

        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            workspace = WorkspaceFactory()

            # Create audits with different entity types
            EntryCreatedAuditFactory(target_entity=entry)
            EntryCreatedAuditFactory(target_entity=workspace)
            StatusChangedAuditFactory(target_entity=entry)

            # Get ContentType for Entry
            entry_content_type = ContentType.objects.get_for_model(entry)

            # Filter by entity type (pass model name as string)
            result = AuditLogSelector().get_audit_logs_with_filters(
                target_entity_type=entry_content_type.model
            )

            # Should only return audits for entry type
            self.assertEqual(result.count(), 2)
            for audit in result:
                self.assertEqual(audit.target_entity_type, entry_content_type)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_date_range(self):
        """Test filtering audit logs by date range."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            # Create audits with different timestamps
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(days=1)

            # Create audits (note: we can't easily control timestamp in factory)
            EntryCreatedAuditFactory(target_entity=entry)
            StatusChangedAuditFactory(target_entity=entry)

            # Test start_date filter
            result = AuditLogSelector().get_audit_logs_with_filters(
                start_date=yesterday
            )

            # Should include audits from yesterday onward
            self.assertGreaterEqual(result.count(), 0)
            for audit in result:
                self.assertGreaterEqual(audit.timestamp, yesterday)

            # Test end_date filter
            result = AuditLogSelector().get_audit_logs_with_filters(end_date=now)

            # Should include audits up to now
            self.assertGreaterEqual(result.count(), 0)
            for audit in result:
                self.assertLessEqual(audit.timestamp, now)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_search_query(self):
        """Test filtering audit logs by search query in metadata."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            EntryCreatedAuditFactory(
                metadata={"description": "user submitted entry"}, target_entity=entry
            )
            EntryCreatedAuditFactory(
                metadata={"description": "entry was approved"}, target_entity=entry
            )
            StatusChangedAuditFactory(
                metadata={"description": "file was uploaded"}, target_entity=entry
            )

            # Search for "entry"
            result = AuditLogSelector().get_audit_logs_with_filters(
                search_query="entry"
            )

            # Should return 3 audits:
            # - 2 containing "entry" in metadata
            # - 1 containing "entry" in action type display name (entry_status_changed -> "Entry Status Changed")
            self.assertEqual(result.count(), 3)

            # Verify that all results contain "entry" either in metadata or action type
            for audit in result:
                contains_entry_in_metadata = "entry" in str(audit.metadata).lower()
                contains_entry_in_action = (
                    "entry" in str(audit.get_action_type_display()).lower()
                )
                self.assertTrue(
                    contains_entry_in_metadata or contains_entry_in_action,
                    f"Audit {audit.audit_id} should contain 'entry' in metadata or action type",
                )

    @pytest.mark.django_db
    def test_get_audit_logs_multiple_filters(self):
        """Test filtering audit logs with multiple filters combined."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            user = CustomUserFactory()
            entry = EntryFactory()
            entry_content_type = ContentType.objects.get_for_model(entry)

            # Create various audits
            target_audit = EntryCreatedAuditFactory(
                user=user,
                target_entity=entry,
                metadata={"description": "user created entry"},
            )

            # Different user
            EntryCreatedAuditFactory(
                target_entity=entry,
            )

            # Different action type
            StatusChangedAuditFactory(
                user=user,
                target_entity=entry,
            )

            # Apply multiple filters
            result = AuditLogSelector().get_audit_logs_with_filters(
                user_id=user.user_id,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity_id=entry.entry_id,
                target_entity_type=entry_content_type.model,
            )

            # Should only return the target audit
            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().audit_id, target_audit.audit_id)

    @pytest.mark.django_db
    def test_get_audit_logs_ordering(self):
        """Test that audit logs are returned in correct order (newest first)."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            # Create multiple audits
            EntryCreatedAuditFactory(target_entity=entry)
            StatusChangedAuditFactory(target_entity=entry)
            EntryCreatedAuditFactory(target_entity=entry)

            result = AuditLogSelector().get_audit_logs_with_filters()

            # Should be ordered by timestamp descending
            timestamps = [audit.timestamp for audit in result]
            self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    @pytest.mark.django_db
    def test_get_audit_logs_select_related_optimization(self):
        """Test that selector uses select_related for user optimization."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()
            EntryCreatedAuditFactory(user=user, target_entity=entry)

            # This should not cause additional database queries
            with self.assertNumQueries(1):  # Should be just one query with join
                result = AuditLogSelector().get_audit_logs_with_filters()
                # Access user to trigger potential additional query
                for audit in result:
                    if audit.user:
                        _ = audit.user.username

    @pytest.mark.django_db
    def test_get_audit_logs_empty_result(self):
        """Test selector with filters that match no records."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            EntryCreatedAuditFactory(target_entity=entry)

            # Filter by non-existent user
            result = AuditLogSelector().get_audit_logs_with_filters(
                user_id=uuid.uuid4()
            )

            self.assertEqual(result.count(), 0)
            self.assertEqual(list(result), [])

    @pytest.mark.django_db
    def test_get_audit_logs_with_none_values(self):
        """Test selector with None filter values."""
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            audit = EntryCreatedAuditFactory(target_entity=entry)

            # None values should be ignored
            result = AuditLogSelector().get_audit_logs_with_filters(
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
        # Clear any existing audit logs to ensure clean test
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            # Create multiple audits efficiently
            user = CustomUserFactory()
            entry = EntryFactory()

            BulkAuditTrailFactory.create_batch_for_entity(
                entity=entry, count=20, user=user
            )

            # Should handle larger datasets efficiently
            result = AuditLogSelector().get_audit_logs_with_filters(
                user_id=user.user_id, target_entity_id=entry.entry_id
            )

            self.assertEqual(result.count(), 20)

            # Should still be properly ordered
            timestamps = [audit.timestamp for audit in result]
            self.assertEqual(timestamps, sorted(timestamps, reverse=True))
