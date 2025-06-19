"""
System and performance tests for AuditLog App.

Following the test plan: AuditLog App (apps.auditlog)
- Performance tests
- System integration tests
- Large dataset handling
"""

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.auditlog.models import AuditTrail
from apps.auditlog.selectors import get_audit_logs_for_workspace_with_filters
from apps.auditlog.services import audit_create
from tests.factories import (
    AuditTrailFactory,
    BulkAuditTrailFactory,
    CustomUserFactory,
    EntryFactory,
    OrganizationFactory,
    WorkspaceFactory,
)

User = get_user_model()


@pytest.mark.system
class TestAuditLogPerformance(TestCase):
    """Test audit log performance with realistic data volumes."""

    @pytest.mark.django_db
    def test_audit_creation_performance(self):
        """Test performance of audit creation under load."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Measure time for single audit creation
        start_time = time.time()
        audit_create(
            user=user,
            action_type="entry_created",
            target_entity=entry,
            metadata={"test": "performance"},
        )
        single_creation_time = time.time() - start_time

        # Single creation should be very fast
        self.assertLess(single_creation_time, 0.1)  # 100ms max

    @pytest.mark.django_db
    def test_bulk_audit_creation_performance(self):
        """Test performance of bulk audit creation."""
        user = CustomUserFactory()
        entries = [EntryFactory() for _ in range(1000)]

        # Measure bulk creation time
        start_time = time.time()

        audits = []
        for i, entry in enumerate(entries):
            audit = audit_create(
                user=user,
                action_type="entry_created",
                target_entity=entry,
                metadata={"sequence": i, "bulk_test": True},
            )
            audits.append(audit)

        bulk_creation_time = time.time() - start_time

        # Bulk creation should complete in reasonable time
        self.assertLess(bulk_creation_time, 30.0)  # 30 seconds max for 1000 audits

        # Verify all audits were created
        self.assertEqual(len(audits), 1000)

        # Verify they exist in database
        bulk_audits = get_audit_logs_for_workspace_with_filters(user_id=user.user_id)
        self.assertEqual(bulk_audits.count(), 1000)

    @pytest.mark.django_db
    def test_audit_querying_performance_small_dataset(self):
        """Test querying performance with small dataset."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create moderate dataset
        BulkAuditTrailFactory.create_batch(100, user=user, target_entity=entry)

        # Test basic query performance
        start_time = time.time()
        result = get_audit_logs_for_workspace_with_filters(user_id=user.user_id)
        list(result)  # Force evaluation
        query_time = time.time() - start_time

        # Should be very fast
        self.assertLess(query_time, 1.0)  # 1 second max

    @pytest.mark.django_db
    def test_audit_querying_performance_large_dataset(self):
        """Test querying performance with large dataset."""
        users = CustomUserFactory.create_batch(10)
        entries = [EntryFactory() for _ in range(5)]

        # Create large dataset across multiple users
        for user in users:
            for entry in entries:
                BulkAuditTrailFactory.create_batch(
                    40, user=user, target_entity=entry
                )  # 2000 total audits (10 users * 5 entries * 40 audits)

        # Test filtered query performance
        start_time = time.time()
        result = get_audit_logs_for_workspace_with_filters(
            user_id=users[0].user_id, action_type="entry_created"
        )
        list(result[:50])  # Get first 50 results
        query_time = time.time() - start_time

        # Should handle large dataset efficiently
        self.assertLess(query_time, 2.0)  # 2 seconds max

    @pytest.mark.django_db
    def test_complex_metadata_search_performance(self):
        """Test performance of metadata search with complex data."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create audits with complex metadata
        for i in range(500):
            complex_metadata = {
                "user_data": {
                    "username": f"user_{i}",
                    "permissions": ["read", "write", "execute"],
                    "profile": {
                        "email": f"user_{i}@example.com",
                        "department": "Engineering" if i % 2 == 0 else "Finance",
                    },
                },
                "action_details": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ip_address": f"192.168.1.{i % 255}",
                    "session_id": str(uuid.uuid4()),
                },
            }

            audit_create(
                user=user,
                action_type="entry_created",
                target_entity=entry,
                metadata=complex_metadata,
            )

        # Test metadata search performance
        start_time = time.time()
        result = get_audit_logs_for_workspace_with_filters(search_query="Engineering")
        matching_audits = list(result)
        search_time = time.time() - start_time

        # Should complete search in reasonable time
        self.assertLess(search_time, 3.0)  # 3 seconds max

        # Verify search results
        self.assertGreater(len(matching_audits), 0)
        for audit in matching_audits[:10]:  # Check first 10
            self.assertIn("Engineering", str(audit.metadata))

    @pytest.mark.django_db
    def test_date_range_filtering_performance(self):
        """Test performance of date range filtering."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create audits over time range
        base_time = datetime.now(timezone.utc)

        for i in range(300):
            # Create audit with timestamp offset
            audit = AuditTrailFactory(user=user, target_entity=entry)
            # Simulate different creation times by updating timestamp
            audit.timestamp = base_time - timedelta(hours=i)
            audit.save(update_fields=["timestamp"])

        # Test date range query performance
        start_date = base_time - timedelta(hours=100)
        end_date = base_time - timedelta(hours=50)

        start_time = time.time()
        result = get_audit_logs_for_workspace_with_filters(
            user_id=user.user_id, start_date=start_date, end_date=end_date
        )
        filtered_audits = list(result)
        filter_time = time.time() - start_time

        # Should filter efficiently
        self.assertLess(filter_time, 1.5)  # 1.5 seconds max

        # Verify results are within date range
        for audit in filtered_audits:
            self.assertGreaterEqual(audit.timestamp, start_date)
            self.assertLessEqual(audit.timestamp, end_date)

    @pytest.mark.django_db
    def test_concurrent_audit_creation_performance(self):
        """Test performance under concurrent audit creation simulation."""
        users = CustomUserFactory.create_batch(5)
        entries = [EntryFactory() for _ in range(10)]

        # Simulate concurrent creation
        start_time = time.time()

        all_audits = []
        for i in range(50):  # 50 rounds
            for user in users:
                entry = entries[i % 10]  # Cycle through available entries
                audit = audit_create(
                    user=user,
                    action_type="status_changed",
                    target_entity=entry,
                    metadata={
                        "round": i,
                        "user_sequence": user.username,
                        "concurrent_test": True,
                    },
                )
                all_audits.append(audit)

        concurrent_time = time.time() - start_time

        # Should handle concurrent-like creation efficiently
        self.assertLess(concurrent_time, 15.0)  # 15 seconds max
        self.assertEqual(len(all_audits), 250)


