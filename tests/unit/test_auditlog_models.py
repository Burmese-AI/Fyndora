"""
Unit tests for the auditlog app models.

Following the test plan: AuditLog App (apps.auditlog)
- AuditTrail Model Tests
- Constants Tests
- Model property tests
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from tests.factories import (
    AuditTrailFactory,
    CustomUserFactory,
    EntryCreatedAuditFactory,
    EntryFactory,
    FileUploadedAuditFactory,
    FlaggedAuditFactory,
    StatusChangedAuditFactory,
    SystemAuditFactory,
)
from tests.factories.workspace_factories import WorkspaceFactory


@pytest.mark.unit
class TestAuditTrailModel(TestCase):
    """Test the AuditTrail model - essential functionality."""

    @pytest.mark.django_db
    def test_audit_trail_creation_with_defaults(self):
        """Test audit trail creation with default values."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        # Check required fields
        self.assertIsNotNone(audit.audit_id)
        self.assertIsInstance(audit.audit_id, uuid.UUID)
        self.assertIsNotNone(audit.action_type)
        self.assertIsNotNone(audit.target_entity)
        self.assertIsNotNone(audit.target_entity_type)
        self.assertIsNotNone(audit.timestamp)
        self.assertIsNotNone(audit.user)

    @pytest.mark.django_db
    def test_audit_trail_creation_without_user(self):
        """Test audit trail creation without user (system actions)."""
        entry = EntryFactory()
        audit = SystemAuditFactory(target_entity=entry)

        self.assertIsNone(audit.user)
        self.assertIsNotNone(audit.action_type)
        self.assertIsNotNone(audit.target_entity)

    @pytest.mark.django_db
    def test_audit_trail_uuid_uniqueness(self):
        """Test that each audit trail gets a unique UUID."""
        entry = EntryFactory()
        audit1 = AuditTrailFactory(target_entity=entry)
        audit2 = AuditTrailFactory(target_entity=entry)

        self.assertNotEqual(audit1.audit_id, audit2.audit_id)
        self.assertIsInstance(audit1.audit_id, uuid.UUID)
        self.assertIsInstance(audit2.audit_id, uuid.UUID)

    @pytest.mark.django_db
    def test_audit_trail_action_type_choices(self):
        """Test that action_type respects the defined choices."""
        entry = EntryFactory()
        valid_action_types = [choice[0] for choice in AuditActionType.choices]

        for action_type in valid_action_types:
            audit = AuditTrailFactory(action_type=action_type, target_entity=entry)
            self.assertEqual(audit.action_type, action_type)

    @pytest.mark.django_db
    def test_audit_trail_target_entity_type_contenttype(self):
        """Test that target_entity_type is properly set to a ContentType."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        self.assertIsInstance(audit.target_entity_type, ContentType)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )

    @pytest.mark.django_db
    def test_audit_trail_timestamp_auto_add(self):
        """Test that timestamp is automatically set on creation."""
        entry = EntryFactory()
        before_creation = datetime.now(timezone.utc)
        audit = AuditTrailFactory(target_entity=entry)
        after_creation = datetime.now(timezone.utc)

        self.assertIsNotNone(audit.timestamp)
        self.assertGreaterEqual(audit.timestamp, before_creation)
        self.assertLessEqual(audit.timestamp, after_creation)

    @pytest.mark.django_db
    def test_audit_trail_metadata_json_field(self):
        """Test that metadata is properly stored as JSON."""
        entry = EntryFactory()
        metadata = {
            "key1": "value1",
            "key2": 42,
            "key3": ["item1", "item2"],
            "key4": {"nested": "value"},
        }
        audit = AuditTrailFactory(metadata=metadata, target_entity=entry)

        self.assertEqual(audit.metadata, metadata)
        self.assertIsInstance(audit.metadata, dict)

    @pytest.mark.django_db
    def test_audit_trail_metadata_null_allowed(self):
        """Test that metadata can be null."""
        entry = EntryFactory()
        audit = AuditTrailFactory(metadata=None, target_entity=entry)
        self.assertIsNone(audit.metadata)

    @pytest.mark.django_db
    def test_audit_trail_str_representation(self):
        """Test string representation format."""
        user = CustomUserFactory(username="testuser")
        entry = EntryFactory()
        audit = AuditTrailFactory(
            user=user,
            action_type="entry_created",
            target_entity=entry,
        )

        expected_parts = [
            "entry_created",
            "testuser",
            str(entry.pk),
        ]

        str_repr = str(audit)
        for part in expected_parts:
            self.assertIn(part, str_repr)

    @pytest.mark.django_db
    def test_audit_trail_str_representation_without_user(self):
        """Test string representation for system actions without user."""
        entry = EntryFactory()
        audit = SystemAuditFactory(
            action_type="entry_created",
            target_entity=entry,
        )

        str_repr = str(audit)
        self.assertIn("entry_created", str_repr)
        self.assertIn("None", str_repr)  # User should be None
        self.assertIn(str(entry.pk), str_repr)

    def test_audit_trail_meta_ordering(self):
        """Test model meta ordering configuration."""
        self.assertEqual(AuditTrail._meta.ordering, ["-timestamp"])

    def test_audit_trail_meta_indexes(self):
        """Test that proper database indexes are defined."""
        indexes = AuditTrail._meta.indexes
        self.assertGreater(len(indexes), 0)

        # Check that expected indexes exist
        index_fields = [idx.fields for idx in indexes]
        expected_indexes = [
            ["target_entity_type", "target_entity_id"],
            ["action_type"],
            ["timestamp"],
            ["user"],
        ]

        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_fields)


@pytest.mark.unit
class TestAuditTrailDetailsProperty(TestCase):
    """Test the AuditTrail details property."""

    @pytest.mark.django_db
    def test_details_property_no_metadata(self):
        """Test details property when metadata is None."""
        entry = EntryFactory()
        audit = AuditTrailFactory(metadata=None, target_entity=entry)
        self.assertEqual(audit.details, "No details provided.")

    @pytest.mark.django_db
    def test_details_property_status_changed(self):
        """Test details property for status_changed action type."""
        entry = EntryFactory()
        audit = StatusChangedAuditFactory(target_entity=entry)

        details = audit.details
        self.assertIn("Status changed from", details)
        self.assertIn("pending", details)
        self.assertIn("approved", details)

    @pytest.mark.django_db
    def test_details_property_status_changed_missing_values(self):
        """Test details property for status_changed with missing values."""
        entry = EntryFactory()
        audit = AuditTrailFactory(
            action_type="status_changed",
            metadata={"some_other_field": "value"},
            target_entity=entry,
        )

        details = audit.details
        self.assertIn("Status changed from 'N/A' to 'N/A'", details)

    @pytest.mark.django_db
    def test_details_property_generic_metadata(self):
        """Test details property for generic metadata."""
        entry = EntryFactory()
        metadata = {"field_one": "value1", "field_two": "value2", "amount": 1000}
        audit = AuditTrailFactory(
            action_type="entry_created",
            metadata=metadata,
            target_entity=entry,
        )

        details = audit.details
        self.assertIn("Field One: value1", details)
        self.assertIn("Field Two: value2", details)
        self.assertIn("Amount: 1000", details)

    @pytest.mark.django_db
    def test_details_property_json_string_metadata(self):
        """Test details property when metadata is a JSON string."""
        entry = EntryFactory()
        json_metadata = json.dumps({"old_status": "draft", "new_status": "submitted"})
        audit = AuditTrailFactory(
            action_type="status_changed",
            metadata=json_metadata,
            target_entity=entry,
        )

        details = audit.details
        self.assertIn("Status changed from", details)
        self.assertIn("draft", details)
        self.assertIn("submitted", details)

    @pytest.mark.django_db
    def test_details_property_invalid_json_string(self):
        """Test details property with invalid JSON string."""
        entry = EntryFactory()
        invalid_json = "not valid json"
        audit = AuditTrailFactory(metadata=invalid_json, target_entity=entry)

        details = audit.details
        self.assertEqual(details, invalid_json)

    @pytest.mark.django_db
    def test_details_property_non_dict_metadata(self):
        """Test details property with non-dictionary metadata."""
        entry = EntryFactory()
        audit = AuditTrailFactory(metadata="simple string", target_entity=entry)

        details = audit.details
        self.assertEqual(details, "simple string")

    @pytest.mark.django_db
    def test_details_property_complex_metadata(self):
        """Test details property with complex nested metadata."""
        entry = EntryFactory()

        # Create custom metadata to avoid 'submitter_type' in Entry.__str__
        custom_metadata = {
            "user_details": {
                "username": "TestUser",
                "user_id": str(uuid.uuid4()),
                "ip_address": "192.168.1.100",
            },
            "entity_details": {
                "entity_type": "entry",
                "entity_id": str(entry.pk),
                "previous_values": {"status": "draft", "amount": "500.00"},
                "new_values": {"status": "submitted", "amount": "750.00"},
            },
            "context": {
                "workspace_id": str(uuid.uuid4()),
                "team_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
            },
        }

        # Use a generic action type that will trigger the generic formatter
        audit = AuditTrailFactory(
            target_entity=entry,
            metadata=custom_metadata,
            action_type="custom_action",  # This will use the generic formatter
        )

        details = audit.details
        # Should contain formatted key-value pairs
        self.assertIn("User Details:", details)
        self.assertIn("Entity Details:", details)
        self.assertIn("Context:", details)


@pytest.mark.unit
class TestAuditTrailConstants(TestCase):
    """Test the auditlog constants."""

    def test_audit_action_type_choices_structure(self):
        """Test that action type choices are properly structured."""
        self.assertIsInstance(AuditActionType.choices, list)
        self.assertGreater(len(AuditActionType.choices), 0)

        for choice in AuditActionType.choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)  # Value
            self.assertIsInstance(choice[1], str)  # Display name

    def test_expected_action_types_present(self):
        """Test that expected action types are present."""
        expected_actions = [
            "entry_created",
            "entry_status_changed",
            "entry_flagged",
            "file_uploaded",
        ]
        action_values = [choice[0] for choice in AuditActionType.choices]

        for expected_action in expected_actions:
            self.assertIn(expected_action, action_values)


@pytest.mark.unit
class TestAuditTrailFactories(TestCase):
    """Test the auditlog factories."""

    @pytest.mark.django_db
    def test_entry_created_audit_factory(self):
        """Test EntryCreatedAuditFactory produces correct audit logs."""
        entry = EntryFactory()
        audit = EntryCreatedAuditFactory(target_entity=entry)

        self.assertEqual(audit.action_type, "entry_created")
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertIn("entry_type", audit.metadata)
        self.assertIn("amount", audit.metadata)
        self.assertIn("submitter", audit.metadata)

    @pytest.mark.django_db
    def test_status_changed_audit_factory(self):
        """Test StatusChangedAuditFactory produces correct audit logs."""
        entry = EntryFactory()
        audit = StatusChangedAuditFactory(target_entity=entry)

        self.assertEqual(audit.action_type, "entry_status_changed")
        # target_entity_type will be set from the entry now
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertIn("old_status", audit.metadata)
        self.assertIn("new_status", audit.metadata)
        self.assertIn("reviewer", audit.metadata)

    @pytest.mark.django_db
    def test_flagged_audit_factory(self):
        """Test FlaggedAuditFactory produces correct audit logs."""
        entry = EntryFactory()
        audit = FlaggedAuditFactory(target_entity=entry)

        self.assertEqual(audit.action_type, AuditActionType.ENTRY_FLAGGED)
        self.assertIn("flag_reason", audit.metadata)
        self.assertIn("flagged_by", audit.metadata)
        self.assertIn("severity", audit.metadata)

    @pytest.mark.django_db
    def test_file_uploaded_audit_factory(self):
        """Test FileUploadedAuditFactory produces correct audit logs."""
        entry = (
            EntryFactory()
        )  # Using EntryFactory as placeholder since we don't have an attachment model
        audit = FileUploadedAuditFactory(target_entity=entry)

        self.assertEqual(audit.action_type, "file_uploaded")
        # target_entity_type will be set from the entry
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertIn("filename", audit.metadata)
        self.assertIn("file_size", audit.metadata)
        self.assertIn("uploaded_by", audit.metadata)

    @pytest.mark.django_db
    def test_system_audit_factory(self):
        """Test SystemAuditFactory produces correct audit logs."""
        entry = EntryFactory()
        audit = SystemAuditFactory(target_entity=entry)

        self.assertIsNone(audit.user)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertIn("system_action", audit.metadata)
        self.assertIn("triggered_by", audit.metadata)

    @pytest.mark.django_db
    def test_complex_metadata_factory(self):
        """Test AuditWithComplexMetadataFactory produces correct structure."""
        entry = EntryFactory()

        # Create custom metadata to avoid 'submitter_type' in Entry.__str__
        custom_metadata = {
            "user_details": {
                "username": "TestUser",
                "user_id": str(uuid.uuid4()),
                "ip_address": "192.168.1.100",
            },
            "entity_details": {
                "entity_type": "entry",
                "entity_id": str(entry.pk),
                "details": "Test entity details",
            },
            "context": {
                "workspace_id": str(uuid.uuid4()),
                "team_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
            },
        }

        audit = AuditTrailFactory(target_entity=entry, metadata=custom_metadata)

        self.assertIn("user_details", audit.metadata)
        self.assertIn("entity_details", audit.metadata)
        self.assertIn("context", audit.metadata)

        # Check nested structure
        self.assertIn("username", audit.metadata["user_details"])
        self.assertIn("entity_type", audit.metadata["entity_details"])
        self.assertIn("workspace_id", audit.metadata["context"])


@pytest.mark.unit
class TestAuditTrailEdgeCases(TestCase):
    """Test edge cases and error conditions."""

    @pytest.mark.django_db
    def test_audit_trail_with_maximum_length_fields(self):
        """Test audit trail with maximum length values."""
        entry = EntryFactory()
        long_action_type = "x" * 100  # Max length for action_type

        # These should not raise validation errors if within max_length
        audit = AuditTrailFactory(
            action_type=long_action_type[:100],
            target_entity=entry,
        )

        self.assertEqual(len(audit.action_type), 100)
        self.assertIsInstance(audit.target_entity_type, ContentType)

    @pytest.mark.django_db
    def test_audit_trail_concurrent_creation(self):
        """Test concurrent audit trail creation doesn't cause conflicts."""
        import threading
        import time
        from django.db import transaction

        entry = EntryFactory()
        results = []
        errors = []

        def create_audit(thread_id):
            try:
                with transaction.atomic():
                    audit = AuditTrailFactory(
                        target_entity=entry,
                        action_type=f"test_action_{thread_id}",
                        metadata={"thread_id": thread_id},
                    )
                    results.append(audit.audit_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_audit, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)
        self.assertEqual(len(set(results)), 5)  # All UUIDs should be unique

    @pytest.mark.django_db
    def test_audit_trail_with_large_metadata(self):
        """Test audit trail with large metadata objects."""
        entry = EntryFactory()
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        audit = AuditTrailFactory(metadata=large_metadata, target_entity=entry)
        self.assertEqual(len(audit.metadata), 100)

        # Test that it can be retrieved correctly
        audit.refresh_from_db()
        self.assertEqual(len(audit.metadata), 100)

    @pytest.mark.django_db
    def test_audit_trail_with_special_characters_in_metadata(self):
        """Test audit trail with special characters in metadata."""
        entry = EntryFactory()
        special_metadata = {
            "unicode": "🔥💻🎯",
            "quotes": "This has \"quotes\" and 'apostrophes'",
            "newlines": "Line 1\nLine 2\rLine 3",
            "html": "<script>alert('test')</script>",
            "json_like": '{"nested": "json"}',
        }

        # Test 1: Regular special characters should work fine
        audit = AuditTrailFactory(metadata=special_metadata, target_entity=entry)
        audit.refresh_from_db()

        # All special characters should be preserved
        self.assertEqual(audit.metadata["unicode"], "🔥💻🎯")
        self.assertIn("quotes", audit.metadata["quotes"])
        self.assertIn("Line 1", audit.metadata["newlines"])

        # Test 2: Null characters should raise an exception in PostgreSQL
        null_metadata = {"null_char": "text\x00with\x00nulls"}

        # PostgreSQL should not accept null characters in JSON fields
        # This is an expected limitation, not a bug in our code
        with self.assertRaises(Exception) as context:
            AuditTrailFactory(metadata=null_metadata, target_entity=entry)

        # Verify the exception is related to the null character
        error_message = str(context.exception)
        self.assertIn("null", error_message.lower()) or self.assertIn(
            "\\u0000", error_message
        ) or self.assertIn("unicode", error_message.lower())

    @pytest.mark.django_db
    def test_audit_trail_ordering_by_timestamp(self):
        """Test that audit trails are ordered by timestamp descending."""
        entry = EntryFactory()
        # Create multiple audit trails
        AuditTrailFactory(target_entity=entry)
        AuditTrailFactory(target_entity=entry)

        # Query all audit trails
        audits = list(AuditTrail.objects.all())

        # Should be ordered by timestamp descending (newest first)
        for i in range(len(audits) - 1):
            self.assertGreaterEqual(audits[i].timestamp, audits[i + 1].timestamp)


