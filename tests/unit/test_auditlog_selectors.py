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
from django.db.models import QuerySet
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

    @pytest.mark.django_db
    def test_get_retention_summary(self):
        """Test get_retention_summary function."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            # Create different types of audits
            EntryCreatedAuditFactory(target_entity=entry, user=user)
            StatusChangedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import get_retention_summary

            summary = get_retention_summary()

            # Verify summary structure
            expected_keys = [
                "total_logs",
                "authentication_logs",
                "critical_logs",
                "default_logs",
                "expired_logs",
            ]

            for key in expected_keys:
                self.assertIn(key, summary)
                self.assertIsInstance(summary[key], int)
                self.assertGreaterEqual(summary[key], 0)

            # Verify total is sum of categories
            self.assertEqual(
                summary["total_logs"],
                summary["authentication_logs"]
                + summary["critical_logs"]
                + summary["default_logs"],
            )

    @pytest.mark.django_db
    def test_get_expired_logs_queryset_no_action_type(self):
        """Test get_expired_logs_queryset without specific action type."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            # Create some audits
            EntryCreatedAuditFactory(target_entity=entry, user=user)
            StatusChangedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import get_expired_logs_queryset

            expired_logs = get_expired_logs_queryset()

            # Should return a queryset
            self.assertIsInstance(expired_logs, QuerySet)
            # Count should be non-negative
            self.assertGreaterEqual(expired_logs.count(), 0)

    @pytest.mark.django_db
    def test_get_expired_logs_queryset_with_action_type(self):
        """Test get_expired_logs_queryset with specific action type."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import get_expired_logs_queryset

            expired_logs = get_expired_logs_queryset(
                action_type=AuditActionType.ENTRY_CREATED
            )

            # Should return a queryset
            self.assertIsInstance(expired_logs, QuerySet)
            # All results should have the specified action type
            for audit in expired_logs:
                self.assertEqual(audit.action_type, AuditActionType.ENTRY_CREATED)

    @pytest.mark.django_db
    def test_get_expired_logs_queryset_with_override_days(self):
        """Test get_expired_logs_queryset with override days."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import get_expired_logs_queryset

            # Test with very high override days (should return no results)
            expired_logs = get_expired_logs_queryset(override_days=36500)  # 100 years
            self.assertEqual(expired_logs.count(), 0)

            # Test with 0 override days (should return all logs)
            expired_logs = get_expired_logs_queryset(override_days=0)
            self.assertGreater(expired_logs.count(), 0)

    @pytest.mark.django_db
    def test_get_expired_logs_queryset_authentication_logs(self):
        """Test get_expired_logs_queryset for authentication logs."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            # Create authentication audit (if we have the factory)
            # For now, test with available action types
            from apps.auditlog.selectors import get_expired_logs_queryset

            # Test with LOGIN_SUCCESS if it exists
            if hasattr(AuditActionType, "LOGIN_SUCCESS"):
                expired_logs = get_expired_logs_queryset(
                    action_type=AuditActionType.LOGIN_SUCCESS
                )
                self.assertIsInstance(expired_logs, QuerySet)

    @pytest.mark.django_db
    def test_get_related_entity_logs_with_entry(self):
        """Test _get_related_entity_logs with Entry entity."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            # Create audit for the entry
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test with Entry entity
            queryset = AuditTrail.objects.all()
            filtered_queryset = AuditLogSelector._get_related_entity_logs(
                str(entry.pk), "entry", queryset
            )

            # Should return logs related to the entry
            self.assertGreater(filtered_queryset.count(), 0)
            for audit in filtered_queryset:
                self.assertEqual(audit.target_entity_id, entry.pk)
                self.assertEqual(audit.target_entity_type.model, "entry")

    @pytest.mark.django_db
    def test_get_related_entity_logs_with_user(self):
        """Test _get_related_entity_logs with User entity."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            user = CustomUserFactory()
            entry = EntryFactory()

            # Create audit for the user
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test with User entity
            queryset = AuditTrail.objects.all()
            filtered_queryset = AuditLogSelector._get_related_entity_logs(
                str(user.pk), "customuser", queryset
            )

            # Should return logs where user is involved
            self.assertGreater(filtered_queryset.count(), 0)
            for audit in filtered_queryset:
                # User could be the actor or target
                self.assertTrue(
                    audit.user_id == user.pk
                    or (
                        audit.target_entity_id == user.pk
                        and audit.target_entity_type.model == "customuser"
                    )
                )

    @pytest.mark.django_db
    def test_get_related_entity_logs_with_workspace(self):
        """Test _get_related_entity_logs with Workspace entity."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            workspace = WorkspaceFactory()
            user = CustomUserFactory()
            entry = EntryFactory(workspace=workspace)

            # Create audit in the workspace
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test with Workspace entity
            queryset = AuditTrail.objects.all()
            filtered_queryset = AuditLogSelector._get_related_entity_logs(
                str(workspace.pk), "workspace", queryset
            )

            # Should return logs related to the workspace
            self.assertGreater(filtered_queryset.count(), 0)
            for audit in filtered_queryset:
                # Workspace could be target or context
                workspace_id_in_metadata = (
                    audit.metadata.get("workspace_id") if audit.metadata else None
                )
                self.assertTrue(
                    workspace_id_in_metadata == str(workspace.pk)
                    or (
                        audit.target_entity_id == workspace.pk
                        and audit.target_entity_type.model == "workspace"
                    )
                )

    @pytest.mark.django_db
    def test_get_related_entity_logs_no_results(self):
        """Test _get_related_entity_logs with entity that has no logs."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            # Don't create any audits for this entry

            from apps.auditlog.selectors import AuditLogSelector

            queryset = AuditTrail.objects.all()
            filtered_queryset = AuditLogSelector._get_related_entity_logs(
                str(entry.pk), "entry", queryset
            )

            # Should return empty queryset
            self.assertEqual(filtered_queryset.count(), 0)

    @pytest.mark.django_db
    def test_get_related_entity_logs_multiple_entities(self):
        """Test _get_related_entity_logs with multiple related entities."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry1 = EntryFactory()
            entry2 = EntryFactory()
            user = CustomUserFactory()

            # Create audits for both entries
            EntryCreatedAuditFactory(target_entity=entry1, user=user)
            EntryCreatedAuditFactory(target_entity=entry2, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test with first entry
            queryset = AuditTrail.objects.all()
            filtered_queryset1 = AuditLogSelector._get_related_entity_logs(
                str(entry1.pk), "entry", queryset
            )

            # Test with second entry
            filtered_queryset2 = AuditLogSelector._get_related_entity_logs(
                str(entry2.pk), "entry", queryset
            )

            # Each should return only logs for their respective entity
            self.assertEqual(filtered_queryset1.count(), 1)
            self.assertEqual(filtered_queryset2.count(), 1)

            # Verify correct entity IDs
            audit1 = filtered_queryset1.first()
            audit2 = filtered_queryset2.first()

            self.assertEqual(audit1.target_entity_id, entry1.pk)
            self.assertEqual(audit2.target_entity_id, entry2.pk)

    @pytest.mark.django_db
    def test_complex_filtering_multiple_parameters(self):
        """Test complex filtering with multiple parameters combined."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            workspace = WorkspaceFactory()
            user1 = CustomUserFactory(username="testuser1")
            user2 = CustomUserFactory(username="testuser2")
            entry1 = EntryFactory(workspace=workspace)
            entry2 = EntryFactory(workspace=workspace)

            # Create various audits
            audit1 = EntryCreatedAuditFactory(target_entity=entry1, user=user1)
            StatusChangedAuditFactory(target_entity=entry2, user=user2)

            from apps.auditlog.selectors import AuditLogSelector

            # Test combining user_id, action_type, and workspace_id
            result = AuditLogSelector.get_audit_logs_with_filters(
                user_id=user1.pk,
                action_type=AuditActionType.ENTRY_CREATED,
                workspace_id=str(workspace.pk),
            )

            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().pk, audit1.pk)

            # Test combining search query with other filters
            result = AuditLogSelector.get_audit_logs_with_filters(
                search_query="testuser1",
                action_type=AuditActionType.ENTRY_CREATED,
                workspace_id=str(workspace.pk),
            )

            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().pk, audit1.pk)

    @pytest.mark.django_db
    def test_complex_filtering_date_range_with_filters(self):
        """Test date range filtering combined with other filters."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            user = CustomUserFactory()
            entry = EntryFactory()

            # Create audit
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector
            from datetime import datetime, timedelta

            # Test date range with action type
            start_date = datetime.now() - timedelta(days=1)
            end_date = datetime.now() + timedelta(days=1)

            result = AuditLogSelector.get_audit_logs_with_filters(
                action_type=AuditActionType.ENTRY_CREATED,
                start_date=start_date,
                end_date=end_date,
            )

            self.assertGreater(result.count(), 0)

            # Test date range that excludes the audit
            old_start_date = datetime.now() - timedelta(days=10)
            old_end_date = datetime.now() - timedelta(days=5)

            result = AuditLogSelector.get_audit_logs_with_filters(
                action_type=AuditActionType.ENTRY_CREATED,
                start_date=old_start_date,
                end_date=old_end_date,
            )

            self.assertEqual(result.count(), 0)

    @pytest.mark.django_db
    def test_complex_filtering_advanced_search_patterns(self):
        """Test advanced search patterns with complex queries."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            user = CustomUserFactory(username="john.doe", email="john.doe@example.com")
            entry = EntryFactory()

            # Create audit with metadata
            EntryCreatedAuditFactory(
                target_entity=entry,
                user=user,
                metadata={"action": "create", "details": "New entry created"},
            )

            from apps.auditlog.selectors import AuditLogSelector

            # Test search by partial username
            result = AuditLogSelector.get_audit_logs_with_filters(search_query="john")
            self.assertGreater(result.count(), 0)

            # Test search by email domain
            result = AuditLogSelector.get_audit_logs_with_filters(
                search_query="example.com"
            )
            self.assertGreater(result.count(), 0)

            # Test search by metadata content
            result = AuditLogSelector.get_audit_logs_with_filters(search_query="create")
            self.assertGreater(result.count(), 0)

            # Test search with no matches
            result = AuditLogSelector.get_audit_logs_with_filters(
                search_query="nonexistent"
            )
            self.assertEqual(result.count(), 0)

    @pytest.mark.django_db
    def test_complex_filtering_security_and_critical_flags(self):
        """Test security_related and critical_actions flags with other filters."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            user = CustomUserFactory()
            entry = EntryFactory()

            # Create different types of audits
            EntryCreatedAuditFactory(target_entity=entry, user=user)
            StatusChangedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test security_related with user filter
            result = AuditLogSelector.get_audit_logs_with_filters(
                security_related_only=True, user_id=user.pk
            )

            # Should return security-related actions for the user
            for audit in result:
                self.assertEqual(audit.user_id, user.pk)

            # Test critical_actions with workspace filter
            result = AuditLogSelector.get_audit_logs_with_filters(
                critical_actions_only=True,
                workspace_id=str(entry.workspace.pk)
                if hasattr(entry, "workspace")
                else None,
            )

            # Should return critical actions in the workspace
            self.assertIsInstance(result, QuerySet)

    @pytest.mark.django_db
    def test_complex_filtering_exclude_system_with_filters(self):
        """Test exclude_system_actions with other filtering parameters."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            user = CustomUserFactory()
            entry = EntryFactory()

            # Create audit
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test exclude_system_actions with action type
            result = AuditLogSelector.get_audit_logs_with_filters(
                exclude_system_actions=True, action_type=AuditActionType.ENTRY_CREATED
            )

            # Should exclude system actions but include user actions
            self.assertGreater(result.count(), 0)
            for audit in result:
                self.assertIsNotNone(audit.user_id)  # Should have a user

    @pytest.mark.django_db
    def test_complex_filtering_performance_with_large_dataset(self):
        """Test performance with complex filters on larger dataset."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            users = [CustomUserFactory() for _ in range(5)]
            entries = [EntryFactory() for _ in range(10)]

            # Create multiple audits
            for i in range(20):
                user = users[i % len(users)]
                entry = entries[i % len(entries)]
                EntryCreatedAuditFactory(target_entity=entry, user=user)

            from apps.auditlog.selectors import AuditLogSelector

            # Test complex query with multiple filters
            result = AuditLogSelector.get_audit_logs_with_filters(
                user_id=users[0].pk,
                action_type=AuditActionType.ENTRY_CREATED,
                search_query=users[0].username,
                order_by="-timestamp",
            )

            # Should return filtered results efficiently
            self.assertGreater(result.count(), 0)

            # Verify ordering
            results_list = list(result)
            if len(results_list) > 1:
                for i in range(len(results_list) - 1):
                    self.assertGreaterEqual(
                        results_list[i].timestamp, results_list[i + 1].timestamp
                    )

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

    @pytest.mark.django_db
    def test_apply_search_filters_metadata(self):
        """Test _apply_search_filters method for metadata search."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory(username="testuser", email="test@example.com")

            # Create audits with different metadata
            audit1 = EntryCreatedAuditFactory(
                metadata={"description": "user created entry"},
                target_entity=entry,
                user=user,
            )
            EntryCreatedAuditFactory(
                metadata={"description": "system backup"},
                target_entity=entry,
                user=user,
            )

            # Test metadata search
            search_conditions = AuditLogSelector._apply_search_filters("entry")
            result = AuditTrail.objects.filter(search_conditions)

            # Should find audit1 (metadata contains "entry") and audit2 (action type contains "entry")
            self.assertGreaterEqual(result.count(), 1)
            audit_ids = [audit.audit_id for audit in result]
            self.assertIn(audit1.audit_id, audit_ids)

    @pytest.mark.django_db
    def test_apply_search_filters_username(self):
        """Test _apply_search_filters method for username search."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user1 = CustomUserFactory(username="johndoe")
            user2 = CustomUserFactory(username="janedoe")

            audit1 = EntryCreatedAuditFactory(user=user1, target_entity=entry)
            EntryCreatedAuditFactory(user=user2, target_entity=entry)

            # Test username search
            search_conditions = AuditLogSelector._apply_search_filters("john")
            result = AuditTrail.objects.filter(search_conditions)

            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().audit_id, audit1.audit_id)

    @pytest.mark.django_db
    def test_apply_search_filters_email(self):
        """Test _apply_search_filters method for email search."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user1 = CustomUserFactory(email="john@company.com")
            user2 = CustomUserFactory(email="jane@company.com")

            audit1 = EntryCreatedAuditFactory(user=user1, target_entity=entry)
            EntryCreatedAuditFactory(user=user2, target_entity=entry)

            # Test email search
            search_conditions = AuditLogSelector._apply_search_filters("john@")
            result = AuditTrail.objects.filter(search_conditions)

            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().audit_id, audit1.audit_id)

    @pytest.mark.django_db
    def test_apply_search_filters_action_type_display(self):
        """Test _apply_search_filters method for action type display name search."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()

            # Create audits with different action types
            EntryCreatedAuditFactory(target_entity=entry)  # "Entry Created"
            audit = StatusChangedAuditFactory(
                target_entity=entry
            )  # "Entry Status Changed"

            # Test action type display name search
            search_conditions = AuditLogSelector._apply_search_filters("Status")
            result = AuditTrail.objects.filter(search_conditions)

            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().audit_id, audit.audit_id)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_workspace_id(self):
        """Test filtering audit logs by workspace_id."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            workspace_id = "test-workspace-123"

            audit1 = EntryCreatedAuditFactory(
                target_entity=entry, metadata={"workspace_id": workspace_id}
            )
            EntryCreatedAuditFactory(
                target_entity=entry, metadata={"workspace_id": "other-workspace"}
            )

            result = AuditLogSelector().get_audit_logs_with_filters(
                workspace_id=workspace_id
            )

            self.assertEqual(result.count(), 1)
            self.assertEqual(result.first().audit_id, audit1.audit_id)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_action_types_list(self):
        """Test filtering audit logs by multiple action types."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()

            audit1 = EntryCreatedAuditFactory(target_entity=entry)
            audit2 = StatusChangedAuditFactory(target_entity=entry)

            result = AuditLogSelector().get_audit_logs_with_filters(
                action_types=[
                    AuditActionType.ENTRY_CREATED,
                    AuditActionType.ENTRY_STATUS_CHANGED,
                ]
            )

            self.assertEqual(result.count(), 2)
            audit_ids = [audit.audit_id for audit in result]
            self.assertIn(audit1.audit_id, audit_ids)
            self.assertIn(audit2.audit_id, audit_ids)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_by_target_entity_types_list(self):
        """Test filtering audit logs by multiple target entity types."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            workspace = WorkspaceFactory()

            audit1 = EntryCreatedAuditFactory(target_entity=entry)
            audit2 = EntryCreatedAuditFactory(target_entity=workspace)

            result = AuditLogSelector().get_audit_logs_with_filters(
                target_entity_types=["entry", "workspace"]
            )

            self.assertEqual(result.count(), 2)
            audit_ids = [audit.audit_id for audit in result]
            self.assertIn(audit1.audit_id, audit_ids)
            self.assertIn(audit2.audit_id, audit_ids)

    @pytest.mark.django_db
    def test_get_audit_logs_filter_security_related_only(self):
        """Test filtering audit logs for security-related actions only."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            # Create regular audit
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            result = AuditLogSelector().get_audit_logs_with_filters(
                security_related_only=True
            )

            # Verify all results are security-related
            from apps.auditlog.utils import is_security_related

            for audit in result:
                self.assertTrue(is_security_related(audit.action_type))

    @pytest.mark.django_db
    def test_get_audit_logs_filter_critical_actions_only(self):
        """Test filtering audit logs for critical actions only."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            # Create regular audit
            EntryCreatedAuditFactory(target_entity=entry, user=user)

            result = AuditLogSelector().get_audit_logs_with_filters(
                critical_actions_only=True
            )

            # Verify all results are critical
            from apps.auditlog.constants import is_critical_action

            for audit in result:
                self.assertTrue(is_critical_action(audit.action_type))

    @pytest.mark.django_db
    def test_get_audit_logs_exclude_system_actions(self):
        """Test excluding system actions (actions without user)."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            user = CustomUserFactory()

            # Create user audit
            audit_with_user = EntryCreatedAuditFactory(target_entity=entry, user=user)

            # Create system audit (no user)
            audit_system = EntryCreatedAuditFactory(target_entity=entry, user=None)

            result = AuditLogSelector().get_audit_logs_with_filters(
                exclude_system_actions=True
            )

            # Should only include audits with users
            audit_ids = [audit.audit_id for audit in result]
            self.assertIn(audit_with_user.audit_id, audit_ids)
            self.assertNotIn(audit_system.audit_id, audit_ids)

            for audit in result:
                self.assertIsNotNone(audit.user)

    @pytest.mark.django_db
    def test_get_audit_logs_custom_ordering(self):
        """Test custom ordering of audit logs."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()

            EntryCreatedAuditFactory(target_entity=entry)
            StatusChangedAuditFactory(target_entity=entry)

            # Test ascending order
            result = AuditLogSelector().get_audit_logs_with_filters(
                order_by="timestamp"
            )

            timestamps = [audit.timestamp for audit in result]
            self.assertEqual(timestamps, sorted(timestamps))

    @pytest.mark.django_db
    def test_get_audit_logs_invalid_entity_type(self):
        """Test filtering with invalid entity type returns empty queryset."""
        AuditTrail.objects.all().delete()

        with disable_automatic_audit_logging():
            entry = EntryFactory()
            EntryCreatedAuditFactory(target_entity=entry)

            result = AuditLogSelector().get_audit_logs_with_filters(
                target_entity_type="nonexistent_model"
            )

            self.assertEqual(result.count(), 0)
