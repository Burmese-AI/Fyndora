"""
Unit tests for the auditlog app models.

Following the test plan: AuditLog App (apps.auditlog)
- AuditTrail Model Tests
- Constants Tests
- Model property tests
"""

import pytest
import uuid
import json
from datetime import datetime, timezone
from django.test import TestCase

from apps.auditlog.models import AuditTrail
from apps.auditlog.constants import (
    AUDIT_ACTION_TYPE_CHOICES,
    AUDIT_TARGET_ENTITY_TYPE_CHOICES,
)
from tests.factories import (
    AuditTrailFactory,
    EntryCreatedAuditFactory,
    StatusChangedAuditFactory,
    FlaggedAuditFactory,
    FileUploadedAuditFactory,
    SystemAuditFactory,
    AuditWithComplexMetadataFactory,
    CustomUserFactory,
)


@pytest.mark.unit
class TestAuditTrailModel(TestCase):
    """Test the AuditTrail model - essential functionality."""

    @pytest.mark.django_db
    def test_audit_trail_creation_with_defaults(self):
        """Test audit trail creation with default values."""
        audit = AuditTrailFactory()

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
        audit = SystemAuditFactory()

        self.assertIsNone(audit.user)
        self.assertIsNotNone(audit.action_type)
        self.assertIsNotNone(audit.target_entity)

    @pytest.mark.django_db
    def test_audit_trail_uuid_uniqueness(self):
        """Test that each audit trail gets a unique UUID."""
        audit1 = AuditTrailFactory()
        audit2 = AuditTrailFactory()

        self.assertNotEqual(audit1.audit_id, audit2.audit_id)
        self.assertIsInstance(audit1.audit_id, uuid.UUID)
        self.assertIsInstance(audit2.audit_id, uuid.UUID)

    @pytest.mark.django_db
    def test_audit_trail_action_type_choices(self):
        """Test that action_type respects the defined choices."""
        valid_action_types = [choice[0] for choice in AUDIT_ACTION_TYPE_CHOICES]

        for action_type in valid_action_types:
            audit = AuditTrailFactory(action_type=action_type)
            self.assertEqual(audit.action_type, action_type)

    @pytest.mark.django_db
    def test_audit_trail_target_entity_type_choices(self):
        """Test that target_entity_type respects the defined choices."""
        valid_entity_types = [choice[0] for choice in AUDIT_TARGET_ENTITY_TYPE_CHOICES]

        for entity_type in valid_entity_types:
            audit = AuditTrailFactory(target_entity_type=entity_type)
            self.assertEqual(audit.target_entity_type, entity_type)

    @pytest.mark.django_db
    def test_audit_trail_timestamp_auto_add(self):
        """Test that timestamp is automatically set on creation."""
        before_creation = datetime.now(timezone.utc)
        audit = AuditTrailFactory()
        after_creation = datetime.now(timezone.utc)

        self.assertIsNotNone(audit.timestamp)
        self.assertGreaterEqual(audit.timestamp, before_creation)
        self.assertLessEqual(audit.timestamp, after_creation)

    @pytest.mark.django_db
    def test_audit_trail_metadata_json_field(self):
        """Test that metadata is properly stored as JSON."""
        metadata = {
            "key1": "value1",
            "key2": 42,
            "key3": ["item1", "item2"],
            "key4": {"nested": "value"},
        }
        audit = AuditTrailFactory(metadata=metadata)

        self.assertEqual(audit.metadata, metadata)
        self.assertIsInstance(audit.metadata, dict)

    @pytest.mark.django_db
    def test_audit_trail_metadata_null_allowed(self):
        """Test that metadata can be null."""
        audit = AuditTrailFactory(metadata=None)
        self.assertIsNone(audit.metadata)

    @pytest.mark.django_db
    def test_audit_trail_str_representation(self):
        """Test string representation format."""
        user = CustomUserFactory(username="testuser")
        audit = AuditTrailFactory(
            user=user,
            action_type="entry_created",
            target_entity_type="entry",
            target_entity=uuid.uuid4(),
        )

        expected_parts = [
            "entry_created",
            "testuser",
            "entry",
            str(audit.target_entity),
        ]

        str_repr = str(audit)
        for part in expected_parts:
            self.assertIn(part, str_repr)

    @pytest.mark.django_db
    def test_audit_trail_str_representation_without_user(self):
        """Test string representation for system actions without user."""
        audit = SystemAuditFactory(
            action_type="entry_created", target_entity_type="system"
        )

        str_repr = str(audit)
        self.assertIn("entry_created", str_repr)
        self.assertIn("None", str_repr)  # User should be None
        self.assertIn("system", str_repr)

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
            ["target_entity_type", "target_entity"],
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
        audit = AuditTrailFactory(metadata=None)
        self.assertEqual(audit.details, "No details provided.")

    @pytest.mark.django_db
    def test_details_property_status_changed(self):
        """Test details property for status_changed action type."""
        audit = StatusChangedAuditFactory()

        details = audit.details
        self.assertIn("Status changed from", details)
        self.assertIn("pending", details)
        self.assertIn("approved", details)

    @pytest.mark.django_db
    def test_details_property_status_changed_missing_values(self):
        """Test details property for status_changed with missing values."""
        audit = AuditTrailFactory(
            action_type="status_changed", metadata={"some_other_field": "value"}
        )

        details = audit.details
        self.assertIn("Status changed from 'N/A' to 'N/A'", details)

    @pytest.mark.django_db
    def test_details_property_generic_metadata(self):
        """Test details property for generic metadata."""
        metadata = {"field_one": "value1", "field_two": "value2", "amount": 1000}
        audit = AuditTrailFactory(action_type="entry_created", metadata=metadata)

        details = audit.details
        self.assertIn("Field One: value1", details)
        self.assertIn("Field Two: value2", details)
        self.assertIn("Amount: 1000", details)

    @pytest.mark.django_db
    def test_details_property_json_string_metadata(self):
        """Test details property when metadata is a JSON string."""
        json_metadata = json.dumps({"old_status": "draft", "new_status": "submitted"})
        audit = AuditTrailFactory(action_type="status_changed", metadata=json_metadata)

        details = audit.details
        self.assertIn("Status changed from", details)
        self.assertIn("draft", details)
        self.assertIn("submitted", details)

    @pytest.mark.django_db
    def test_details_property_invalid_json_string(self):
        """Test details property with invalid JSON string."""
        invalid_json = "not valid json"
        audit = AuditTrailFactory(metadata=invalid_json)

        details = audit.details
        self.assertEqual(details, invalid_json)

    @pytest.mark.django_db
    def test_details_property_non_dict_metadata(self):
        """Test details property with non-dictionary metadata."""
        audit = AuditTrailFactory(metadata="simple string")

        details = audit.details
        self.assertEqual(details, "simple string")

    @pytest.mark.django_db
    def test_details_property_complex_metadata(self):
        """Test details property with complex nested metadata."""
        audit = AuditWithComplexMetadataFactory()

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
        self.assertIsInstance(AUDIT_ACTION_TYPE_CHOICES, tuple)
        self.assertGreater(len(AUDIT_ACTION_TYPE_CHOICES), 0)

        for choice in AUDIT_ACTION_TYPE_CHOICES:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)  # Value
            self.assertIsInstance(choice[1], str)  # Display name

    def test_audit_target_entity_type_choices_structure(self):
        """Test that target entity type choices are properly structured."""
        self.assertIsInstance(AUDIT_TARGET_ENTITY_TYPE_CHOICES, tuple)
        self.assertGreater(len(AUDIT_TARGET_ENTITY_TYPE_CHOICES), 0)

        for choice in AUDIT_TARGET_ENTITY_TYPE_CHOICES:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)  # Value
            self.assertIsInstance(choice[1], str)  # Display name

    def test_expected_action_types_present(self):
        """Test that expected action types are present."""
        expected_actions = [
            "entry_created",
            "status_changed",
            "flagged",
            "file_uploaded",
        ]
        action_values = [choice[0] for choice in AUDIT_ACTION_TYPE_CHOICES]

        for expected_action in expected_actions:
            self.assertIn(expected_action, action_values)

    def test_expected_entity_types_present(self):
        """Test that expected entity types are present."""
        expected_entities = [
            "entry",
            "attachment",
            "workspace",
            "team",
            "user",
            "system",
        ]
        entity_values = [choice[0] for choice in AUDIT_TARGET_ENTITY_TYPE_CHOICES]

        for expected_entity in expected_entities:
            self.assertIn(expected_entity, entity_values)


