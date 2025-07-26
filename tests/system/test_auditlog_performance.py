"""
System and performance tests for AuditLog App.

Following the test plan: AuditLog App (apps.auditlog)
- Performance tests
- System integration tests
- Large dataset handling
- Signal handler performance tests
- Business logger performance tests
- Concurrent audit logging tests
- Memory usage tests
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase, TransactionTestCase

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from apps.auditlog.selectors import (
    AuditLogSelector,
)
from apps.auditlog.services import audit_create
from apps.auditlog.signal_handlers import AuditModelRegistry
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

    def setUp(self):
        """Clear existing audit logs before each test."""
        AuditTrail.objects.all().delete()

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
        bulk_audits = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)
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
        result = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)
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
        result = AuditLogSelector.get_audit_logs_with_filters(
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
        result = AuditLogSelector.get_audit_logs_with_filters(
            search_query="Engineering"
        )
        matching_audits = list(result)
        search_time = time.time() - start_time

        # Should complete search in reasonable time
        self.assertLess(search_time, 3.0)  # 3 seconds max

        # Verify search results
        self.assertGreater(len(matching_audits), 0)
        for audit in matching_audits[:10]:  # Check first 10
            self.assertIn("Engineering", str(audit.metadata))

    @pytest.mark.django_db
    def test_signal_handler_performance(self):
        """Test performance of signal handlers during model operations."""
        # Register Entry model for audit
        registry = AuditModelRegistry()
        registry.register_model(
            EntryFactory._meta.model,
            action_types={
                "created": AuditActionType.ENTRY_CREATED,
                "updated": AuditActionType.ENTRY_UPDATED,
                "deleted": AuditActionType.ENTRY_DELETED,
            },
            tracked_fields=["description", "amount"],
        )

        start_time = time.time()

        # Create 50 entries (will trigger signal handlers)
        entries = []
        for i in range(50):
            entry = EntryFactory(description=f"Performance Test Entry {i}")
            entries.append(entry)

        end_time = time.time()
        duration = end_time - start_time

        # Entry creation with signal handlers should be reasonable
        self.assertLess(
            duration, 3.0, f"Signal handler performance too slow: {duration:.2f}s"
        )

        # Verify audit trails were created by signals
        audit_count = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_CREATED
        ).count()
        self.assertEqual(audit_count, 50)

    @pytest.mark.django_db
    def test_business_logger_performance(self):
        """Test performance of business logger operations."""
        user = CustomUserFactory()
        entries = [EntryFactory() for _ in range(20)]

        start_time = time.time()

        # Log 20 entry actions using business logger
        for entry in entries:
            BusinessAuditLogger.log_entry_action(
                user=user, entry=entry, action="submit", request=None
            )

        end_time = time.time()
        duration = end_time - start_time

        # Business logger should be efficient
        self.assertLess(
            duration, 2.0, f"Business logger performance too slow: {duration:.2f}s"
        )

        # Verify audit logs were created
        audit_count = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_SUBMITTED
        ).count()
        self.assertEqual(audit_count, 20)

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
        result = AuditLogSelector.get_audit_logs_with_filters(
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

    def setUp(self):
        """Clear existing audit logs before each test."""
        AuditTrail.objects.all().delete()

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
            action_type="entry_status_changed",
            target_entity=entry,
            metadata={
                "old_status": "submitted",
                "new_status": "approved",
                "reviewer": reviewer.username,
                "review_notes": "Approved with attachments",
            },
        )

        # Verify complete system audit trail
        all_audits = AuditLogSelector.get_audit_logs_with_filters()
        # Filter to only count audits from this test (by checking for specific users)
        test_audits = all_audits.filter(
            models.Q(user=user) | models.Q(user=reviewer) | models.Q(user__isnull=True)
        )
        # Account for automatic audit logs created by factories (6 manual + automatic from factories)
        self.assertGreaterEqual(test_audits.count(), 6)

        # Verify workflow relationships
        user_audits = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)
        # Account for automatic audit logs (4 manual + automatic from factories)
        self.assertGreaterEqual(user_audits.count(), 4)  # User performed at least 4 actions

        entry_audits = AuditLogSelector.get_audit_logs_with_filters(
            target_entity_id=entry.entry_id
        )
        # Account for automatic audit logs (2 manual + automatic from EntryFactory)
        self.assertGreaterEqual(entry_audits.count(), 2)  # Entry had at least 2 actions

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
                        action_type="entry_status_changed",
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
        total_audits = AuditTrail.objects.filter(
            user__in=users
        ).count()
        self.assertEqual(
            total_audits, audit_count
        )  # 3 users * 5 entities * 20 rounds = 300

        # Verify relationships remain intact
        for user in users:
            user_audit_count = AuditLogSelector.get_audit_logs_with_filters(
                user_id=user.user_id
            ).count()
            self.assertEqual(
                user_audit_count, 100
            )  # 5 entities * 20 rounds = 100 per user

        for entry in entries[:5]:
            entity_audit_count = AuditLogSelector.get_audit_logs_with_filters(
                target_entity_id=entry.entry_id
            ).count()
            # Account for automatic audit logs from EntryFactory (60 manual + 1 automatic = 61)
            self.assertGreaterEqual(
                entity_audit_count, 60
            )  # 3 users * 20 rounds = at least 60 per entity

    @pytest.mark.django_db
    def test_audit_log_database_optimization(self):
        """Test that database queries are optimized."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create test data
        BulkAuditTrailFactory.create_batch(50, user=user, target_entity=entry)

        # Test that selector uses proper optimization
        with self.assertNumQueries(1):  # Should be single query with join
            result = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)

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
        search_result = AuditLogSelector.get_audit_logs_with_filters(
            search_query="item_50"
        )
        self.assertEqual(search_result.count(), 1)


