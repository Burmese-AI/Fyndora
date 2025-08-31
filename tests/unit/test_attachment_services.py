"""
Unit tests for Attachment services.

Tests attachment service functions including delete, replace/append, and create operations.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock

from apps.attachments.constants import AttachmentType
from apps.attachments.models import Attachment
from apps.attachments.services import (
    delete_attachment,
    replace_or_append_attachments,
    create_attachments,
)
from tests.factories import (
    AttachmentFactory,
    EntryFactory,
    CustomUserFactory,
)


@pytest.mark.unit
class TestDeleteAttachment(TestCase):
    """Test delete_attachment service function."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()
        self.attachment1 = AttachmentFactory(entry=self.entry)
        self.attachment2 = AttachmentFactory(entry=self.entry)
        self.request = self.factory.get("/")
        self.request.user = self.user

    @patch("apps.attachments.services.messages")
    def test_delete_attachment_success(self, mock_messages):
        """Test successful attachment deletion."""
        attachment_id = self.attachment1.attachment_id

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            success, attachments = delete_attachment(attachment_id, self.request)

        assert success is True
        assert attachments is not None
        assert attachments.count() == 1
        assert self.attachment2 in attachments
        assert self.attachment1 not in attachments

        # Check that attachment was soft deleted
        assert not Attachment.objects.filter(attachment_id=attachment_id).exists()
        assert Attachment.all_objects.filter(attachment_id=attachment_id).exists()

        # Verify audit logging was called
        mock_logger.assert_called_once()

        # Verify success message was called
        mock_messages.success.assert_called_once()

    @patch("apps.attachments.services.messages")
    def test_delete_attachment_not_found(self, mock_messages):
        """Test deletion of non-existent attachment."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        success, attachments = delete_attachment(fake_id, self.request)

        assert success is False
        assert attachments is None

        # Verify error message was called
        mock_messages.error.assert_called_once_with(
            self.request, "Attachment not found."
        )

    @patch("apps.attachments.services.messages")
    def test_delete_last_attachment_fails(self, mock_messages):
        """Test that deleting the last attachment fails."""
        # Delete one attachment first
        self.attachment2.delete()

        attachment_id = self.attachment1.attachment_id

        success, attachments = delete_attachment(attachment_id, self.request)

        assert success is False
        assert attachments is None

        # Check that attachment still exists
        assert Attachment.objects.filter(attachment_id=attachment_id).exists()

        # Verify error message was called
        mock_messages.error.assert_called_once_with(
            self.request, "You cannot delete the last attachment"
        )

    @patch("apps.attachments.services.messages")
    def test_delete_attachment_with_exception(self, mock_messages):
        """Test attachment deletion when an exception occurs."""
        attachment_id = self.attachment1.attachment_id

        # Mock the attachment.delete() method to raise an exception
        with patch.object(
            Attachment, "delete", side_effect=Exception("Database error")
        ):
            success, attachments = delete_attachment(attachment_id, self.request)

        assert success is False
        assert attachments is None

        # Verify error message was called
        mock_messages.error.assert_called_once_with(
            self.request, "Failed to delete attachment."
        )

    @patch("apps.attachments.services.messages")
    def test_delete_attachment_audit_logging(self, mock_messages):
        """Test that audit logging is performed on successful deletion."""
        attachment_id = self.attachment1.attachment_id

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            success, _ = delete_attachment(attachment_id, self.request)

        assert success is True
        mock_logger.assert_called_once()

        # Verify the call arguments
        call_args = mock_logger.call_args
        assert call_args[1]["operation"] == "delete"
        assert call_args[1]["file_obj"] == self.attachment1

    @patch("apps.attachments.services.messages")
    def test_delete_attachment_with_unauthenticated_user(self, mock_messages):
        """Test deletion with unauthenticated user."""
        attachment_id = self.attachment1.attachment_id
        request = self.factory.get("/")
        request.user = MagicMock()
        request.user.is_authenticated = False

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            success, attachments = delete_attachment(attachment_id, request)

        assert success is True
        # Audit logging should not be called for unauthenticated users
        mock_logger.assert_not_called()


@pytest.mark.unit
class TestReplaceOrAppendAttachments(TestCase):
    """Test replace_or_append_attachments service function."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()
        self.existing_attachment = AttachmentFactory(entry=self.entry)
        self.request = self.factory.get("/")
        self.request.user = self.user

    def test_replace_attachments_success(self):
        """Test successful replacement of attachments."""
        new_files = [
            SimpleUploadedFile("new1.pdf", b"content1"),
            SimpleUploadedFile("new2.jpg", b"content2"),
        ]

        with (
            patch(
                "apps.attachments.services.BusinessAuditLogger.log_bulk_operation"
            ) as mock_bulk_logger,
            patch(
                "apps.attachments.services.BusinessAuditLogger.log_file_operation"
            ) as mock_file_logger,
        ):
            created_attachments = replace_or_append_attachments(
                entry=self.entry,
                attachments=new_files,
                replace_attachments=True,
                user=self.user,
                request=self.request,
            )

        # Check that new attachments were created
        assert len(created_attachments) == 2
        assert created_attachments[0].entry == self.entry
        assert created_attachments[1].entry == self.entry

        # Check that existing attachment was soft deleted
        assert not Attachment.objects.filter(
            attachment_id=self.existing_attachment.attachment_id
        ).exists()
        assert Attachment.all_objects.filter(
            attachment_id=self.existing_attachment.attachment_id
        ).exists()

        # Check file types were detected correctly
        assert created_attachments[0].file_type == AttachmentType.PDF
        assert created_attachments[1].file_type == AttachmentType.IMAGE

        # Verify audit logging was called
        mock_bulk_logger.assert_called_once()
        assert mock_file_logger.call_count == 2

    def test_append_attachments_success(self):
        """Test successful appending of attachments."""
        new_files = [
            SimpleUploadedFile("new1.pdf", b"content1"),
        ]

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            created_attachments = replace_or_append_attachments(
                entry=self.entry,
                attachments=new_files,
                replace_attachments=False,
                user=self.user,
                request=self.request,
            )

        # Check that new attachment was created
        assert len(created_attachments) == 1
        assert created_attachments[0].entry == self.entry

        # Check that existing attachment remains
        assert Attachment.objects.filter(
            attachment_id=self.existing_attachment.attachment_id
        ).exists()

        # Check file type was detected correctly
        assert created_attachments[0].file_type == AttachmentType.PDF

        # Verify audit logging was called
        mock_logger.assert_called_once()

    def test_replace_attachments_with_unknown_file_type(self):
        """Test replacement with files of unknown type."""
        new_files = [
            SimpleUploadedFile("unknown.xyz", b"content"),
        ]

        created_attachments = replace_or_append_attachments(
            entry=self.entry,
            attachments=new_files,
            replace_attachments=True,
            user=self.user,
            request=self.request,
        )

        # Check that attachment was created with OTHER type
        assert len(created_attachments) == 1
        assert created_attachments[0].file_type == AttachmentType.OTHER

    def test_replace_attachments_without_user(self):
        """Test replacement without user (no audit logging)."""
        new_files = [
            SimpleUploadedFile("new1.pdf", b"content1"),
        ]

        with (
            patch(
                "apps.attachments.services.BusinessAuditLogger.log_bulk_operation"
            ) as mock_bulk_logger,
            patch(
                "apps.attachments.services.BusinessAuditLogger.log_file_operation"
            ) as mock_file_logger,
        ):
            created_attachments = replace_or_append_attachments(
                entry=self.entry,
                attachments=new_files,
                replace_attachments=True,
                user=None,
                request=self.request,
            )

        assert len(created_attachments) == 1

        # Audit logging should not be called when no user
        mock_bulk_logger.assert_not_called()
        mock_file_logger.assert_not_called()

    def test_replace_attachments_empty_list(self):
        """Test replacement with empty attachments list."""
        created_attachments = replace_or_append_attachments(
            entry=self.entry,
            attachments=[],
            replace_attachments=True,
            user=self.user,
            request=self.request,
        )

        assert len(created_attachments) == 0

        # Existing attachment should be soft deleted
        assert not Attachment.objects.filter(entry=self.entry).exists()

    def test_replace_attachments_audit_logging_details(self):
        """Test that audit logging includes correct details."""
        new_files = [
            SimpleUploadedFile("new1.pdf", b"content1"),
        ]

        with (
            patch(
                "apps.attachments.services.BusinessAuditLogger.log_bulk_operation"
            ) as mock_bulk_logger,
            patch(
                "apps.attachments.services.BusinessAuditLogger.log_file_operation"
            ) as mock_file_logger,
        ):
            replace_or_append_attachments(
                entry=self.entry,
                attachments=new_files,
                replace_attachments=True,
                user=self.user,
                request=self.request,
            )

        # Check bulk operation logging
        bulk_call_args = mock_bulk_logger.call_args[1]
        assert bulk_call_args["operation_type"] == "attachment_replacement_deletion"
        assert bulk_call_args["replaced_count"] == 1

        # Check file operation logging
        file_call_args = mock_file_logger.call_args[1]
        assert file_call_args["operation"] == "upload"
        assert file_call_args["operation_context"] == "replace_or_append"
        assert file_call_args["is_replacement"] is True


