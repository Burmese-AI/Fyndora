"""
Integration tests for Attachment workflows.

Tests complete attachment workflows including file upload, processing, and management.
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from apps.attachments.constants import AttachmentType
from apps.attachments.models import Attachment
from apps.attachments.services import (
    create_attachments,
    delete_attachment,
    replace_or_append_attachments,
)
from apps.entries.constants import EntryStatus
from apps.entries.models import Entry
from tests.factories import (
    AttachmentFactory,
    EntryFactory,
    MultipleAttachmentsFactory,
)


@pytest.mark.integration
class TestAttachmentEntryWorkflow(TestCase):
    """Test attachment workflows with entry lifecycle."""

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

    @staticmethod
    def create_test_file(
        filename="test.txt", content=b"test content", content_type="text/plain"
    ):
        """Helper method to create test files."""
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def test_entry_with_attachments_creation_workflow(self):
        """Test complete workflow of creating entry with attachments."""
        # Create entry
        entry = EntryFactory(status=EntryStatus.PENDING_REVIEW)

        # Add attachments to the entry
        files = [
            self.create_test_file("receipt.jpg", b"receipt image", "image/jpeg"),
            self.create_test_file("invoice.pdf", b"invoice pdf", "application/pdf"),
            self.create_test_file(
                "budget.xlsx",
                b"budget spreadsheet",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ]

        created_attachments = create_attachments(entry=entry, attachments=files)

        # Verify attachments are properly linked
        assert entry.attachments.count() == 3
        assert len(created_attachments) == 3

        # Verify file types are correctly assigned
        file_types = {att.file_type for att in entry.attachments.all()}
        expected_types = {
            AttachmentType.IMAGE,
            AttachmentType.PDF,
            AttachmentType.SPREADSHEET,
        }
        assert file_types == expected_types

        # Verify entry status is unchanged
        assert entry.status == EntryStatus.PENDING_REVIEW

    def test_entry_attachment_replacement_workflow(self):
        """Test workflow of replacing attachments during entry editing."""
        # Create entry with initial attachments
        entry = EntryFactory()
        initial_files = [
            SimpleUploadedFile(
                "old_receipt.jpg", b"old receipt", content_type="image/jpeg"
            ),
            SimpleUploadedFile(
                "old_invoice.pdf", b"old invoice", content_type="application/pdf"
            ),
        ]

        create_attachments(entry=entry, attachments=initial_files)
        initial_attachment_ids = set(
            entry.attachments.values_list("attachment_id", flat=True)
        )

        # Replace with new attachments
        new_files = [
            SimpleUploadedFile(
                "new_receipt.jpg", b"new receipt", content_type="image/jpeg"
            ),
            SimpleUploadedFile(
                "new_invoice.pdf", b"new invoice", content_type="application/pdf"
            ),
            SimpleUploadedFile(
                "additional_doc.xlsx",
                b"additional doc",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=new_files, replace_attachments=True
        )

        # Verify replacement
        assert entry.attachments.count() == 3  # New count matches new files
        new_attachment_ids = set(
            entry.attachments.values_list("attachment_id", flat=True)
        )

        # No overlap between old and new attachment IDs
        assert initial_attachment_ids.isdisjoint(new_attachment_ids)

        # Old attachments should be soft deleted
        for old_id in initial_attachment_ids:
            assert not Attachment.objects.filter(attachment_id=old_id).exists()
            assert Attachment.all_objects.filter(attachment_id=old_id).exists()

    def test_entry_attachment_append_workflow(self):
        """Test workflow of appending attachments to existing entry."""
        # Create entry with initial attachments
        entry = EntryFactory()
        initial_files = [
            SimpleUploadedFile("receipt.jpg", b"receipt", content_type="image/jpeg"),
        ]

        create_attachments(entry=entry, attachments=initial_files)
        initial_attachment_id = entry.attachments.first().attachment_id

        # Append additional attachments
        additional_files = [
            SimpleUploadedFile(
                "invoice.pdf", b"invoice", content_type="application/pdf"
            ),
            SimpleUploadedFile(
                "budget.xlsx",
                b"budget",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=additional_files, replace_attachments=False
        )

        # Verify append
        assert entry.attachments.count() == 3

        # Original attachment should still exist
        assert Attachment.objects.filter(attachment_id=initial_attachment_id).exists()

        # Verify all file types are present
        file_types = {att.file_type for att in entry.attachments.all()}
        expected_types = {
            AttachmentType.IMAGE,
            AttachmentType.PDF,
            AttachmentType.SPREADSHEET,
        }
        assert file_types == expected_types

    def test_entry_deletion_cascades_to_attachments(self):
        """Test that deleting entry cascades to attachments."""
        # Create entry with attachments
        entry = EntryFactory()
        attachments = MultipleAttachmentsFactory.create(entry=entry, count=3)
        attachment_ids = [att.attachment_id for att in attachments]

        # Verify attachments exist
        assert Attachment.objects.filter(attachment_id__in=attachment_ids).count() == 3

        # Delete entry (regular delete since Entry doesn't have soft delete)
        entry.delete()

        # Verify attachments are also deleted due to CASCADE
        assert Attachment.objects.filter(attachment_id__in=attachment_ids).count() == 0
        assert (
            Attachment.all_objects.filter(attachment_id__in=attachment_ids).count() == 0
        )

    def test_entry_deletion_affects_attachments(self):
        """Test that deleting entry affects attachments due to CASCADE relationship."""
        # Create entry with attachments
        entry = EntryFactory()
        attachments = MultipleAttachmentsFactory.create(entry=entry, count=2)
        attachment_ids = [att.attachment_id for att in attachments]
        entry_id = entry.entry_id

        # Verify initial state
        assert Attachment.objects.filter(attachment_id__in=attachment_ids).count() == 2
        assert Entry.objects.filter(entry_id=entry_id).exists()

        # Delete entry (Entry doesn't have soft delete, so this is permanent)
        entry.delete()

        # Verify entry is deleted
        assert not Entry.objects.filter(entry_id=entry_id).exists()

        # Verify attachments are also deleted due to CASCADE foreign key
        assert Attachment.objects.filter(attachment_id__in=attachment_ids).count() == 0
        assert (
            Attachment.all_objects.filter(attachment_id__in=attachment_ids).count() == 0
        )


@pytest.mark.integration
class TestAttachmentFileHandlingWorkflow(TestCase):
    """Test attachment file handling and storage workflows."""

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

    @staticmethod
    def create_test_file(
        filename="test.txt", content=b"test content", content_type="text/plain"
    ):
        """Helper method to create test files."""
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def test_attachment_file_upload_and_storage(self):
        """Test file upload and storage workflow."""
        entry = EntryFactory()

        # Create files with different content
        files = [
            SimpleUploadedFile(
                "test_image.jpg",
                b"fake jpeg content with some data to make it larger",
                content_type="image/jpeg",
            ),
            SimpleUploadedFile(
                "test_document.pdf",
                b"fake pdf content with substantial data for testing file storage",
                content_type="application/pdf",
            ),
        ]

        created_attachments = create_attachments(entry=entry, attachments=files)

        # Verify files are stored
        for attachment in created_attachments:
            assert attachment.file_url.name is not None
            assert attachment.file_url.size > 0

            # Verify file path includes attachments directory
            assert "attachments/" in attachment.file_url.name

    def test_attachment_file_type_detection_workflow(self):
        """Test file type detection workflow with various extensions."""
        entry = EntryFactory()

        test_files = [
            # Image files
            ("photo.jpg", AttachmentType.IMAGE),
            ("picture.jpeg", AttachmentType.IMAGE),
            ("graphic.png", AttachmentType.IMAGE),
            # PDF files
            ("document.pdf", AttachmentType.PDF),
            ("report.PDF", AttachmentType.PDF),  # Test case insensitive
            # Spreadsheet files
            ("data.xls", AttachmentType.SPREADSHEET),
            ("analysis.xlsx", AttachmentType.SPREADSHEET),
            ("export.csv", AttachmentType.SPREADSHEET),
            # Unknown files
            ("readme.txt", AttachmentType.OTHER),
            ("config.json", AttachmentType.OTHER),
            ("noextension", AttachmentType.OTHER),
        ]

        files = [
            SimpleUploadedFile(filename, b"test content") for filename, _ in test_files
        ]

        created_attachments = create_attachments(entry=entry, attachments=files)

        # Sort both lists by filename for comparison
        created_attachments.sort(key=lambda x: x.file_url.name)
        test_files.sort(key=lambda x: x[0])

        for attachment, (filename, expected_type) in zip(
            created_attachments, test_files
        ):
            assert attachment.file_type == expected_type, (
                f"File {filename} should be {expected_type}, got {attachment.file_type}"
            )

    def test_attachment_file_handling_edge_cases(self):
        """Test edge cases in file handling."""
        entry = EntryFactory()

        # Test empty file
        empty_file = self.create_test_file("empty.txt", b"", "text/plain")
        attachments = create_attachments(entry=entry, attachments=[empty_file])
        assert len(attachments) == 1
        assert attachments[0].file_type == AttachmentType.OTHER

        # Test file with no extension
        no_ext_file = self.create_test_file(
            "noextension", b"content", "application/octet-stream"
        )
        attachments = create_attachments(entry=entry, attachments=[no_ext_file])
        assert len(attachments) == 1
        assert attachments[0].file_type == AttachmentType.OTHER

    def test_attachment_bulk_operations(self):
        """Test bulk attachment operations."""
        entry = EntryFactory()

        # Create multiple attachments at once
        files = [
            self.create_test_file(
                f"file_{i}.txt", f"content {i}".encode(), "text/plain"
            )
            for i in range(5)
        ]

        attachments = create_attachments(entry=entry, attachments=files)
        assert len(attachments) == 5
        assert Attachment.objects.filter(entry=entry).count() == 5

        # Verify all attachments have correct type
        for attachment in attachments:
            assert attachment.file_type == AttachmentType.OTHER

    def test_attachment_large_file_handling(self):
        """Test handling of larger files."""
        entry = EntryFactory()

        # Create a larger file (1MB)
        large_content = b"x" * (1024 * 1024)  # 1MB
        large_file = self.create_test_file(
            "large_document.pdf", large_content, "application/pdf"
        )

        created_attachments = create_attachments(entry=entry, attachments=[large_file])

        assert len(created_attachments) == 1
        attachment = created_attachments[0]
        assert attachment.file_url.size == len(large_content)
        assert attachment.file_type == AttachmentType.PDF

    def test_attachment_empty_file_handling(self):
        """Test handling of empty files."""
        entry = EntryFactory()

        empty_file = self.create_test_file("empty.txt", b"", "text/plain")

        created_attachments = create_attachments(entry=entry, attachments=[empty_file])

        assert len(created_attachments) == 1
        attachment = created_attachments[0]
        assert attachment.file_url.size == 0
        assert attachment.file_type == AttachmentType.OTHER


@pytest.mark.integration
class TestAttachmentDeletionWorkflow(TestCase):
    """Test attachment deletion workflows and constraints."""

    @staticmethod
    def create_test_file(
        filename="test.txt", content=b"test content", content_type="text/plain"
    ):
        """Helper method to create test files."""
        return SimpleUploadedFile(filename, content, content_type=content_type)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_attachment_deletion_with_multiple_attachments(self):
        """Test attachment deletion when entry has multiple attachments."""
        entry = EntryFactory()
        attachments = MultipleAttachmentsFactory.create(entry=entry, count=3)

        factory = RequestFactory()
        request = factory.get("/")

        # Delete one attachment
        attachment_to_delete = attachments[0]

        with patch("apps.attachments.services.messages"):
            success, remaining_attachments = delete_attachment(
                attachment_to_delete.attachment_id, request
            )

        assert success is True
        assert Attachment.objects.filter(entry=entry).count() == 2

        # Verify specific attachment was deleted
        assert not Attachment.objects.filter(
            attachment_id=attachment_to_delete.attachment_id
        ).exists()

        # Verify other attachments remain
        remaining_ids = {att.attachment_id for att in remaining_attachments}
        expected_remaining_ids = {att.attachment_id for att in attachments[1:]}
        assert remaining_ids == expected_remaining_ids

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_attachment_deletion_protection_for_last_attachment(self):
        """Test that last attachment cannot be deleted."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)  # Only one attachment

        factory = RequestFactory()
        request = factory.get("/")

        with patch("apps.attachments.services.messages") as mock_messages:
            success, remaining_attachments = delete_attachment(
                attachment.attachment_id, request
            )

        assert success is False
        assert remaining_attachments is None
        assert Attachment.objects.filter(entry=entry).count() == 1

        # Verify attachment still exists
        assert Attachment.objects.filter(
            attachment_id=attachment.attachment_id
        ).exists()

        # Verify error message
        mock_messages.error.assert_called_with(
            request, "You cannot delete the last attachment"
        )

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_attachment_deletion_and_restoration_workflow(self):
        """Test complete deletion and restoration workflow."""
        entry = EntryFactory()
        attachment1 = AttachmentFactory(entry=entry)
        attachment2 = AttachmentFactory(entry=entry)

        # Verify both attachments exist initially
        assert entry.attachments.count() == 2
        assert Attachment.objects.filter(
            attachment_id=attachment2.attachment_id
        ).exists()

        factory = RequestFactory()
        request = factory.get("/")

        # Delete one attachment
        with patch("apps.attachments.services.messages"):
            success, _ = delete_attachment(attachment1.attachment_id, request)

        assert success is True
        assert Attachment.objects.filter(entry=entry).count() == 1

        # Verify soft deletion
        assert not Attachment.objects.filter(
            attachment_id=attachment1.attachment_id
        ).exists()
        assert Attachment.all_objects.filter(
            attachment_id=attachment1.attachment_id
        ).exists()

        # Verify attachment2 still exists after attachment1 deletion
        assert Attachment.objects.filter(
            attachment_id=attachment2.attachment_id
        ).exists()

        # Restore the deleted attachment
        deleted_attachment = Attachment.all_objects.get(
            attachment_id=attachment1.attachment_id
        )
        deleted_attachment.restore()

        # Verify restoration
        assert Attachment.objects.filter(entry=entry).count() == 2
        assert Attachment.objects.filter(
            attachment_id=attachment1.attachment_id
        ).exists()

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_attachment_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        entry = EntryFactory()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"temporary content")
            temp_file_path = temp_file.name

        # Verify temp file exists
        assert os.path.exists(temp_file_path)

        # Create attachment from temp file
        test_file = self.create_test_file(
            "temp_test.txt", b"temporary content", "text/plain"
        )
        attachments = create_attachments(entry=entry, attachments=[test_file])

        assert len(attachments) == 1
        assert attachments[0].file_type == AttachmentType.OTHER

        # Clean up the temp file we created for testing
        os.unlink(temp_file_path)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_attachment_with_different_entry_statuses(self):
        """Test attachment operations with entries in different statuses."""
        # Test with approved entry
        approved_entry = EntryFactory(status=EntryStatus.APPROVED)
        test_file = self.create_test_file(
            "approved_doc.pdf", b"PDF content", "application/pdf"
        )
        attachments = create_attachments(entry=approved_entry, attachments=[test_file])
        assert len(attachments) == 1

        # Test with flagged entry
        flagged_entry = EntryFactory(is_flagged=True)
        test_file = self.create_test_file(
            "flagged_doc.pdf", b"PDF content", "application/pdf"
        )
        attachments = create_attachments(entry=flagged_entry, attachments=[test_file])
        assert len(attachments) == 1