@pytest.mark.system
class TestAuditLogScalability(TestCase):
    """Test audit log scalability scenarios."""

    def setUp(self):
        """Clear existing audit logs before each test."""
        AuditTrail.objects.all().delete()

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
            result = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)
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
        result = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)

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
            lambda: AuditLogSelector.get_audit_logs_with_filters(
                user_id=users[0].user_id
            ),
            # Test action_type index
            lambda: AuditLogSelector.get_audit_logs_with_filters(
                action_type="entry_created"
            ),
            # Test entity_type index (pass model name string, not ContentType object)
            lambda: AuditLogSelector.get_audit_logs_with_filters(
                target_entity_type="entry"
            ),
            # Test combined filters (should use multiple indexes)
            lambda: AuditLogSelector.get_audit_logs_with_filters(
                user_id=users[0].user_id,
                action_type="entry_created",
                target_entity_id=entries[0].entry_id,
                target_entity_type="entry",
            ),
        ]

        for query_func in test_queries:
            start_time = time.time()
            result = query_func()
            list(result[:100])  # Force evaluation of first 100 results
            query_time = time.time() - start_time

            # Indexed queries should be fast even with large dataset
            self.assertLess(query_time, 0.5)  # 0.5 seconds max


@pytest.mark.system
class TestAuditLogConcurrency(TransactionTestCase):
    """Test audit log system under concurrent access."""

    def setUp(self):
        """Clear existing audit logs and set up test data."""
        AuditTrail.objects.all().delete()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.num_threads = 5
        self.operations_per_thread = 10

    def test_concurrent_audit_creation(self):
        """Test concurrent audit creation from multiple threads."""
        results = []
        errors = []

        def create_audits(thread_id):
            """Create audits in a thread."""
            thread_results = []
            try:
                for i in range(self.operations_per_thread):
                    entry = EntryFactory(description=f"Thread {thread_id} Entry {i}")

                    audit_create(
                        user=self.user,
                        action_type=AuditActionType.ENTRY_CREATED,
                        target_entity=entry,
                        metadata={"thread_id": thread_id, "operation": i},
                    )
                    thread_results.append(f"thread_{thread_id}_op_{i}")

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

            return thread_results

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [
                executor.submit(create_audits, thread_id)
                for thread_id in range(self.num_threads)
            ]

            for future in as_completed(futures):
                try:
                    thread_results = future.result(timeout=10)
                    results.extend(thread_results)
                except Exception as e:
                    errors.append(f"Future error: {str(e)}")

        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent errors occurred: {errors}")

        expected_operations = self.num_threads * self.operations_per_thread
        self.assertEqual(
            len(results),
            expected_operations,
            f"Expected {expected_operations} operations, got {len(results)}",
        )

        # Verify all audits were created in database
        total_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_CREATED, user=self.user
        ).count()
        self.assertEqual(
            total_audits,
            expected_operations,
            f"Expected {expected_operations} audit records, found {total_audits}",
        )

    def test_concurrent_signal_handlers(self):
        """Test concurrent signal handler execution."""
        # Register model for audit
        registry = AuditModelRegistry()
        registry.register_model(
            EntryFactory._meta.model,
            action_types={
                "created": AuditActionType.ENTRY_CREATED,
                "updated": AuditActionType.ENTRY_UPDATED,
                "deleted": AuditActionType.ENTRY_DELETED,
            },
            tracked_fields=["description", "amount"],
        )

        results = []
        errors = []

        def create_entries(thread_id):
            """Create entries in a thread (triggers signals)."""
            thread_results = []
            try:
                for i in range(self.operations_per_thread):
                    entry = EntryFactory(
                        description=f"Concurrent Thread {thread_id} Entry {i}",
                        amount=100 + thread_id + i,
                    )
                    thread_results.append(entry.entry_id)

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

            return thread_results

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [
                executor.submit(create_entries, thread_id)
                for thread_id in range(self.num_threads)
            ]

            for future in as_completed(futures):
                try:
                    thread_results = future.result(timeout=10)
                    results.extend(thread_results)
                except Exception as e:
                    errors.append(f"Future error: {str(e)}")

        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent signal errors: {errors}")

        expected_entries = self.num_threads * self.operations_per_thread
        self.assertEqual(len(results), expected_entries)

        # Verify signal handlers created audit trails
        audit_count = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_CREATED
        ).count()
        self.assertEqual(
            audit_count,
            expected_entries,
            f"Expected {expected_entries} signal audits, found {audit_count}",
        )

    def test_concurrent_business_logger_operations(self):
        """Test concurrent business logger operations."""
        entries = [
            EntryFactory() for _ in range(self.num_threads * self.operations_per_thread)
        ]

        results = []
        errors = []

        def log_business_actions(thread_id):
            """Log business actions in a thread."""
            thread_results = []
            try:
                start_idx = thread_id * self.operations_per_thread
                end_idx = start_idx + self.operations_per_thread

                for i, entry in enumerate(entries[start_idx:end_idx]):
                    BusinessAuditLogger.log_entry_action(
                        user=self.user,
                        entry=entry,
                        action="submit",
                        request=None,
                        notes=f"Thread {thread_id} operation {i}",
                    )
                    thread_results.append(f"thread_{thread_id}_entry_{entry.entry_id}")

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

            return thread_results

        # Run concurrent business logger operations
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [
                executor.submit(log_business_actions, thread_id)
                for thread_id in range(self.num_threads)
            ]

            for future in as_completed(futures):
                try:
                    thread_results = future.result(timeout=10)
                    results.extend(thread_results)
                except Exception as e:
                    errors.append(f"Future error: {str(e)}")

        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent business logger errors: {errors}")

        expected_operations = self.num_threads * self.operations_per_thread
        self.assertEqual(len(results), expected_operations)

        # Verify business logger created audit trails
        audit_count = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_SUBMITTED
        ).count()
        self.assertEqual(
            audit_count,
            expected_operations,
            f"Expected {expected_operations} business audits, found {audit_count}",
        )


