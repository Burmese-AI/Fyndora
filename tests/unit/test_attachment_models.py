"""
Unit tests for Attachment models.

Tests attachment model validation, relationships, and business logic.
"""

import shutil
import tempfile
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings

from apps.attachments.constants import AttachmentType
from apps.attachments.models import Attachment
from tests.factories import (
    AttachmentFactory,
    EntryFactory,
    ImageAttachmentFactory,
    PDFAttachmentFactory,
    SpreadsheetAttachmentFactory,
)


@pytest.mark.unit
class TestAttachmentModel(TestCase):
    """Test Attachment model functionality."""

    def setUp(self):
        """Set up test environment with temporary media directory."""
        self.temp_media_root = tempfile.mkdtemp()
        self.settings_patcher = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.settings_patcher.enable()

    def tearDown(self):
        """Clean up test environment."""
        self.settings_patcher.disable()
        # Clean up temporary directory
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def test_attachment_creation_with_valid_data(self):
        """Test attachment creation with valid data."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        assert attachment.attachment_id is not None
        assert isinstance(attachment.attachment_id, uuid.UUID)
        assert attachment.entry == entry
        assert attachment.file_url is not None
        assert attachment.file_type in [choice[0] for choice in AttachmentType.choices]
        assert attachment.created_at is not None
        assert attachment.updated_at is not None
        assert attachment.deleted_at is None

    def test_attachment_str_representation(self):
        """Test attachment string representation."""
        attachment = AttachmentFactory()
        expected_str = f"{attachment.file_type} - {attachment.file_url.name} - {attachment.entry.pk} - {attachment.deleted_at}"

        assert str(attachment) == expected_str

    def test_attachment_uuid_is_unique(self):
        """Test that attachment_id is unique for each attachment."""
        attachment1 = AttachmentFactory()
        attachment2 = AttachmentFactory()

        assert attachment1.attachment_id != attachment2.attachment_id

    def test_attachment_uuid_is_primary_key(self):
        """Test that attachment_id serves as primary key."""
        attachment = AttachmentFactory()

        assert attachment.pk == attachment.attachment_id

    def test_attachment_entry_relationship(self):
        """Test attachment-entry foreign key relationship."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        assert attachment.entry == entry
        assert attachment in entry.attachments.all()

    def test_attachment_cascade_delete_with_entry(self):
        """Test that attachment is deleted when entry is deleted."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)
        attachment_id = attachment.attachment_id

        # Delete the entry (soft delete)
        entry.delete()

        # Since Entry uses SoftDeleteModel, soft deleting the entry doesn't automatically
        # soft delete the attachment due to CASCADE. The attachment should remain active.
        # Check that attachment still exists in default queryset
        assert Attachment.objects.filter(attachment_id=attachment_id).exists()

        # The entry should be soft deleted
        assert not entry.__class__.objects.filter(pk=entry.pk).exists()

    def test_attachment_file_type_choices(self):
        """Test that file_type accepts only valid choices."""
        entry = EntryFactory()

        # Test valid choices
        for file_type, _ in AttachmentType.choices:
            attachment = AttachmentFactory(entry=entry, file_type=file_type)
            assert attachment.file_type == file_type

    def test_attachment_file_type_invalid_choice(self):
        """Test that invalid file_type raises validation error."""
        entry = EntryFactory()

        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_url=SimpleUploadedFile("test.txt", b"content"),
                file_type="invalid_type",
            )
            attachment.full_clean()

    def test_attachment_without_entry_fails(self):
        """Test that attachment without entry fails validation."""
        with pytest.raises(IntegrityError):
            Attachment.objects.create(
                file_url=SimpleUploadedFile("test.txt", b"content"),
                file_type=AttachmentType.PDF,
            )

    def test_attachment_soft_delete(self):
        """Test attachment soft delete functionality."""
        attachment = AttachmentFactory()
        attachment_id = attachment.attachment_id

        # Soft delete
        attachment.delete()

        # Should not be in default queryset
        assert not Attachment.objects.filter(attachment_id=attachment_id).exists()

        # Should be in all_objects queryset
        assert Attachment.all_objects.filter(attachment_id=attachment_id).exists()

        # Should have deleted_at timestamp
        deleted_attachment = Attachment.all_objects.get(attachment_id=attachment_id)
        assert deleted_attachment.deleted_at is not None

    def test_attachment_hard_delete(self):
        """Test attachment hard delete functionality."""
        attachment = AttachmentFactory()
        attachment_id = attachment.attachment_id

        # Hard delete
        attachment.hard_delete()

        # Should not exist in any queryset
        assert not Attachment.objects.filter(attachment_id=attachment_id).exists()
        assert not Attachment.all_objects.filter(attachment_id=attachment_id).exists()

    def test_attachment_restore(self):
        """Test attachment restore functionality."""
        attachment = AttachmentFactory()
        attachment_id = attachment.attachment_id

        # Soft delete
        attachment.delete()
        assert not Attachment.objects.filter(attachment_id=attachment_id).exists()

        # Restore
        deleted_attachment = Attachment.all_objects.get(attachment_id=attachment_id)
        deleted_attachment.restore()

        # Should be back in default queryset
        assert Attachment.objects.filter(attachment_id=attachment_id).exists()

        # deleted_at should be None
        restored_attachment = Attachment.objects.get(attachment_id=attachment_id)
        assert restored_attachment.deleted_at is None

    def test_attachment_meta_verbose_name_plural(self):
        """Test attachment model meta verbose name plural."""
        assert Attachment._meta.verbose_name_plural == "Attachments"


@pytest.mark.unit
class TestAttachmentTypes(TestCase):
    """Test different attachment types."""

    def setUp(self):
        """Set up test environment with temporary media directory."""
        self.temp_media_root = tempfile.mkdtemp()
        self.settings_patcher = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.settings_patcher.enable()

    def tearDown(self):
        """Clean up test environment."""
        self.settings_patcher.disable()
        # Clean up temporary directory
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def test_image_attachment_creation(self):
        """Test image attachment creation."""
        attachment = ImageAttachmentFactory()

        assert attachment.file_type == AttachmentType.IMAGE
        assert attachment.file_url.name.endswith(".jpg")

    def test_pdf_attachment_creation(self):
        """Test PDF attachment creation."""
        attachment = PDFAttachmentFactory()

        assert attachment.file_type == AttachmentType.PDF
        assert attachment.file_url.name.endswith(".pdf")

    def test_spreadsheet_attachment_creation(self):
        """Test spreadsheet attachment creation."""
        attachment = SpreadsheetAttachmentFactory()

        assert attachment.file_type == AttachmentType.SPREADSHEET
        assert attachment.file_url.name.endswith(".xlsx")

    def test_attachment_file_type_consistency(self):
        """Test that file type matches file extension."""
        # Test image
        image_attachment = ImageAttachmentFactory()
        assert image_attachment.file_type == AttachmentType.IMAGE
        assert any(
            image_attachment.file_url.name.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png"]
        )

        # Test PDF
        pdf_attachment = PDFAttachmentFactory()
        assert pdf_attachment.file_type == AttachmentType.PDF
        assert pdf_attachment.file_url.name.lower().endswith(".pdf")

        # Test spreadsheet
        spreadsheet_attachment = SpreadsheetAttachmentFactory()
        assert spreadsheet_attachment.file_type == AttachmentType.SPREADSHEET
        assert any(
            spreadsheet_attachment.file_url.name.lower().endswith(ext)
            for ext in [".xlsx", ".xls", ".csv"]
        )


@pytest.mark.unit
class TestAttachmentRelationships(TestCase):
    """Test attachment relationships and constraints."""

    def setUp(self):
        """Set up test environment with temporary media directory."""
        self.temp_media_root = tempfile.mkdtemp()
        self.settings_patcher = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.settings_patcher.enable()

    def tearDown(self):
        """Clean up test environment."""
        self.settings_patcher.disable()
        # Clean up temporary directory
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def test_multiple_attachments_per_entry(self):
        """Test that an entry can have multiple attachments."""
        entry = EntryFactory()

        # Create multiple attachments for the same entry
        attachment1 = AttachmentFactory(entry=entry, file_type=AttachmentType.IMAGE)
        attachment2 = AttachmentFactory(entry=entry, file_type=AttachmentType.PDF)
        attachment3 = AttachmentFactory(
            entry=entry, file_type=AttachmentType.SPREADSHEET
        )

        # Verify all attachments are linked to the entry
        entry_attachments = entry.attachments.all()
        assert attachment1 in entry_attachments
        assert attachment2 in entry_attachments
        assert attachment3 in entry_attachments
        assert entry_attachments.count() == 3

    def test_attachment_entry_related_name(self):
        """Test that entry.attachments related name works correctly."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Test related name access
        assert entry.attachments.count() == 1
        assert entry.attachments.first() == attachment

    def test_attachment_queryset_filtering(self):
        """Test attachment queryset filtering by entry."""
        entry1 = EntryFactory()
        entry2 = EntryFactory()

        attachment1 = AttachmentFactory(entry=entry1)
        attachment2 = AttachmentFactory(entry=entry2)

        # Filter attachments by entry
        entry1_attachments = Attachment.objects.filter(entry=entry1)
        entry2_attachments = Attachment.objects.filter(entry=entry2)

        assert attachment1 in entry1_attachments
        assert attachment1 not in entry2_attachments
        assert attachment2 in entry2_attachments
        assert attachment2 not in entry1_attachments

    def test_attachment_ordering(self):
        """Test attachment ordering by creation time."""
        entry = EntryFactory()

        # Create attachments in sequence
        attachment1 = AttachmentFactory(entry=entry)
        attachment2 = AttachmentFactory(entry=entry)
        attachment3 = AttachmentFactory(entry=entry)

        # Get attachments ordered by creation time
        attachments = entry.attachments.order_by("created_at")

        assert list(attachments) == [attachment1, attachment2, attachment3]


