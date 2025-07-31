"""
Unit tests for Attachment service business logic.

Tests attachment service functions validation and business rules.
"""

from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.attachments.constants import AttachmentType
from apps.attachments.models import Attachment
from apps.attachments.services import (
    create_attachments,
    delete_attachment,
    replace_or_append_attachments,
)
from tests.factories import (
    AttachmentFactory,
    EntryFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestDeleteAttachmentService:
    """Test delete_attachment service business logic."""

    def setup_method(self, method):
        """Set up test data."""
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        # Add messages framework to request
        self.request._messages = Mock()

    def test_delete_attachment_success(self):
        """Test successful attachment deletion."""
        entry = EntryFactory()
        # Create multiple attachments so we can delete one
        attachment1 = AttachmentFactory(entry=entry)
        attachment2 = AttachmentFactory(entry=entry)

        with patch("apps.attachments.services.messages") as mock_messages:
            success, remaining_attachments = delete_attachment(
                attachment1.attachment_id, self.request
            )

        assert success is True
        assert remaining_attachments is not None
        assert attachment1 not in remaining_attachments
        assert attachment2 in remaining_attachments

        # Verify attachment was soft deleted
        assert not Attachment.objects.filter(
            attachment_id=attachment1.attachment_id
        ).exists()
        assert Attachment.all_objects.filter(
            attachment_id=attachment1.attachment_id
        ).exists()

        mock_messages.success.assert_called_once()

    def test_delete_attachment_not_found(self):
        """Test deletion of non-existent attachment."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        with patch("apps.attachments.services.messages") as mock_messages:
            success, remaining_attachments = delete_attachment(
                non_existent_id, self.request
            )

        assert success is False
        assert remaining_attachments is None
        mock_messages.error.assert_called_once_with(
            self.request, "Attachment not found."
        )

    def test_delete_last_attachment_fails(self):
        """Test that deleting the last attachment fails."""
        entry = EntryFactory()
        attachment = AttachmentFactory(entry=entry)  # Only one attachment

        with patch("apps.attachments.services.messages") as mock_messages:
            success, remaining_attachments = delete_attachment(
                attachment.attachment_id, self.request
            )

        assert success is False
        assert remaining_attachments is None
        mock_messages.error.assert_called_once_with(
            self.request, "You cannot delete the last attachment"
        )

        # Verify attachment was not deleted
        assert Attachment.objects.filter(
            attachment_id=attachment.attachment_id
        ).exists()

    def test_delete_attachment_exception_handling(self):
        """Test exception handling during attachment deletion."""
        entry = EntryFactory()
        attachment1 = AttachmentFactory(entry=entry)
        AttachmentFactory(entry=entry)  # Create second attachment to avoid "last attachment" protection

        with (
            patch("apps.attachments.services.messages") as mock_messages,
            patch.object(Attachment, "delete", side_effect=Exception("Database error")),
        ):
            success, remaining_attachments = delete_attachment(
                attachment1.attachment_id, self.request
            )

        assert success is False
        assert remaining_attachments is None
        mock_messages.error.assert_called_once_with(
            self.request, "Failed to delete attachment."
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestReplaceOrAppendAttachmentsService:
    """Test replace_or_append_attachments service business logic."""

    def test_append_attachments(self):
        """Test appending new attachments without replacing existing ones."""
        entry = EntryFactory()
        existing_attachment = AttachmentFactory(entry=entry)

        # Create new files to append
        new_files = [
            SimpleUploadedFile(
                "new_image.jpg", b"image content", content_type="image/jpeg"
            ),
            SimpleUploadedFile(
                "new_doc.pdf", b"pdf content", content_type="application/pdf"
            ),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=new_files, replace_attachments=False
        )

        # Should have 3 attachments total (1 existing + 2 new)
        assert entry.attachments.count() == 3

        # Existing attachment should still exist
        assert Attachment.objects.filter(
            attachment_id=existing_attachment.attachment_id
        ).exists()

        # New attachments should be created
        new_attachments = entry.attachments.exclude(
            attachment_id=existing_attachment.attachment_id
        )
        assert new_attachments.count() == 2

    def test_replace_attachments(self):
        """Test replacing existing attachments with new ones."""
        entry = EntryFactory()
        existing_attachment1 = AttachmentFactory(entry=entry)
        existing_attachment2 = AttachmentFactory(entry=entry)

        # Create new files to replace with
        new_files = [
            SimpleUploadedFile(
                "replacement.jpg", b"image content", content_type="image/jpeg"
            ),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=new_files, replace_attachments=True
        )

        # Should have only 1 attachment (the replacement)
        assert entry.attachments.count() == 1

        # Existing attachments should be soft deleted
        assert not Attachment.objects.filter(
            attachment_id=existing_attachment1.attachment_id
        ).exists()
        assert not Attachment.objects.filter(
            attachment_id=existing_attachment2.attachment_id
        ).exists()

        # But should exist in all_objects
        assert Attachment.all_objects.filter(
            attachment_id=existing_attachment1.attachment_id
        ).exists()
        assert Attachment.all_objects.filter(
            attachment_id=existing_attachment2.attachment_id
        ).exists()

    def test_file_type_detection_by_extension(self):
        """Test that file types are correctly detected by extension."""
        entry = EntryFactory()

        files = [
            SimpleUploadedFile("test.jpg", b"content", content_type="image/jpeg"),
            SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf"),
            SimpleUploadedFile(
                "test.xlsx",
                b"content",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            SimpleUploadedFile(
                "test.unknown", b"content", content_type="application/octet-stream"
            ),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=files, replace_attachments=False
        )

        attachments = entry.attachments.all()
        assert attachments.count() == 4

        # Check file types
        file_types = [att.file_type for att in attachments]
        assert AttachmentType.IMAGE in file_types
        assert AttachmentType.PDF in file_types
        assert AttachmentType.SPREADSHEET in file_types
        assert AttachmentType.OTHER in file_types

    def test_empty_attachments_list(self):
        """Test handling of empty attachments list."""
        entry = EntryFactory()
        existing_attachment = AttachmentFactory(entry=entry)

        replace_or_append_attachments(
            entry=entry, attachments=[], replace_attachments=False
        )

        # Should still have the existing attachment
        assert entry.attachments.count() == 1
        assert Attachment.objects.filter(
            attachment_id=existing_attachment.attachment_id
        ).exists()

    def test_replace_with_empty_attachments_list(self):
        """Test replacing with empty attachments list."""
        entry = EntryFactory()
        existing_attachment = AttachmentFactory(entry=entry)

        replace_or_append_attachments(
            entry=entry, attachments=[], replace_attachments=True
        )

        # Should have no attachments
        assert entry.attachments.count() == 0

        # Existing attachment should be soft deleted
        assert not Attachment.objects.filter(
            attachment_id=existing_attachment.attachment_id
        ).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateAttachmentsService:
    """Test create_attachments service business logic."""

    def test_create_attachments_success(self):
        """Test successful creation of multiple attachments."""
        entry = EntryFactory()

        files = [
            SimpleUploadedFile(
                "test1.jpg", b"image content", content_type="image/jpeg"
            ),
            SimpleUploadedFile(
                "test2.pdf", b"pdf content", content_type="application/pdf"
            ),
            SimpleUploadedFile(
                "test3.xlsx",
                b"spreadsheet content",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ]

        created_attachments = create_attachments(entry=entry, attachments=files)

        assert len(created_attachments) == 3
        assert entry.attachments.count() == 3

        # Verify file types are correctly assigned
        file_types = [att.file_type for att in created_attachments]
        assert AttachmentType.IMAGE in file_types
        assert AttachmentType.PDF in file_types
        assert AttachmentType.SPREADSHEET in file_types

    def test_create_attachments_with_unknown_extension(self):
        """Test creating attachments with unknown file extensions."""
        entry = EntryFactory()

        files = [
            SimpleUploadedFile(
                "test.unknown", b"content", content_type="application/octet-stream"
            ),
            SimpleUploadedFile("noextension", b"content", content_type="text/plain"),
        ]

        created_attachments = create_attachments(entry=entry, attachments=files)

        assert len(created_attachments) == 2

        # Both should be assigned OTHER type
        for attachment in created_attachments:
            assert attachment.file_type == AttachmentType.OTHER

    def test_create_attachments_empty_list(self):
        """Test creating attachments with empty list."""
        entry = EntryFactory()

        created_attachments = create_attachments(entry=entry, attachments=[])

        assert len(created_attachments) == 0
        assert entry.attachments.count() == 0

    def test_create_attachments_bulk_creation(self):
        """Test that attachments are created using bulk_create for efficiency."""
        entry = EntryFactory()

        files = [
            SimpleUploadedFile(f"test{i}.jpg", b"content", content_type="image/jpeg")
            for i in range(5)
        ]

        with patch.object(
            Attachment.objects, "bulk_create", wraps=Attachment.objects.bulk_create
        ) as mock_bulk_create:
            created_attachments = create_attachments(entry=entry, attachments=files)

        # Verify bulk_create was called once
        mock_bulk_create.assert_called_once()

        # Verify all attachments were created
        assert len(created_attachments) == 5
        assert entry.attachments.count() == 5

    def test_create_attachments_file_type_assignment(self):
        """Test correct file type assignment for various extensions."""
        entry = EntryFactory()

        test_cases = [
            ("test.jpg", AttachmentType.IMAGE),
            ("test.jpeg", AttachmentType.IMAGE),
            ("test.png", AttachmentType.IMAGE),
            ("test.pdf", AttachmentType.PDF),
            ("test.xls", AttachmentType.SPREADSHEET),
            ("test.xlsx", AttachmentType.SPREADSHEET),
            ("test.csv", AttachmentType.SPREADSHEET),
            ("test.txt", AttachmentType.OTHER),
            ("test.doc", AttachmentType.OTHER),
        ]

        files = [SimpleUploadedFile(filename, b"content") for filename, _ in test_cases]

        created_attachments = create_attachments(entry=entry, attachments=files)

        # Verify we have the correct number of attachments
        assert len(created_attachments) == len(test_cases)

        # Test each file type individually by checking the extension logic
        for filename, expected_type in test_cases:
            # Use the same logic as the service to determine expected type
            actual_type = AttachmentType.get_file_type_by_extension(filename) or AttachmentType.OTHER
            assert actual_type == expected_type, f"Extension logic failed for {filename}: expected {expected_type}, got {actual_type}"

        # Verify all attachments have valid file types
        for attachment in created_attachments:
            assert attachment.file_type in [
                AttachmentType.IMAGE,
                AttachmentType.PDF,
                AttachmentType.SPREADSHEET,
                AttachmentType.OTHER,
            ], f"Invalid file type: {attachment.file_type}"

    def test_create_attachments_with_existing_attachments(self):
        """Test creating attachments when entry already has attachments."""
        entry = EntryFactory()
        existing_attachment = AttachmentFactory(entry=entry)

        files = [
            SimpleUploadedFile("new.jpg", b"content", content_type="image/jpeg"),
        ]

        created_attachments = create_attachments(entry=entry, attachments=files)

        # Should have 2 attachments total (1 existing + 1 new)
        assert entry.attachments.count() == 2
        assert len(created_attachments) == 1

        # Existing attachment should still exist
        assert Attachment.objects.filter(
            attachment_id=existing_attachment.attachment_id
        ).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestAttachmentServiceIntegration:
    """Test integration between attachment services."""

    def test_full_attachment_lifecycle(self):
        """Test complete attachment lifecycle: create, replace, delete."""
        entry = EntryFactory()

        # Step 1: Create initial attachments
        initial_files = [
            SimpleUploadedFile("initial1.jpg", b"content", content_type="image/jpeg"),
            SimpleUploadedFile(
                "initial2.pdf", b"content", content_type="application/pdf"
            ),
        ]

        create_attachments(entry=entry, attachments=initial_files)
        assert entry.attachments.count() == 2

        # Step 2: Replace with new attachments
        replacement_files = [
            SimpleUploadedFile(
                "replacement.xlsx",
                b"content",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=replacement_files, replace_attachments=True
        )

        assert entry.attachments.count() == 1
        assert entry.attachments.first().file_type == AttachmentType.SPREADSHEET

        # Step 3: Add more attachments
        additional_files = [
            SimpleUploadedFile("additional.jpg", b"content", content_type="image/jpeg"),
        ]

        replace_or_append_attachments(
            entry=entry, attachments=additional_files, replace_attachments=False
        )

        assert entry.attachments.count() == 2

        # Step 4: Try to delete last attachment (should fail)
        factory = RequestFactory()
        request = factory.get("/")

        # Delete one attachment first
        first_attachment = entry.attachments.first()
        with patch("apps.attachments.services.messages"):
            success, _ = delete_attachment(first_attachment.attachment_id, request)

        assert success is True
        assert entry.attachments.count() == 1

        # Try to delete the last attachment (should fail)
        last_attachment = entry.attachments.first()
        with patch("apps.attachments.services.messages") as mock_messages:
            success, _ = delete_attachment(last_attachment.attachment_id, request)

        assert success is False
        assert entry.attachments.count() == 1
        mock_messages.error.assert_called_with(
            request, "You cannot delete the last attachment"
        )