@pytest.mark.system
class TestAuditLogMemoryUsage(TestCase):
    """Test audit log system memory usage patterns."""

    def setUp(self):
        """Clear existing audit logs and set up test data."""
        AuditTrail.objects.all().delete()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_memory_usage_during_bulk_creation(self):
        """Test performance during bulk audit creation."""
        # Create many audits and measure time efficiency
        entries = [EntryFactory() for _ in range(100)]

        start_time = time.time()

        for entry in entries:
            audit_create(
                user=self.user,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=entry,
                metadata={"test": "memory_usage"},
            )

        end_time = time.time()
        duration = end_time - start_time

        # Bulk creation should be efficient (less than 2 seconds for 100 audits)
        self.assertLess(
            duration, 2.0, f"Bulk audit creation took too long: {duration:.3f}s"
        )

        # Verify all audits were created
        audit_count = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_CREATED, user=self.user
        ).count()
        self.assertEqual(audit_count, 100)

    @pytest.mark.django_db
    def test_signal_handler_memory_efficiency(self):
        """Test signal handler performance efficiency."""

        # Register model for audit
        registry = AuditModelRegistry()
        registry.register_model(
            EntryFactory._meta.model,
            action_types={
                "created": AuditActionType.ENTRY_CREATED,
                "updated": AuditActionType.ENTRY_UPDATED,
                "deleted": AuditActionType.ENTRY_DELETED,
            },
            tracked_fields=["description"],
        )

        start_time = time.time()

        # Create entries (triggers signals)
        entries = []
        for i in range(50):
            entry = EntryFactory(description=f"Memory Test {i}")
            entries.append(entry)

        end_time = time.time()
        duration = end_time - start_time

        # Signal handlers should be efficient (less than 10 seconds for 50 entries)
        self.assertLess(
            duration,
            10.0,
            f"Signal handlers took too long: {duration:.3f}s",
        )

        # Verify audits were created
        audit_count = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_CREATED
        ).count()
        self.assertEqual(audit_count, 50)


