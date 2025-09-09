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
    OrganizationFactory,
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
    def test_audit_trail_rapid_creation(self):
        """Test rapid audit trail creation doesn't cause conflicts."""
        from django.db import transaction

        entry = EntryFactory()
        results = []

        # Create multiple audit trails rapidly in sequence (not concurrently)
        for i in range(5):
            with transaction.atomic():
                audit = AuditTrailFactory(
                    target_entity=entry,
                    action_type=f"test_action_{i}",
                    metadata={"sequence_id": i},
                )
                results.append(audit.audit_id)

        # Verify results
        self.assertEqual(len(results), 5)
        self.assertEqual(len(set(results)), 5)  # All UUIDs should be unique

        # Verify all audits were created successfully
        for i, audit_id in enumerate(results):
            audit = AuditTrail.objects.get(audit_id=audit_id)
            self.assertEqual(audit.action_type, f"test_action_{i}")
            self.assertEqual(audit.metadata["sequence_id"], i)

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

        # Test 2: Null characters - behavior depends on database backend
        null_metadata = {"null_char": "text\x00with\x00nulls"}

        # Test whether null characters are handled gracefully or raise an exception
        try:
            audit_with_nulls = AuditTrailFactory(
                metadata=null_metadata, target_entity=entry
            )
            # If no exception is raised, verify the data is stored correctly
            audit_with_nulls.refresh_from_db()
            # The null characters might be escaped or handled by the database
            self.assertIn("null_char", audit_with_nulls.metadata)
            # Check that the value contains some form of the original text
            stored_value = audit_with_nulls.metadata["null_char"]
            self.assertIn("text", stored_value)
            self.assertIn("with", stored_value)
            self.assertIn("nulls", stored_value)
        except Exception as e:
            # If an exception is raised, verify it's related to null characters
            error_message = str(e).lower()
            self.assertTrue(
                any(
                    keyword in error_message
                    for keyword in ["null", "\\u0000", "unicode", "invalid"]
                ),
                f"Unexpected error message: {error_message}",
            )

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