@pytest.mark.system
class TestAuditLogSystemIntegration(TestCase):
    """Test audit log system integration scenarios."""

    @pytest.mark.django_db
    def test_cross_app_audit_system_workflow(self):
        """Test system-wide audit logging workflow across apps."""
        # Simulate a complete business workflow with audit logging

        # Step 1: User registration (accounts app would log this)
        user = CustomUserFactory()
        audit_create(
            user=None,  # System action
            action_type="entry_created",  # Using available action
            target_entity=user,
            metadata={
                "action": "user_registered",
                "registration_method": "email",
                "ip_address": "192.168.1.100",
            },
        )

        # Step 2: Organization creation (organizations app would log this)
        organization = OrganizationFactory()
        audit_create(
            user=user,
            action_type="entry_created",
            target_entity=organization,
            metadata={
                "action": "organization_created",
                "org_name": "Test Organization",
                "owner": user.username,
            },
        )

        # Step 3: Workspace creation (workspaces app would log this)
        workspace = WorkspaceFactory(organization=organization)
        audit_create(
            user=user,
            action_type="entry_created",
            target_entity=workspace,
            metadata={
                "action": "workspace_created",
                "workspace_name": workspace.title,
                "organization_id": str(organization.organization_id),
            },
        )

        # Step 4: Entry submission (entries app would log this)
        entry = EntryFactory(workspace=workspace)
        audit_create(
            user=user,
            action_type="entry_created",
            target_entity=entry,
            metadata={
                "amount": "1500.00",
                "entry_type": "income",
                "organization_id": str(organization.organization_id),
                "workspace_id": str(workspace.workspace_id),
            },
        )

        # Step 5: File attachment (attachments app would log this)
        # For now, we use Entry as a fallback since we don't have a dedicated Attachment model
        file_entry = EntryFactory(workspace=workspace)
        audit_create(
            user=user,
            action_type="file_uploaded",
            target_entity=file_entry,
            metadata={
                "filename": "receipt.pdf",
                "file_size": "2048",
                "entry_id": str(entry.entry_id),
            },
        )

        # Step 6: Entry review (entries app would log this)
        reviewer = CustomUserFactory()
        audit_create(
            user=reviewer,
            action_type="status_changed",
            target_entity=entry,
            metadata={
                "old_status": "submitted",
                "new_status": "approved",
                "reviewer": reviewer.username,
                "review_notes": "Approved with attachments",
            },
        )

        # Verify complete system audit trail
        all_audits = get_audit_logs_for_workspace_with_filters()
        self.assertEqual(all_audits.count(), 6)

        # Verify workflow relationships
        user_audits = get_audit_logs_for_workspace_with_filters(user_id=user.user_id)
        self.assertEqual(user_audits.count(), 4)  # User performed 4 actions

        entry_audits = get_audit_logs_for_workspace_with_filters(
            target_entity_id=entry.entry_id
        )
        self.assertEqual(entry_audits.count(), 2)  # Entry had 2 actions

    @pytest.mark.django_db
    def test_audit_log_data_integrity_under_stress(self):
        """Test data integrity under stress conditions."""
        users = CustomUserFactory.create_batch(3)
        entries = [EntryFactory() for _ in range(10)]

        # Create complex interwoven audit trail
        audit_count = 0
        for round_num in range(20):
            for user in users:
                for entry in entries[:5]:  # Only use first 5 entities
                    audit_create(
                        user=user,
                        action_type="status_changed",
                        target_entity=entry,
                        metadata={
                            "round": round_num,
                            "user_id": str(user.user_id),
                            "entity_sequence": str(entry.entry_id),
                            "stress_test": True,
                        },
                    )
                    audit_count += 1

        # Verify data integrity
        total_audits = AuditTrail.objects.count()
        self.assertEqual(
            total_audits, audit_count
        )  # 3 users * 5 entities * 20 rounds = 300

        # Verify relationships remain intact
        for user in users:
            user_audit_count = get_audit_logs_for_workspace_with_filters(
                user_id=user.user_id
            ).count()
            self.assertEqual(
                user_audit_count, 100
            )  # 5 entities * 20 rounds = 100 per user

        for entry in entries[:5]:
            entity_audit_count = get_audit_logs_for_workspace_with_filters(
                target_entity_id=entry.entry_id
            ).count()
            self.assertEqual(
                entity_audit_count, 60
            )  # 3 users * 20 rounds = 60 per entity

    @pytest.mark.django_db
    def test_audit_log_database_optimization(self):
        """Test that database queries are optimized."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create test data
        BulkAuditTrailFactory.create_batch(50, user=user, target_entity=entry)

        # Test that selector uses proper optimization
        with self.assertNumQueries(1):  # Should be single query with join
            result = get_audit_logs_for_workspace_with_filters(user_id=user.user_id)

            # Access related user data to test select_related
            for audit in result[:10]:
                if audit.user:
                    _ = audit.user.username
                    _ = audit.user.email

    @pytest.mark.django_db
    def test_large_metadata_storage_and_retrieval(self):
        """Test storage and retrieval of large metadata objects."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create audit with very large metadata
        large_metadata = {
            "large_description": "x" * 50000,  # 50KB text
            "nested_structure": {
                "level_1": {
                    f"item_{i}": {
                        "data": f"value_{i}" * 100,
                        "nested": {"deep_data": f"deep_{i}" * 50},
                    }
                    for i in range(200)
                }
            },
            "array_data": [
                {
                    "id": i,
                    "name": f"item_{i}",
                    "description": f"desc_{i}" * 20,
                    "tags": [f"tag_{j}" for j in range(10)],
                }
                for i in range(100)
            ],
        }

        # Create audit with large metadata
        audit = audit_create(
            user=user,
            action_type="entry_created",
            target_entity=entry,
            metadata=large_metadata,
        )

        # Verify storage
        self.assertIsNotNone(audit.audit_id)

        # Verify retrieval
        retrieved_audit = AuditTrail.objects.get(audit_id=audit.audit_id)
        self.assertEqual(len(retrieved_audit.metadata["large_description"]), 50000)
        self.assertEqual(
            len(retrieved_audit.metadata["nested_structure"]["level_1"]), 200
        )
        self.assertEqual(len(retrieved_audit.metadata["array_data"]), 100)

        # Verify searchability of large metadata
        search_result = get_audit_logs_for_workspace_with_filters(
            search_query="item_50"
        )
        self.assertEqual(search_result.count(), 1)