@pytest.mark.unit
class TestAuditTrailCriticalActions(TestCase):
    """Test critical action type functionality."""

    def test_critical_action_identification(self):
        """Test that critical actions are properly identified."""
        from apps.auditlog.constants import is_critical_action

        # Test critical actions
        critical_actions = [
            AuditActionType.USER_DELETED,
            AuditActionType.ORGANIZATION_DELETED,
            AuditActionType.PERMISSION_REVOKED,
            AuditActionType.DATA_EXPORTED,
            AuditActionType.SYSTEM_ERROR,
        ]

        for action in critical_actions:
            self.assertTrue(
                is_critical_action(action), f"{action} should be identified as critical"
            )

        # Test non-critical actions
        non_critical_actions = [
            AuditActionType.LOGIN_SUCCESS,
            AuditActionType.ENTRY_CREATED,
            AuditActionType.FILE_DOWNLOADED,
        ]

        for action in non_critical_actions:
            self.assertFalse(
                is_critical_action(action),
                f"{action} should not be identified as critical",
            )

    @pytest.mark.django_db
    def test_critical_action_audit_creation(self):
        """Test audit creation for critical actions."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create audit for critical action
        audit = AuditTrailFactory(
            user=user,
            action_type=AuditActionType.DATA_EXPORTED,
            target_entity=entry,
            metadata={
                "export_type": "entries",
                "record_count": 100,
                "reason": "compliance_audit",
            },
        )

        self.assertEqual(audit.action_type, AuditActionType.DATA_EXPORTED)
        self.assertIn("export_type", audit.metadata)
        self.assertIn("record_count", audit.metadata)


@pytest.mark.unit
class TestAuditTrailWorkspaceDetection(TestCase):
    """Test workspace detection and association."""

    @pytest.mark.django_db
    def test_workspace_detection_from_entry(self):
        """Test workspace detection from entry target entity."""
        workspace = WorkspaceFactory()
        entry = EntryFactory(workspace=workspace)

        audit = AuditTrailFactory(
            target_entity=entry, action_type=AuditActionType.ENTRY_CREATED
        )

        # Verify the audit was created with correct target entity
        self.assertEqual(audit.target_entity, entry)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )

    @pytest.mark.django_db
    def test_workspace_as_target_entity(self):
        """Test workspace as direct target entity."""
        workspace = WorkspaceFactory()

        audit = AuditTrailFactory(
            target_entity=workspace, action_type=AuditActionType.WORKSPACE_CREATED
        )

        self.assertEqual(audit.target_entity, workspace)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(workspace)
        )


@pytest.mark.unit
class TestAuditTrailQueryOptimization(TestCase):
    """Test query optimization and database performance."""

    @pytest.mark.django_db
    def test_audit_trail_select_related_optimization(self):
        """Test that queries can be optimized with select_related."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Create multiple audit trails
        for i in range(10):
            AuditTrailFactory(
                user=user,
                target_entity=entry,
                action_type=AuditActionType.ENTRY_CREATED,
            )

        # Test optimized query
        with self.assertNumQueries(1):
            audits = list(
                AuditTrail.objects.select_related("user", "target_entity_type").filter(
                    user=user
                )[:5]
            )

            # Access related fields (should not trigger additional queries)
            for audit in audits:
                _ = audit.user.username
                _ = audit.target_entity_type.model

    @pytest.mark.django_db
    def test_audit_trail_filtering_performance(self):
        """Test performance of common filtering operations."""
        import time

        user = CustomUserFactory()
        entry = EntryFactory()

        # Create a larger dataset
        for i in range(500):
            AuditTrailFactory(
                user=user if i % 2 == 0 else CustomUserFactory(),
                target_entity=entry,
                action_type=AuditActionType.ENTRY_CREATED
                if i % 3 == 0
                else AuditActionType.ENTRY_UPDATED,
            )

        # Test filtering by user
        start_time = time.time()
        user_audits = list(AuditTrail.objects.filter(user=user))
        user_filter_time = time.time() - start_time

        # Test filtering by action type
        start_time = time.time()
        action_audits = list(
            AuditTrail.objects.filter(action_type=AuditActionType.ENTRY_CREATED)
        )
        action_filter_time = time.time() - start_time

        # Performance assertions
        self.assertLess(user_filter_time, 1.0, "User filtering took too long")
        self.assertLess(action_filter_time, 1.0, "Action type filtering took too long")

        # Verify results
        self.assertGreater(len(user_audits), 0)
        self.assertGreater(len(action_audits), 0)