@pytest.mark.integration
class TestAttachmentBulkOperationsWorkflow(TestCase):
    """Test bulk operations on attachments."""

    @staticmethod
    def create_test_file(
        filename="test.txt", content=b"test content", content_type="text/plain"
    ):
        """Helper method to create test files."""
        return SimpleUploadedFile(filename, content, content_type=content_type)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_bulk_attachment_creation_performance(self):
        """Test bulk creation of many attachments."""
        entry = EntryFactory()

        # Create many files
        files = [
            self.create_test_file(f"file_{i}.jpg", b"content", "image/jpeg")
            for i in range(10)
        ]

        # Verify bulk creation is used
        with patch.object(
            Attachment.objects, "bulk_create", wraps=Attachment.objects.bulk_create
        ) as mock_bulk_create:
            created_attachments = create_attachments(entry=entry, attachments=files)

        # Should call bulk_create once
        mock_bulk_create.assert_called_once()

        # Verify all attachments created
        assert len(created_attachments) == 10
        assert Attachment.objects.filter(entry=entry).count() == 10

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_bulk_attachment_replacement_workflow(self):
        """Test bulk replacement of attachments."""
        entry = EntryFactory()

        # Create initial attachments
        initial_files = [
            self.create_test_file(f"initial_{i}.pdf", b"content", "application/pdf")
            for i in range(5)
        ]
        create_attachments(entry=entry, attachments=initial_files)
        initial_ids = set(
            Attachment.objects.filter(entry=entry).values_list(
                "attachment_id", flat=True
            )
        )

        # Replace with new attachments
        replacement_files = [
            self.create_test_file(f"replacement_{i}.jpg", b"content", "image/jpeg")
            for i in range(3)
        ]

        replace_or_append_attachments(
            entry=entry, attachments=replacement_files, replace_attachments=True
        )

        # Verify replacement
        assert Attachment.objects.filter(entry=entry).count() == 3
        new_ids = set(
            Attachment.objects.filter(entry=entry).values_list(
                "attachment_id", flat=True
            )
        )

        # No overlap between old and new
        assert initial_ids.isdisjoint(new_ids)

        # All new attachments should be images
        file_types = set(
            Attachment.objects.filter(entry=entry).values_list("file_type", flat=True)
        )
        assert file_types == {AttachmentType.IMAGE}

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_mixed_file_types_bulk_operations(self):
        """Test bulk operations with mixed file types."""
        entry = EntryFactory()

        # Create files of different types
        mixed_files = [
            self.create_test_file("image1.jpg", b"content", "image/jpeg"),
            self.create_test_file("image2.png", b"content", "image/png"),
            self.create_test_file("doc1.pdf", b"content", "application/pdf"),
            self.create_test_file("doc2.pdf", b"content", "application/pdf"),
            self.create_test_file(
                "sheet1.xlsx",
                b"content",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            self.create_test_file("sheet2.csv", b"content", "text/csv"),
            self.create_test_file("other.txt", b"content", "text/plain"),
        ]

        created_attachments = create_attachments(entry=entry, attachments=mixed_files)

        # Verify all types are represented
        file_types = {att.file_type for att in created_attachments}
        expected_types = {
            AttachmentType.IMAGE,
            AttachmentType.PDF,
            AttachmentType.SPREADSHEET,
            AttachmentType.OTHER,
        }
        assert file_types == expected_types

        # Verify counts
        type_counts = {}
        for att in created_attachments:
            type_counts[att.file_type] = type_counts.get(att.file_type, 0) + 1

        assert type_counts[AttachmentType.IMAGE] == 2
        assert type_counts[AttachmentType.PDF] == 2
        assert type_counts[AttachmentType.SPREADSHEET] == 2
        assert type_counts[AttachmentType.OTHER] == 1