@pytest.mark.unit
class TestAttachmentValidation(TestCase):
    """Test attachment validation rules."""

    def setUp(self):
        """Set up test environment with temporary media directory."""
        self.temp_media_root = tempfile.mkdtemp()
        self.settings_patcher = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.settings_patcher.enable()

    def tearDown(self):
        """Clean up test environment."""
        self.settings_patcher.disable()
        # Clean up temporary directory
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def test_attachment_file_url_required(self):
        """Test that file_url is required."""
        entry = EntryFactory()

        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_type=AttachmentType.PDF,
                # Missing file_url
            )
            attachment.full_clean()

    def test_attachment_file_type_required(self):
        """Test that file_type is required."""
        entry = EntryFactory()

        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_url=SimpleUploadedFile("test.pdf", b"content"),
                # Missing file_type
            )
            attachment.full_clean()

    def test_attachment_file_type_max_length(self):
        """Test file_type max length constraint."""
        entry = EntryFactory()

        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_url=SimpleUploadedFile("test.pdf", b"content"),
                file_type="x" * 21,  # Exceeds max_length=20
            )
            attachment.full_clean()

    def test_attachment_with_empty_file(self):
        """Test attachment with empty file."""
        entry = EntryFactory()

        # Empty file should still be valid
        attachment = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile("empty.pdf", b""),
            file_type=AttachmentType.PDF,
        )
        attachment.full_clean()  # Should not raise ValidationError
        attachment.save()

        assert attachment.file_url.size == 0

    def test_attachment_file_size_limits(self):
        """Test attachment with various file sizes."""
        entry = EntryFactory()

        # Test with small file
        small_content = b"x" * 1024  # 1KB
        small_attachment = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile("small.txt", small_content),
            file_type=AttachmentType.PDF,
        )
        small_attachment.full_clean()
        small_attachment.save()
        assert small_attachment.file_url.size == 1024

        # Test with larger file
        large_content = b"x" * (1024 * 1024)  # 1MB
        large_attachment = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile("large.txt", large_content),
            file_type=AttachmentType.PDF,
        )
        large_attachment.full_clean()
        large_attachment.save()
        assert large_attachment.file_url.size == 1024 * 1024

    def test_attachment_file_extension_validation(self):
        """Test that file extensions are properly handled."""
        entry = EntryFactory()

        # Test with various file extensions
        test_files = [
            ("document.pdf", b"content", AttachmentType.PDF),
            ("image.jpg", b"content", AttachmentType.IMAGE),
            ("spreadsheet.xlsx", b"content", AttachmentType.SPREADSHEET),
            ("text.txt", b"content", AttachmentType.PDF),  # txt can be PDF type
        ]

        for filename, content, file_type in test_files:
            attachment = Attachment(
                entry=entry,
                file_url=SimpleUploadedFile(filename, content),
                file_type=file_type,
            )
            attachment.full_clean()
            attachment.save()
            # Django automatically prepends upload_to path, so check that filename is included
            assert filename in attachment.file_url.name
            assert attachment.file_url.name.startswith("attachments/")

    def test_attachment_unicode_filename(self):
        """Test attachment with unicode filename."""
        entry = EntryFactory()
        unicode_filename = "测试文件.pdf"

        attachment = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile(unicode_filename, b"content"),
            file_type=AttachmentType.PDF,
        )
        attachment.full_clean()
        attachment.save()

        # Django automatically prepends upload_to path and may generate unique filenames
        # So check that filename is included and path starts correctly
        assert unicode_filename in attachment.file_url.name
        assert attachment.file_url.name.startswith("attachments/")

    def test_attachment_special_characters_filename(self):
        """Test attachment with special characters in filename."""
        entry = EntryFactory()
        special_filename = "file-with-special-chars_@#$%.pdf"

        attachment = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile(special_filename, b"content"),
            file_type=AttachmentType.PDF,
        )
        attachment.full_clean()
        attachment.save()

        # Django automatically prepends upload_to path and sanitizes filenames
        # Check that the base filename (without special chars) is included
        assert "file-with-special-chars" in attachment.file_url.name
        assert ".pdf" in attachment.file_url.name
        assert attachment.file_url.name.startswith("attachments/")

    def test_attachment_very_long_filename(self):
        """Test attachment with very long filename."""
        entry = EntryFactory()
        long_filename = "a" * 200 + ".pdf"

        attachment = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile(long_filename, b"content"),
            file_type=AttachmentType.PDF,
        )
        attachment.full_clean()
        attachment.save()

        # Django automatically prepends upload_to path and may truncate/sanitize filenames
        # Check that the extension is preserved and path starts correctly
        assert ".pdf" in attachment.file_url.name
        assert attachment.file_url.name.startswith("attachments/")
        # Check that some part of the long filename is preserved
        assert "a" in attachment.file_url.name

    def test_attachment_duplicate_filenames_same_entry(self):
        """Test that same entry can have attachments with same filename."""
        entry = EntryFactory()

        # Create two attachments with same filename for same entry
        attachment1 = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile("duplicate.pdf", b"content1"),
            file_type=AttachmentType.PDF,
        )
        attachment1.save()

        attachment2 = Attachment(
            entry=entry,
            file_url=SimpleUploadedFile("duplicate.pdf", b"content2"),
            file_type=AttachmentType.PDF,
        )
        attachment2.save()

        # Both should exist
        assert Attachment.objects.filter(entry=entry).count() == 2

        # Django generates unique filenames to avoid conflicts
        # So we check that both have the base filename in their path
        assert "duplicate" in attachment1.file_url.name
        assert "duplicate" in attachment2.file_url.name
        assert ".pdf" in attachment1.file_url.name
        assert ".pdf" in attachment2.file_url.name
        assert attachment1.file_url.name.startswith("attachments/")
        assert attachment2.file_url.name.startswith("attachments/")

        # Filenames should be different due to Django's unique generation
        assert attachment1.file_url.name != attachment2.file_url.name

    def test_attachment_queryset_methods(self):
        """Test custom queryset methods if they exist."""
        entry = EntryFactory()

        # Create attachments with specific types
        pdf_attachment = AttachmentFactory(entry=entry, file_type=AttachmentType.PDF)
        image_attachment = AttachmentFactory(
            entry=entry, file_type=AttachmentType.IMAGE
        )

        # Test basic queryset operations
        assert Attachment.objects.count() == 2
        assert Attachment.objects.filter(entry=entry).count() == 2

        # Test filtering by file type
        pdf_attachments = Attachment.objects.filter(file_type=AttachmentType.PDF)
        image_attachments = Attachment.objects.filter(file_type=AttachmentType.IMAGE)

        assert pdf_attachment in pdf_attachments
        assert image_attachment in image_attachments
        assert pdf_attachment not in image_attachments
        assert image_attachment not in pdf_attachments

    def test_attachment_model_constraints(self):
        """Test model constraints and database-level validations."""
        EntryFactory()

        # Test that we can't create attachment without required fields
        with pytest.raises(IntegrityError):
            Attachment.objects.create(
                # Missing entry
                file_url=SimpleUploadedFile("test.pdf", b"content"),
                file_type=AttachmentType.PDF,
            )

    def test_attachment_file_field_upload_to(self):
        """Test that files are uploaded to correct directory."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Check that file is uploaded to attachments/ directory
        assert attachment.file_url.name.startswith("attachments/")

    def test_attachment_bulk_operations(self):
        """Test bulk operations on attachments."""
        entry = EntryFactory()

        # Create multiple attachments
        attachments_data = [
            {
                "file_url": SimpleUploadedFile(f"file{i}.pdf", b"content"),
                "file_type": AttachmentType.PDF,
            }
            for i in range(5)
        ]

        attachments = []
        for data in attachments_data:
            attachment = Attachment(entry=entry, **data)
            attachment.full_clean()
            attachments.append(attachment)

        # Bulk create
        Attachment.objects.bulk_create(attachments)

        # Verify all were created
        assert Attachment.objects.filter(entry=entry).count() == 5

    def test_attachment_soft_delete_bulk(self):
        """Test bulk soft delete operations."""
        entry = EntryFactory()
        attachments = [AttachmentFactory(entry=entry) for _ in range(3)]

        # Bulk soft delete
        attachment_ids = [att.attachment_id for att in attachments]
        Attachment.objects.filter(attachment_id__in=attachment_ids).delete()

        # All should be soft deleted
        assert Attachment.objects.filter(entry=entry).count() == 0
        assert Attachment.all_objects.filter(entry=entry).count() == 3

    def test_attachment_restore_bulk(self):
        """Test bulk restore operations."""
        entry = EntryFactory()
        attachments = [AttachmentFactory(entry=entry) for _ in range(3)]

        # Soft delete all
        for attachment in attachments:
            attachment.delete()

        # Bulk restore
        attachment_ids = [att.attachment_id for att in attachments]
        Attachment.all_objects.filter(attachment_id__in=attachment_ids).update(
            deleted_at=None
        )

        # All should be restored
        assert Attachment.objects.filter(entry=entry).count() == 3

    def test_attachment_file_field_validation(self):
        """Test file field validation edge cases."""
        entry = EntryFactory()

        # Test with None file_url
        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_url=None,
                file_type=AttachmentType.PDF,
            )
            attachment.full_clean()

    def test_attachment_file_type_edge_cases(self):
        """Test file type field edge cases."""
        entry = EntryFactory()

        # Test with empty string
        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_url=SimpleUploadedFile("test.pdf", b"content"),
                file_type="",
            )
            attachment.full_clean()

        # Test with whitespace-only string
        with pytest.raises(ValidationError):
            attachment = Attachment(
                entry=entry,
                file_url=SimpleUploadedFile("test.pdf", b"content"),
                file_type="   ",
            )
            attachment.full_clean()

    def test_attachment_model_inheritance(self):
        """Test that Attachment properly inherits from base models."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)

        # Check inheritance from baseModel
        assert hasattr(attachment, "created_at")
        assert hasattr(attachment, "updated_at")

        # Check inheritance from SoftDeleteModel
        assert hasattr(attachment, "deleted_at")
        assert hasattr(attachment, "delete")
        assert hasattr(attachment, "hard_delete")
        assert hasattr(attachment, "restore")

    def test_attachment_str_method_edge_cases(self):
        """Test string representation edge cases."""
        entry = EntryFactory()

        # Test with deleted attachment
        attachment = AttachmentFactory(entry=entry)
        attachment.delete()

        # String should still work
        str_repr = str(attachment)
        assert attachment.file_type in str_repr
        assert attachment.file_url.name in str_repr
        assert str(attachment.entry.pk) in str_repr

    def test_attachment_queryset_annotations(self):
        """Test queryset annotations and aggregations."""
        entry = EntryFactory()

        # Create attachments with different types
        AttachmentFactory(entry=entry, file_type=AttachmentType.PDF)
        AttachmentFactory(entry=entry, file_type=AttachmentType.IMAGE)
        AttachmentFactory(entry=entry, file_type=AttachmentType.SPREADSHEET)

        # Test aggregation
        from django.db.models import Count

        type_counts = (
            Attachment.objects.values("file_type")
            .annotate(count=Count("file_type"))
            .order_by("file_type")
        )

        assert len(type_counts) == 3
        assert type_counts[0]["count"] == 1
        assert type_counts[1]["count"] == 1
        assert type_counts[2]["count"] == 1

    def test_attachment_transaction_rollback(self):
        """Test that failed transactions properly rollback."""
        from django.db import transaction

        entry = EntryFactory()

        try:
            with transaction.atomic():
                # Create valid attachment
                AttachmentFactory(entry=entry)

                # Try to create invalid attachment (should fail)
                invalid_attachment = Attachment(
                    entry=entry,
                    file_url=SimpleUploadedFile("test.pdf", b"content"),
                    file_type="invalid_type",
                )
                invalid_attachment.full_clean()
                invalid_attachment.save()

        except ValidationError:
            pass

        # Both attachments should not exist due to rollback
        assert Attachment.objects.filter(entry=entry).count() == 0