@pytest.mark.system
class TestAuditLogScalability(TestCase):
    """Test audit log scalability scenarios."""

    @pytest.mark.django_db
    def test_pagination_performance_large_dataset(self):
        """Test pagination performance with large datasets."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create large dataset
        BulkAuditTrailFactory.create_batch(1000, user=user, target_entity=entry)

        # Test pagination performance
        page_times = []

        for page in range(1, 6):  # Test first 5 pages
            start_time = time.time()

            # Simulate pagination (get 20 items starting from offset)
            offset = (page - 1) * 20
            result = get_audit_logs_for_workspace_with_filters(user_id=user.user_id)
            page_data = list(result[offset : offset + 20])

            page_time = time.time() - start_time
            page_times.append(page_time)

            # Verify page contains expected number of items
            self.assertEqual(len(page_data), 20)

        # All pages should load in reasonable time
        for page_time in page_times:
            self.assertLess(page_time, 1.0)  # 1 second max per page

        # Performance should be consistent across pages
        max_time = max(page_times)
        min_time = min(page_times)
        self.assertLess(max_time - min_time, 0.5)  # Variance should be < 0.5 seconds

    @pytest.mark.django_db
    def test_memory_efficiency_large_queryset(self):
        """Test memory efficiency when handling large querysets."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create large dataset
        BulkAuditTrailFactory.create_batch(500, user=user, target_entity=entry)

        # Test that we can iterate through large queryset without loading everything
        result = get_audit_logs_for_workspace_with_filters(user_id=user.user_id)

        # Process in chunks to test memory efficiency
        processed_count = 0
        chunk_size = 50

        # This should not load all 500 records into memory at once
        for i in range(0, 500, chunk_size):
            chunk = list(result[i : i + chunk_size])
            processed_count += len(chunk)

            # Verify chunk size (except possibly the last chunk)
            expected_chunk_size = min(chunk_size, 500 - i)
            self.assertEqual(len(chunk), expected_chunk_size)

        # Verify we processed all records
        self.assertEqual(processed_count, 500)

    @pytest.mark.django_db
    def test_index_effectiveness(self):
        """Test that database indexes are effective."""
        users = CustomUserFactory.create_batch(10)
        entries = [EntryFactory() for _ in range(3)]
        content_types = [ContentType.objects.get_for_model(entry) for entry in entries]

        # Create data that will test index effectiveness
        for user in users:
            for action_type in ["entry_created", "status_changed", "flagged"]:
                for i, entry in enumerate(entries):
                    BulkAuditTrailFactory.create_batch(
                        10,
                        user=user,
                        action_type=action_type,
                        target_entity=entry,
                    )

        # Test queries that should benefit from indexes
        test_queries = [
            # Test user index
            lambda: get_audit_logs_for_workspace_with_filters(user_id=users[0].user_id),
            # Test action_type index
            lambda: get_audit_logs_for_workspace_with_filters(
                action_type="entry_created"
            ),
            # Test entity_type index
            lambda: get_audit_logs_for_workspace_with_filters(
                target_entity_type=content_types[0]
            ),
            # Test combined filters (should use multiple indexes)
            lambda: get_audit_logs_for_workspace_with_filters(
                user_id=users[0].user_id,
                action_type="entry_created",
                target_entity_id=entries[0].entry_id,
                target_entity_type=content_types[0],
            ),
        ]

        for query_func in test_queries:
            start_time = time.time()
            result = query_func()
            list(result[:100])  # Force evaluation of first 100 results
            query_time = time.time() - start_time

            # Indexed queries should be fast even with large dataset
            self.assertLess(query_time, 0.5)  # 0.5 seconds max