@pytest.mark.unit
class TestCreateAttachments(TestCase):
    """Test create_attachments service function."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user

    def test_create_attachments_success(self):
        """Test successful bulk creation of attachments."""
        files = [
            SimpleUploadedFile("file1.pdf", b"content1"),
            SimpleUploadedFile("file2.jpg", b"content2"),
            SimpleUploadedFile("file3.xlsx", b"content3"),
        ]

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            created_attachments = create_attachments(
                entry=self.entry,
                attachments=files,
                user=self.user,
                request=self.request,
            )

        # Check that all attachments were created
        assert len(created_attachments) == 3

        # Check that they're linked to the entry
        for attachment in created_attachments:
            assert attachment.entry == self.entry

        # Check file types were detected correctly
        assert created_attachments[0].file_type == AttachmentType.PDF
        assert created_attachments[1].file_type == AttachmentType.IMAGE
        assert created_attachments[2].file_type == AttachmentType.SPREADSHEET

        # Verify audit logging was called for each attachment
        assert mock_logger.call_count == 3

    def test_create_attachments_with_unknown_file_type(self):
        """Test creation with files of unknown type."""
        files = [
            SimpleUploadedFile("unknown.xyz", b"content"),
        ]

        created_attachments = create_attachments(
            entry=self.entry,
            attachments=files,
            user=self.user,
            request=self.request,
        )

        # Check that attachment was created with OTHER type
        assert len(created_attachments) == 1
        assert created_attachments[0].file_type == AttachmentType.OTHER

    def test_create_attachments_without_user(self):
        """Test creation without user (no audit logging)."""
        files = [
            SimpleUploadedFile("file1.pdf", b"content1"),
        ]

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            created_attachments = create_attachments(
                entry=self.entry,
                attachments=files,
                user=None,
                request=self.request,
            )

        assert len(created_attachments) == 1

        # Audit logging should not be called when no user
        mock_logger.assert_not_called()

    def test_create_attachments_empty_list(self):
        """Test creation with empty attachments list."""
        created_attachments = create_attachments(
            entry=self.entry,
            attachments=[],
            user=self.user,
            request=self.request,
        )

        assert len(created_attachments) == 0

    def test_create_attachments_audit_logging_details(self):
        """Test that audit logging includes correct details."""
        files = [
            SimpleUploadedFile("file1.pdf", b"content1"),
        ]

        with patch(
            "apps.attachments.services.BusinessAuditLogger.log_file_operation"
        ) as mock_logger:
            create_attachments(
                entry=self.entry,
                attachments=files,
                user=self.user,
                request=self.request,
            )

        # Check logging call arguments
        call_args = mock_logger.call_args[1]
        assert call_args["operation"] == "upload"
        assert call_args["operation_context"] == "bulk_create"
        assert call_args["bulk_operation"] is True
        assert call_args["total_attachments"] == 1
        assert "attachment_id" in call_args

    def test_create_attachments_bulk_create_behavior(self):
        """Test that attachments are actually created in the database."""
        files = [
            SimpleUploadedFile("file1.pdf", b"content1"),
            SimpleUploadedFile("file2.jpg", b"content2"),
        ]

        created_attachments = create_attachments(
            entry=self.entry,
            attachments=files,
            user=self.user,
            request=self.request,
        )

        # Check that attachments exist in database
        for attachment in created_attachments:
            assert Attachment.objects.filter(
                attachment_id=attachment.attachment_id
            ).exists()

    def test_create_attachments_mixed_file_types(self):
        """Test creation with various file types."""
        files = [
            SimpleUploadedFile("document.pdf", b"content"),
            SimpleUploadedFile("image.png", b"content"),
            SimpleUploadedFile("data.csv", b"content"),
            SimpleUploadedFile("unknown.xyz", b"content"),
        ]

        created_attachments = create_attachments(
            entry=self.entry,
            attachments=files,
            user=self.user,
            request=self.request,
        )

        # Check file types
        file_types = [att.file_type for att in created_attachments]
        assert AttachmentType.PDF in file_types
        assert AttachmentType.IMAGE in file_types
        assert AttachmentType.SPREADSHEET in file_types
        assert AttachmentType.OTHER in file_types


@pytest.mark.unit
class TestAttachmentServicesIntegration(TestCase):
    """Test integration between different attachment services."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.entry = EntryFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user

    def test_replace_then_create_attachments_workflow(self):
        """Test workflow: replace attachments then create new ones."""
        # Create initial attachment
        initial_files = [SimpleUploadedFile("initial.pdf", b"content")]
        create_attachments(
            entry=self.entry,
            attachments=initial_files,
            user=self.user,
            request=self.request,
        )

        # Replace with new attachments
        new_files = [SimpleUploadedFile("new.jpg", b"content")]
        replaced_attachments = replace_or_append_attachments(
            entry=self.entry,
            attachments=new_files,
            replace_attachments=True,
            user=self.user,
            request=self.request,
        )

        # Check that initial attachment was soft deleted
        assert not Attachment.objects.filter(
            entry=self.entry, file_type=AttachmentType.PDF
        ).exists()

        # Check that new attachment was created
        assert len(replaced_attachments) == 1
        assert replaced_attachments[0].file_type == AttachmentType.IMAGE

    @patch("apps.attachments.services.messages")
    def test_attachment_count_validation(self, mock_messages):
        """Test that attachment count validation works correctly."""
        # Create single attachment
        files = [SimpleUploadedFile("single.pdf", b"content")]
        created_attachments = create_attachments(
            entry=self.entry,
            attachments=files,
            user=self.user,
            request=self.request,
        )

        attachment = created_attachments[0]

        # Try to delete the only attachment (should fail)
        success, remaining = delete_attachment(attachment.attachment_id, self.request)

        assert success is False
        assert remaining is None

        # Attachment should still exist
        assert Attachment.objects.filter(
            attachment_id=attachment.attachment_id
        ).exists()

        # Verify error message was called
        mock_messages.error.assert_called_once_with(
            self.request, "You cannot delete the last attachment"
        )
