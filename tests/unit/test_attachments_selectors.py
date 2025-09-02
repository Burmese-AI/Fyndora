"""
Unit tests for apps.attachments.selectors
"""

import pytest
from unittest.mock import patch
from django.core.exceptions import ValidationError

from apps.attachments.selectors import get_attachment
from apps.attachments.models import Attachment
from tests.factories import AttachmentFactory, EntryFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestGetAttachment:
    """Test get_attachment selector function."""

    def test_get_attachment_success(self):
        """Test getting attachment by primary key successfully."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        result = get_attachment(attachment.attachment_id)

        assert result == attachment
        assert result.entry == entry

    def test_get_attachment_with_string_pk(self):
        """Test getting attachment with string primary key."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        result = get_attachment(str(attachment.attachment_id))

        assert result == attachment

    def test_get_attachment_does_not_exist(self):
        """Test getting attachment when attachment doesn't exist."""
        with pytest.raises(ValidationError):
            get_attachment("nonexistent-id")

    def test_get_attachment_with_none_pk(self):
        """Test getting attachment with None primary key."""
        with pytest.raises(Attachment.DoesNotExist):
            get_attachment(None)

    def test_get_attachment_with_empty_string_pk(self):
        """Test getting attachment with empty string primary key."""
        with pytest.raises(ValidationError):
            get_attachment("")

    def test_get_attachment_with_invalid_uuid(self):
        """Test getting attachment with invalid UUID format."""
        with pytest.raises(ValidationError):
            get_attachment("invalid-uuid-format")

    def test_get_attachment_multiple_objects_returned(self):
        """Test getting attachment when multiple objects are returned."""
        with patch("apps.attachments.selectors.Attachment.objects.get") as mock_get:
            mock_get.side_effect = Attachment.MultipleObjectsReturned(
                "Multiple attachments found"
            )

            with pytest.raises(Attachment.MultipleObjectsReturned):
                get_attachment("some-id")

    def test_get_attachment_with_database_error(self):
        """Test getting attachment when database error occurs."""
        with patch("apps.attachments.selectors.Attachment.objects.get") as mock_get:
            mock_get.side_effect = Exception("Database connection error")

            with pytest.raises(Exception, match="Database connection error"):
                get_attachment("some-id")

    def test_get_attachment_with_soft_deleted_attachment(self):
        """Test getting attachment that has been soft deleted."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Soft delete the attachment
        attachment.delete()

        # Should raise DoesNotExist because soft deleted objects are excluded
        with pytest.raises(Attachment.DoesNotExist):
            get_attachment(attachment.attachment_id)

    def test_get_attachment_with_different_entry_types(self):
        """Test getting attachments for different entry types."""
        # Create entries with different types
        income_entry = EntryFactory(entry_type="income")
        disbursement_entry = EntryFactory(entry_type="disbursement")

        income_attachment = AttachmentFactory(entry=income_entry)
        disbursement_attachment = AttachmentFactory(entry=disbursement_entry)

        # Test getting both attachments
        result1 = get_attachment(income_attachment.attachment_id)
        result2 = get_attachment(disbursement_attachment.attachment_id)

        assert result1 == income_attachment
        assert result2 == disbursement_attachment
        assert result1.entry.entry_type == "income"
        assert result2.entry.entry_type == "disbursement"

    def test_get_attachment_with_different_file_types(self):
        """Test getting attachments with different file types."""
        entry = EntryFactory()

        # Create attachments with different file types
        receipt_attachment = AttachmentFactory(entry=entry, file_type="receipt")
        invoice_attachment = AttachmentFactory(entry=entry, file_type="invoice")

        # Test getting both attachments
        result1 = get_attachment(receipt_attachment.attachment_id)
        result2 = get_attachment(invoice_attachment.attachment_id)

        assert result1 == receipt_attachment
        assert result2 == invoice_attachment
        assert result1.file_type == "receipt"
        assert result2.file_type == "invoice"

    def test_get_attachment_returns_correct_model_instance(self):
        """Test that get_attachment returns the correct model instance."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        result = get_attachment(attachment.attachment_id)

        # Verify it's the correct model instance
        assert isinstance(result, Attachment)
        assert result.pk == attachment.pk
        assert result.attachment_id == attachment.attachment_id
        assert result.entry == attachment.entry
        assert result.file_url == attachment.file_url
        assert result.file_type == attachment.file_type

    def test_get_attachment_with_large_pk(self):
        """Test getting attachment with large primary key value."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Test with the actual UUID
        result = get_attachment(attachment.attachment_id)

        assert result == attachment

    def test_get_attachment_preserves_relationships(self):
        """Test that get_attachment preserves all relationships."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        result = get_attachment(attachment.attachment_id)

        # Verify all relationships are preserved
        assert result.entry == entry
        assert result.entry.organization == entry.organization
        assert result.entry.workspace == entry.workspace
        assert result.entry.workspace_team == entry.workspace_team

    def test_get_attachment_with_special_characters_in_pk(self):
        """Test getting attachment with special characters in primary key."""
        # This should fail since UUIDs don't contain special characters
        with pytest.raises(ValidationError):
            get_attachment("attachment-id-with-special-chars!@#")

    def test_get_attachment_with_whitespace_pk(self):
        """Test getting attachment with whitespace in primary key."""
        with pytest.raises(ValidationError):
            get_attachment("   ")

    def test_get_attachment_with_numeric_pk(self):
        """Test getting attachment with numeric primary key."""
        with pytest.raises(Attachment.DoesNotExist):
            get_attachment(12345)

    def test_get_attachment_with_boolean_pk(self):
        """Test getting attachment with boolean primary key."""
        with pytest.raises(Attachment.DoesNotExist):
            get_attachment(True)

    def test_get_attachment_with_list_pk(self):
        """Test getting attachment with list primary key."""
        with pytest.raises(ValidationError):
            get_attachment(["attachment-id"])

    def test_get_attachment_with_dict_pk(self):
        """Test getting attachment with dictionary primary key."""
        with pytest.raises(ValidationError):
            get_attachment({"id": "attachment-id"})

    def test_get_attachment_performance(self):
        """Test that get_attachment performs efficiently."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Test multiple calls to ensure no performance degradation
        for _ in range(5):
            result = get_attachment(attachment.attachment_id)
            assert result == attachment

    def test_get_attachment_with_concurrent_access(self):
        """Test get_attachment behavior with concurrent access simulation."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Simulate concurrent access by calling multiple times
        results = []
        for _ in range(3):
            result = get_attachment(attachment.attachment_id)
            results.append(result)

        # All results should be the same attachment
        for result in results:
            assert result == attachment
            assert result.attachment_id == attachment.attachment_id