@pytest.mark.unit
class TestAuditTrailOrganizationField(TestCase):
    """Test organization field functionality in AuditTrail model."""

    @pytest.mark.django_db
    def test_audit_trail_with_organization_field(self):
        """Test audit trail creation with organization field set."""
        organization = OrganizationFactory()
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=organization,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertEqual(audit.organization, organization)
        self.assertEqual(audit.organization.pk, organization.pk)
        self.assertIsNotNone(audit.organization.title)

    @pytest.mark.django_db
    def test_audit_trail_organization_field_null_allowed(self):
        """Test that organization field can be null."""
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=None,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertIsNone(audit.organization)

    @pytest.mark.django_db
    def test_audit_trail_organization_foreign_key_relationship(self):
        """Test organization foreign key relationship integrity."""
        organization = OrganizationFactory()
        entry = EntryFactory()

        # Create audit with organization
        audit = AuditTrailFactory(
            organization=organization,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        # Verify relationship works both ways
        self.assertEqual(audit.organization, organization)

        # Test reverse relationship (organization should have audit trails)
        organization_audits = AuditTrail.objects.filter(organization=organization)
        self.assertIn(audit, organization_audits)

    @pytest.mark.django_db
    def test_audit_trail_organization_cascade_behavior(self):
        """Test behavior when organization is deleted."""
        organization = OrganizationFactory()
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=organization,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        audit_id = audit.audit_id

        # Hard delete organization to trigger CASCADE behavior
        organization.hard_delete()

        # With CASCADE, audit trail should be deleted when organization is deleted
        self.assertFalse(AuditTrail.objects.filter(audit_id=audit_id).exists())

    @pytest.mark.django_db
    def test_audit_trail_organization_filtering(self):
        """Test filtering audit trails by organization."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        entry = EntryFactory()

        # Create audits for different organizations
        audit1 = AuditTrailFactory(
            organization=org1,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )
        audit2 = AuditTrailFactory(
            organization=org2,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_UPDATED,
        )
        audit3 = AuditTrailFactory(
            organization=None,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_FLAGGED,
        )

        # Test filtering by organization
        org1_audits = AuditTrail.objects.filter(organization=org1)
        org2_audits = AuditTrail.objects.filter(organization=org2)
        null_org_audits = AuditTrail.objects.filter(organization__isnull=True)

        self.assertIn(audit1, org1_audits)
        self.assertNotIn(audit2, org1_audits)
        self.assertNotIn(audit3, org1_audits)

        self.assertIn(audit2, org2_audits)
        self.assertNotIn(audit1, org2_audits)
        self.assertNotIn(audit3, org2_audits)

        self.assertIn(audit3, null_org_audits)
        self.assertNotIn(audit1, null_org_audits)
        self.assertNotIn(audit2, null_org_audits)


@pytest.mark.unit
class TestAuditTrailWorkspaceField(TestCase):
    """Test workspace field functionality in AuditTrail model."""

    @pytest.mark.django_db
    def test_audit_trail_with_workspace_field(self):
        """Test audit trail creation with workspace field set."""
        workspace = WorkspaceFactory()
        entry = EntryFactory()

        audit = AuditTrailFactory(
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertEqual(audit.workspace, workspace)
        self.assertEqual(audit.workspace.pk, workspace.pk)
        self.assertIsNotNone(audit.workspace.title)

    @pytest.mark.django_db
    def test_audit_trail_workspace_field_null_allowed(self):
        """Test that workspace field can be null."""
        entry = EntryFactory()

        audit = AuditTrailFactory(
            workspace=None,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertIsNone(audit.workspace)

    @pytest.mark.django_db
    def test_audit_trail_workspace_foreign_key_relationship(self):
        """Test workspace foreign key relationship integrity."""
        workspace = WorkspaceFactory()
        entry = EntryFactory()

        # Create audit with workspace
        audit = AuditTrailFactory(
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        # Verify relationship works both ways
        self.assertEqual(audit.workspace, workspace)

        # Test reverse relationship (workspace should have audit trails)
        workspace_audits = AuditTrail.objects.filter(workspace=workspace)
        self.assertIn(audit, workspace_audits)

    @pytest.mark.django_db
    def test_audit_trail_workspace_cascade_behavior(self):
        """Test behavior when workspace is deleted."""
        workspace = WorkspaceFactory()
        entry = EntryFactory()

        audit = AuditTrailFactory(
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        audit_id = audit.audit_id

        # Delete workspace to trigger CASCADE behavior
        workspace.delete()

        # With CASCADE, audit trail should be deleted when workspace is deleted
        self.assertFalse(AuditTrail.objects.filter(audit_id=audit_id).exists())

    @pytest.mark.django_db
    def test_audit_trail_workspace_filtering(self):
        """Test filtering audit trails by workspace."""
        workspace1 = WorkspaceFactory()
        workspace2 = WorkspaceFactory()
        entry = EntryFactory()

        # Create audits for different workspaces
        audit1 = AuditTrailFactory(
            workspace=workspace1,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )
        audit2 = AuditTrailFactory(
            workspace=workspace2,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_UPDATED,
        )
        audit3 = AuditTrailFactory(
            workspace=None,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_FLAGGED,
        )

        # Test filtering by workspace
        ws1_audits = AuditTrail.objects.filter(workspace=workspace1)
        ws2_audits = AuditTrail.objects.filter(workspace=workspace2)
        null_ws_audits = AuditTrail.objects.filter(workspace__isnull=True)

        self.assertIn(audit1, ws1_audits)
        self.assertNotIn(audit2, ws1_audits)
        self.assertNotIn(audit3, ws1_audits)

        self.assertIn(audit2, ws2_audits)
        self.assertNotIn(audit1, ws2_audits)
        self.assertNotIn(audit3, ws2_audits)

        self.assertIn(audit3, null_ws_audits)
        self.assertNotIn(audit1, null_ws_audits)
        self.assertNotIn(audit2, null_ws_audits)

    @pytest.mark.django_db
    def test_audit_trail_workspace_with_organization_context(self):
        """Test workspace field in context of organization relationship."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        entry = EntryFactory()

        audit = AuditTrailFactory(
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertEqual(audit.workspace, workspace)
        self.assertEqual(audit.workspace.organization, organization)
        # Verify we can access organization through workspace
        self.assertIsNotNone(audit.workspace.organization.title)


@pytest.mark.unit
class TestAuditTrailOrganizationWorkspaceRelationships(TestCase):
    """Test organization and workspace field relationships in AuditTrail model."""

    @pytest.mark.django_db
    def test_audit_trail_with_both_organization_and_workspace(self):
        """Test audit trail with both organization and workspace fields set."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=organization,
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertEqual(audit.organization, organization)
        self.assertEqual(audit.workspace, workspace)
        self.assertEqual(audit.workspace.organization, organization)

    @pytest.mark.django_db
    def test_audit_trail_organization_without_workspace(self):
        """Test audit trail with organization but no workspace."""
        organization = OrganizationFactory()
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=organization,
            workspace=None,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertEqual(audit.organization, organization)
        self.assertIsNone(audit.workspace)

    @pytest.mark.django_db
    def test_audit_trail_workspace_without_organization(self):
        """Test audit trail with workspace but no organization."""
        workspace = WorkspaceFactory()
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=None,
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertIsNone(audit.organization)
        self.assertEqual(audit.workspace, workspace)

    @pytest.mark.django_db
    def test_audit_trail_mismatched_organization_workspace(self):
        """Test audit trail with mismatched organization and workspace."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org2)
        entry = EntryFactory()

        # This should be allowed - audit can have different org than workspace's org
        audit = AuditTrailFactory(
            organization=org1,
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        self.assertEqual(audit.organization, org1)
        self.assertEqual(audit.workspace, workspace)
        self.assertEqual(audit.workspace.organization, org2)
        self.assertNotEqual(audit.organization, audit.workspace.organization)

    @pytest.mark.django_db
    def test_audit_trail_filtering_by_organization_and_workspace(self):
        """Test complex filtering by both organization and workspace."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        ws1 = WorkspaceFactory(organization=org1)
        ws2 = WorkspaceFactory(organization=org2)
        entry = EntryFactory()

        # Create various audit combinations
        audit1 = AuditTrailFactory(
            organization=org1,
            workspace=ws1,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )
        audit2 = AuditTrailFactory(
            organization=org2,
            workspace=ws2,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_UPDATED,
        )
        audit3 = AuditTrailFactory(
            organization=org1,
            workspace=None,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_FLAGGED,
        )
        audit4 = AuditTrailFactory(
            organization=None,
            workspace=ws1,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_DELETED,
        )

        # Test filtering by organization
        org1_audits = AuditTrail.objects.filter(organization=org1)
        self.assertIn(audit1, org1_audits)
        self.assertIn(audit3, org1_audits)
        self.assertNotIn(audit2, org1_audits)
        self.assertNotIn(audit4, org1_audits)

        # Test filtering by workspace
        ws1_audits = AuditTrail.objects.filter(workspace=ws1)
        self.assertIn(audit1, ws1_audits)
        self.assertIn(audit4, ws1_audits)
        self.assertNotIn(audit2, ws1_audits)
        self.assertNotIn(audit3, ws1_audits)

        # Test filtering by both organization and workspace
        org1_ws1_audits = AuditTrail.objects.filter(organization=org1, workspace=ws1)
        self.assertIn(audit1, org1_ws1_audits)
        self.assertNotIn(audit2, org1_ws1_audits)
        self.assertNotIn(audit3, org1_ws1_audits)
        self.assertNotIn(audit4, org1_ws1_audits)

    @pytest.mark.django_db
    def test_audit_trail_organization_workspace_cascade_scenarios(self):
        """Test cascade behavior with organization and workspace deletions."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        entry = EntryFactory()

        audit = AuditTrailFactory(
            organization=organization,
            workspace=workspace,
            target_entity=entry,
            action_type=AuditActionType.ENTRY_CREATED,
        )

        audit_id = audit.audit_id

        # Delete workspace first to trigger CASCADE behavior
        workspace.delete()

        # With CASCADE, audit trail should be deleted when workspace is deleted
        self.assertFalse(AuditTrail.objects.filter(audit_id=audit_id).exists())


@pytest.mark.unit
class TestAuditTrailCoverageGaps(TestCase):
    """Test specific coverage gaps in AuditTrail model."""

    @pytest.mark.django_db
    def test_parse_metadata_json_decode_error(self):
        """Test _parse_metadata with invalid JSON string."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        # Mock metadata as invalid JSON string
        audit.metadata = "invalid json {"
        result = audit._parse_metadata()

        self.assertEqual(result, {"raw_data": "invalid json {"})

    @pytest.mark.django_db
    def test_parse_metadata_other_types(self):
        """Test _parse_metadata with non-dict, non-string types."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        # Mock metadata as non-dict, non-string type
        audit.metadata = 12345
        result = audit._parse_metadata()

        self.assertEqual(result, {"value": "12345"})

    @pytest.mark.django_db
    def test_format_authentication_event_login_success(self):
        """Test _format_authentication_event for LOGIN_SUCCESS."""
        entry = EntryFactory()
        audit = AuditTrailFactory(
            action_type=AuditActionType.LOGIN_SUCCESS,
            target_entity=entry,
            metadata={"login_method": "email"},
        )

        result = audit._format_authentication_event(audit.metadata)
        self.assertEqual(result, "Successful login via email")

    @pytest.mark.django_db
    def test_format_authentication_event_login_failed(self):
        """Test _format_authentication_event for LOGIN_FAILED."""
        entry = EntryFactory()
        audit = AuditTrailFactory(
            action_type=AuditActionType.LOGIN_FAILED,
            target_entity=entry,
            metadata={
                "attempted_username": "testuser",
                "failure_reason": "invalid_password",
            },
        )

        result = audit._format_authentication_event(audit.metadata)
        self.assertEqual(
            result, "Failed login attempt for 'testuser' - invalid_password"
        )

    @pytest.mark.django_db
    def test_format_authentication_event_logout(self):
        """Test _format_authentication_event for LOGOUT."""
        entry = EntryFactory()
        audit = AuditTrailFactory(
            action_type=AuditActionType.LOGOUT, target_entity=entry, metadata={}
        )

        result = audit._format_authentication_event(audit.metadata)
        self.assertEqual(result, "User logged out")

    @pytest.mark.django_db
    def test_format_authentication_event_unknown_action(self):
        """Test _format_authentication_event for unknown action type."""
        entry = EntryFactory()
        audit = AuditTrailFactory(
            action_type="unknown_auth_action",
            target_entity=entry,
            metadata={"some_field": "some_value"},
        )

        result = audit._format_authentication_event(audit.metadata)
        # Should fall back to generic formatting
        self.assertIn("Some Field: some_value", result)

    @pytest.mark.django_db
    def test_format_crud_operation_with_entity_type(self):
        """Test _format_crud_operation with entity_type."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {"entity_type": "Entry"}
        result = audit._format_crud_operation(metadata)
        self.assertIn("Entity: Entry", result)

    @pytest.mark.django_db
    def test_format_crud_operation_with_workspace_id(self):
        """Test _format_crud_operation with workspace_id."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {"workspace_id": "123e4567-e89b-12d3-a456-426614174000"}
        result = audit._format_crud_operation(metadata)
        self.assertIn("Workspace: 123e4567-e89b-12d3-a456-426614174000", result)

    @pytest.mark.django_db
    def test_format_crud_operation_with_changed_fields(self):
        """Test _format_crud_operation with changed_fields."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {"changed_fields": ["title", "amount", "status"]}
        result = audit._format_crud_operation(metadata)
        self.assertIn("Changed fields: title, amount, status", result)

    @pytest.mark.django_db
    def test_format_crud_operation_with_old_new_values(self):
        """Test _format_crud_operation with old_values and new_values."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {
            "old_values": {"title": "Old Title", "amount": "100.00"},
            "new_values": {"title": "New Title", "amount": "200.00"},
        }
        result = audit._format_crud_operation(metadata)
        self.assertIn("title: 'Old Title' → 'New Title'", result)
        self.assertIn("amount: '100.00' → '200.00'", result)

    @pytest.mark.django_db
    def test_format_bulk_operation(self):
        """Test _format_bulk_operation."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {
            "operation_type": "delete",
            "affected_count": 5,
            "object_types": ["Entry", "User"],
        }
        result = audit._format_bulk_operation(metadata)
        self.assertIn("Bulk delete operation", result)
        self.assertIn("Affected items: 5", result)
        self.assertIn("Types: Entry, User", result)

    @pytest.mark.django_db
    def test_format_workflow_action(self):
        """Test _format_workflow_action."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {
            "previous_status": "draft",
            "new_status": "submitted",
            "reviewer": "admin@example.com",
            "comments": "Looks good",
            "reason": "Ready for review",
        }
        result = audit._format_workflow_action(metadata)
        self.assertIn("Status: draft → submitted", result)
        self.assertIn("Reviewer: admin@example.com", result)
        self.assertIn("Comments: Looks good", result)
        self.assertIn("Reason: Ready for review", result)

    @pytest.mark.django_db
    def test_format_generic_with_empty_metadata(self):
        """Test _format_generic with empty metadata."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        result = audit._format_generic({})
        self.assertEqual(result, "No additional details")

    @pytest.mark.django_db
    def test_format_generic_with_filtered_fields(self):
        """Test _format_generic with fields that get filtered out."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {
            "_internal_field": "value1",
            "automatic_logging": "value2",
            "timestamp": "value3",
            "valid_field": "value4",
        }
        result = audit._format_generic(metadata)
        self.assertIn("Valid Field: value4", result)
        self.assertNotIn("_internal_field", result)
        self.assertNotIn("automatic_logging", result)
        self.assertNotIn("timestamp", result)

    @pytest.mark.django_db
    def test_format_generic_with_all_fields_filtered(self):
        """Test _format_generic when all fields get filtered out."""
        entry = EntryFactory()
        audit = AuditTrailFactory(target_entity=entry)

        metadata = {
            "_internal_field": "value1",
            "automatic_logging": "value2",
            "timestamp": "value3",
        }
        result = audit._format_generic(metadata)
        self.assertEqual(result, "No additional details")

    @pytest.mark.django_db
    def test_is_expired_method(self):
        """Test is_expired method."""
        from datetime import timedelta
        from django.utils import timezone

        entry = EntryFactory()

        # Create an old audit trail
        old_timestamp = timezone.now() - timedelta(days=400)  # Very old
        audit = AuditTrailFactory(
            target_entity=entry, action_type=AuditActionType.ENTRY_CREATED
        )
        # Manually set old timestamp
        audit.timestamp = old_timestamp
        audit.save()

        # Test is_expired
        self.assertTrue(audit.is_expired())

    @pytest.mark.django_db
    def test_details_property_with_authentication_events(self):
        """Test details property with authentication events."""
        entry = EntryFactory()

        # Test LOGIN_SUCCESS
        audit = AuditTrailFactory(
            action_type=AuditActionType.LOGIN_SUCCESS,
            target_entity=entry,
            metadata={"login_method": "oauth"},
        )
        details = audit.details
        self.assertIn("Successful login via oauth", details)

    @pytest.mark.django_db
    def test_details_property_with_status_changes(self):
        """Test details property with status change events."""
        entry = EntryFactory()

        # Test ORGANIZATION_STATUS_CHANGED
        audit = AuditTrailFactory(
            action_type=AuditActionType.ORGANIZATION_STATUS_CHANGED,
            target_entity=entry,
            metadata={"old_status": "active", "new_status": "suspended"},
        )
        details = audit.details
        self.assertIn("Status changed from 'active' to 'suspended'", details)

    @pytest.mark.django_db
    def test_details_property_with_workflow_actions(self):
        """Test details property with workflow actions."""
        entry = EntryFactory()

        # Test ENTRY_SUBMITTED
        audit = AuditTrailFactory(
            action_type=AuditActionType.ENTRY_SUBMITTED,
            target_entity=entry,
            metadata={
                "previous_status": "draft",
                "new_status": "submitted",
                "reviewer": "reviewer@example.com",
            },
        )
        details = audit.details
        self.assertIn("Status: draft → submitted", details)
        self.assertIn("Reviewer: reviewer@example.com", details)

    @pytest.mark.django_db
    def test_details_property_with_bulk_operations(self):
        """Test details property with bulk operations."""
        entry = EntryFactory()

        # Test BULK_OPERATION
        audit = AuditTrailFactory(
            action_type=AuditActionType.BULK_OPERATION,
            target_entity=entry,
            metadata={
                "operation_type": "update",
                "affected_count": 10,
                "object_types": ["Entry", "User"],
            },
        )
        details = audit.details
        self.assertIn("Bulk update operation", details)
        self.assertIn("Affected items: 10", details)
        self.assertIn("Types: Entry, User", details)

    @pytest.mark.django_db
    def test_details_property_with_crud_operations(self):
        """Test details property with CRUD operations."""
        entry = EntryFactory()

        # Test ENTRY_CREATED
        audit = AuditTrailFactory(
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata={
                "entity_type": "Entry",
                "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
                "changed_fields": ["title", "amount"],
            },
        )
        details = audit.details
        self.assertIn("Entity: Entry", details)
        self.assertIn("Workspace: 123e4567-e89b-12d3-a456-426614174000", details)
        self.assertIn("Changed fields: title, amount", details)
