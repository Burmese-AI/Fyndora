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

        # Delete the entry
        entry.delete()

        # Attachment should be deleted due to CASCADE
        assert not Attachment.objects.filter(attachment_id=attachment_id).exists()

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