@pytest.mark.unit
class TestAuditTrailFactories(TestCase):
    """Test the auditlog factories."""

    @pytest.mark.django_db
    def test_entry_created_audit_factory(self):
        """Test EntryCreatedAuditFactory produces correct audit logs."""
        audit = EntryCreatedAuditFactory()

        self.assertEqual(audit.action_type, "entry_created")
        self.assertEqual(audit.target_entity_type, "entry")
        self.assertIn("entry_type", audit.metadata)
        self.assertIn("amount", audit.metadata)
        self.assertIn("submitter", audit.metadata)

    @pytest.mark.django_db
    def test_status_changed_audit_factory(self):
        """Test StatusChangedAuditFactory produces correct audit logs."""
        audit = StatusChangedAuditFactory()

        self.assertEqual(audit.action_type, "status_changed")
        self.assertEqual(audit.target_entity_type, "entry")
        self.assertIn("old_status", audit.metadata)
        self.assertIn("new_status", audit.metadata)
        self.assertIn("reviewer", audit.metadata)

    @pytest.mark.django_db
    def test_flagged_audit_factory(self):
        """Test FlaggedAuditFactory produces correct audit logs."""
        audit = FlaggedAuditFactory()

        self.assertEqual(audit.action_type, "flagged")
        self.assertIn("flag_reason", audit.metadata)
        self.assertIn("flagged_by", audit.metadata)
        self.assertIn("severity", audit.metadata)

    @pytest.mark.django_db
    def test_file_uploaded_audit_factory(self):
        """Test FileUploadedAuditFactory produces correct audit logs."""
        audit = FileUploadedAuditFactory()

        self.assertEqual(audit.action_type, "file_uploaded")
        self.assertEqual(audit.target_entity_type, "attachment")
        self.assertIn("filename", audit.metadata)
        self.assertIn("file_size", audit.metadata)
        self.assertIn("uploaded_by", audit.metadata)

    @pytest.mark.django_db
    def test_system_audit_factory(self):
        """Test SystemAuditFactory produces correct audit logs."""
        audit = SystemAuditFactory()

        self.assertIsNone(audit.user)
        self.assertEqual(audit.target_entity_type, "system")
        self.assertIn("system_action", audit.metadata)
        self.assertIn("triggered_by", audit.metadata)

    @pytest.mark.django_db
    def test_complex_metadata_factory(self):
        """Test AuditWithComplexMetadataFactory produces correct structure."""
        audit = AuditWithComplexMetadataFactory()

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
        long_action_type = "x" * 100  # Max length for action_type
        long_entity_type = "y" * 100  # Max length for target_entity_type

        # These should not raise validation errors if within max_length
        audit = AuditTrailFactory(
            action_type=long_action_type[:100],
            target_entity_type=long_entity_type[:100],
        )

        self.assertEqual(len(audit.action_type), 100)
        self.assertEqual(len(audit.target_entity_type), 100)

    @pytest.mark.django_db
    def test_audit_trail_with_large_metadata(self):
        """Test audit trail with large metadata objects."""
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        audit = AuditTrailFactory(metadata=large_metadata)
        self.assertEqual(len(audit.metadata), 100)

        # Test that it can be retrieved correctly
        audit.refresh_from_db()
        self.assertEqual(len(audit.metadata), 100)

    @pytest.mark.django_db
    def test_audit_trail_with_special_characters_in_metadata(self):
        """Test audit trail with special characters in metadata."""
        special_metadata = {
            "unicode": "🔥💻🎯",
            "quotes": "This has \"quotes\" and 'apostrophes'",
            "newlines": "Line 1\nLine 2\rLine 3",
            "html": "<script>alert('test')</script>",
            "json_like": '{"nested": "json"}',
            "null_char": "text\x00with\x00nulls",
        }

        audit = AuditTrailFactory(metadata=special_metadata)
        audit.refresh_from_db()

        # All special characters should be preserved
        self.assertEqual(audit.metadata["unicode"], "🔥💻🎯")
        self.assertIn("quotes", audit.metadata["quotes"])
        self.assertIn("Line 1", audit.metadata["newlines"])

    @pytest.mark.django_db
    def test_audit_trail_ordering_by_timestamp(self):
        """Test that audit trails are ordered by timestamp descending."""
        # Create multiple audit trails
        AuditTrailFactory()
        AuditTrailFactory()

        # Query all audit trails
        audits = list(AuditTrail.objects.all())

        # Should be ordered by timestamp descending (newest first)
        self.assertGreaterEqual(audits[0].timestamp, audits[1].timestamp)
        self.assertGreaterEqual(audits[1].timestamp, audits[2].timestamp)