@pytest.mark.system
class TestAuditLogSystemScalability(TestCase):
    """Test audit log system scalability with large datasets."""

    def setUp(self):
        """Clear existing audit logs and set up test data."""
        AuditTrail.objects.all().delete()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_large_metadata_performance(self):
        """Test performance with large metadata objects."""
        # Create large metadata
        large_metadata = {
            "description": "A" * 1000,  # 1KB string
            "details": {
                f"field_{i}": f"value_{i}" * 10 for i in range(100)
            },  # Nested object
            "tags": [f"tag_{i}" for i in range(50)],  # Array
            "numbers": list(range(100)),  # Number array
        }

        entry = EntryFactory()

        start_time = time.time()

        audit_create(
            user=self.user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata=large_metadata,
        )

        end_time = time.time()
        duration = end_time - start_time

        # Should handle large metadata reasonably
        self.assertLess(duration, 0.5, f"Large metadata audit took {duration:.3f}s")

        # Verify audit was created and metadata preserved
        audit = AuditTrail.objects.filter(
            user=self.user,
            action_type=AuditActionType.ENTRY_CREATED
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["description"], "A" * 1000)
        self.assertEqual(len(audit.metadata["details"]), 100)

    @pytest.mark.django_db
    def test_bulk_operation_scalability(self):
        """Test bulk operation logging scalability."""
        # Create large number of objects
        entries = [EntryFactory() for _ in range(500)]

        start_time = time.time()

        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_approve",
            affected_objects=entries,
            request=None,
        )

        end_time = time.time()
        duration = end_time - start_time

        # Bulk operation should be efficient even with many objects
        self.assertLess(duration, 10.0, f"Bulk operation logging took {duration:.3f}s")

        # Verify audit was created
        audit = AuditTrail.objects.filter(
            user=self.user
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata["total_affected"], 500)

    @pytest.mark.django_db
    def test_audit_cleanup_performance(self):
        """Test performance of audit cleanup operations."""
        # Create many old audit records
        entries = [EntryFactory() for _ in range(200)]
        for entry in entries:
            audit_create(
                user=self.user,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=entry,
            )

        initial_count = AuditTrail.objects.filter(user=self.user).count()
        self.assertEqual(initial_count, 200)

        start_time = time.time()

        # Simulate cleanup operation (delete half)
        audits_to_delete = AuditTrail.objects.filter(user=self.user)[:100]
        audit_ids = list(audits_to_delete.values_list("audit_id", flat=True))
        AuditTrail.objects.filter(audit_id__in=audit_ids).delete()

        end_time = time.time()
        duration = end_time - start_time

        # Cleanup should be efficient
        self.assertLess(duration, 1.0, f"Audit cleanup took {duration:.3f}s")

        # Verify cleanup worked
        remaining_count = AuditTrail.objects.filter(user=self.user).count()
        self.assertEqual(remaining_count, 100)


@pytest.mark.system
class TestAuditLogPerformanceWorkflows(TestCase):
    """Test audit log performance in realistic scenarios."""

    def setUp(self):
        """Clear existing audit logs before each test."""
        AuditTrail.objects.all().delete()

    @pytest.mark.django_db
    def test_high_volume_audit_logging(self):
        """Test performance with high volume audit logging."""
        user = CustomUserFactory()

        # Create high volume of audit entries
        start_time = datetime.now()

        for i in range(100):
            audit_create(
                user=user,
                action_type=AuditActionType.ENTRY_CREATED,
                target_entity=EntryFactory(),
                metadata={"sequence": i},
            )

        end_time = datetime.now()
        creation_time = (end_time - start_time).total_seconds()

        # Should create 100 audits reasonably quickly (adjust threshold as needed)
        self.assertLess(creation_time, 40.0)  # 40 seconds max

        # Verify all were created
        user_audits = AuditLogSelector.get_audit_logs_with_filters(user_id=user.user_id)
        self.assertEqual(user_audits.count(), 100)

    @pytest.mark.django_db
    def test_complex_filtering_performance(self):
        """Test performance of complex filtering queries."""
        users = CustomUserFactory.create_batch(10)

        # Create diverse audit data
        for user in users:
            BulkAuditTrailFactory.create_batch_for_entity(
                entity=EntryFactory(submitter=user), count=10, user=user
            )

        # Test complex filtering performance
        start_time = datetime.now()

        result = AuditLogSelector.get_audit_logs_with_filters(
            user_id=users[0].user_id,
            action_type=AuditActionType.ENTRY_CREATED,
            start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            search_query="entry",
        )

        # Force evaluation
        list(result[:10])

        end_time = datetime.now()
        query_time = (end_time - start_time).total_seconds()

        # Complex query should complete reasonably quickly
        self.assertLess(query_time, 2.0)  # 2 seconds max
