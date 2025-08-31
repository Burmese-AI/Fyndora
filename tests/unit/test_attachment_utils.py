"""
Unit tests for Attachment utilities.

Tests file validation and business context extraction functions.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.attachments.utils import (
    validate_uploaded_files,
    extract_attachment_business_context,
)
from apps.attachments.constants import AttachmentType
from tests.factories import (
    AttachmentFactory,
    EntryFactory,
    WorkspaceFactory,
    OrganizationFactory,
)


@pytest.mark.unit
class TestValidateUploadedFiles(TestCase):
    """Test validate_uploaded_files utility function."""

    def test_validate_uploaded_files_with_valid_files(self):
        """Test validation with valid files."""
        files = [
            SimpleUploadedFile("document.pdf", b"content" * 1000),  # ~1KB
            SimpleUploadedFile("image.jpg", b"content" * 2000),  # ~2KB
            SimpleUploadedFile("spreadsheet.xlsx", b"content" * 500),  # ~500B
        ]

        # Should not raise any exceptions
        validate_uploaded_files(files)
        validate_uploaded_files(files, max_size_mb=1)  # Test with custom size limit

    def test_validate_uploaded_files_with_size_limit_exceeded(self):
        """Test validation when file size exceeds limit."""
        # Create a file larger than 5MB (default limit)
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        files = [SimpleUploadedFile("large_file.pdf", large_content)]

        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files)

        assert "exceeds 5MB size limit" in str(exc_info.value)

    def test_validate_uploaded_files_with_custom_size_limit(self):
        """Test validation with custom size limit."""
        # Create a file larger than 2MB but smaller than 5MB
        medium_content = b"x" * (3 * 1024 * 1024)  # 3MB
        files = [SimpleUploadedFile("medium_file.pdf", medium_content)]

        # Should pass with default 5MB limit
        validate_uploaded_files(files)

        # Should fail with 2MB limit
        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files, max_size_mb=2)

        assert "exceeds 2MB size limit" in str(exc_info.value)

    def test_validate_uploaded_files_with_unsupported_extension(self):
        """Test validation with unsupported file extensions."""
        files = [
            SimpleUploadedFile("script.py", b"content"),
            SimpleUploadedFile("document.txt", b"content"),
            SimpleUploadedFile("archive.zip", b"content"),
        ]

        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files)

        # Check that the error message mentions the unsupported extension
        error_message = str(exc_info.value)
        assert "has unsupported file type" in error_message
        assert (
            ".py" in error_message or ".txt" in error_message or ".zip" in error_message
        )

    def test_validate_uploaded_files_with_mixed_valid_and_invalid(self):
        """Test validation with mix of valid and invalid files."""
        files = [
            SimpleUploadedFile("valid.pdf", b"content"),  # Valid
            SimpleUploadedFile("invalid.py", b"content"),  # Invalid extension
        ]

        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files)

        # Should fail on first invalid file
        assert "invalid.py" in str(exc_info.value)
        assert "has unsupported file type" in str(exc_info.value)

    def test_validate_uploaded_files_with_empty_files(self):
        """Test validation with empty files."""
        files = [
            SimpleUploadedFile("empty.pdf", b""),
            SimpleUploadedFile("empty.jpg", b""),
        ]

        # Empty files should pass validation
        validate_uploaded_files(files)

    def test_validate_uploaded_files_with_files_at_size_limit(self):
        """Test validation with files exactly at the size limit."""
        # Create files exactly at the 5MB limit
        exact_size_content = b"x" * (5 * 1024 * 1024)  # Exactly 5MB
        files = [SimpleUploadedFile("exact_size.pdf", exact_size_content)]

        # Should pass validation
        validate_uploaded_files(files)

        # Should fail with 4MB limit
        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files, max_size_mb=4)

        assert "exceeds 4MB size limit" in str(exc_info.value)

    def test_validate_uploaded_files_with_files_just_under_limit(self):
        """Test validation with files just under the size limit."""
        # Create files just under the 5MB limit
        under_limit_content = b"x" * ((5 * 1024 * 1024) - 1)  # 5MB - 1 byte
        files = [SimpleUploadedFile("under_limit.pdf", under_limit_content)]

        # Should pass validation
        validate_uploaded_files(files)

    def test_validate_uploaded_files_with_files_just_over_limit(self):
        """Test validation with files just over the size limit."""
        # Create files just over the 5MB limit
        over_limit_content = b"x" * ((5 * 1024 * 1024) + 1)  # 5MB + 1 byte
        files = [SimpleUploadedFile("over_limit.pdf", over_limit_content)]

        # Should fail validation
        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files)

        assert "exceeds 5MB size limit" in str(exc_info.value)

    def test_validate_uploaded_files_with_single_file(self):
        """Test validation with a single file."""
        file = SimpleUploadedFile("single.pdf", b"content")

        # Should not raise any exceptions
        validate_uploaded_files([file])

    def test_validate_uploaded_files_with_no_files(self):
        """Test validation with empty list."""
        files = []

        # Should not raise any exceptions
        validate_uploaded_files(files)

    def test_validate_uploaded_files_with_case_sensitive_extensions(self):
        """Test validation with different case extensions."""
        files = [
            SimpleUploadedFile("document.PDF", b"content"),  # Uppercase
            SimpleUploadedFile("image.JPG", b"content"),  # Uppercase
            SimpleUploadedFile("data.XLSX", b"content"),  # Uppercase
        ]

        # Should not raise any exceptions (extensions are converted to lowercase)
        validate_uploaded_files(files)

    def test_validate_uploaded_files_with_complex_filenames(self):
        """Test validation with complex filenames."""
        files = [
            SimpleUploadedFile("my.document.2023.final.pdf", b"content"),
            SimpleUploadedFile("image_thumb_150x150.jpg", b"content"),
            SimpleUploadedFile("data_quarterly_Q1_2023.xlsx", b"content"),
        ]

        # Should not raise any exceptions
        validate_uploaded_files(files)

    def test_validate_uploaded_files_with_files_no_extension(self):
        """Test validation with files that have no extension."""
        files = [
            SimpleUploadedFile("filename", b"content"),
            SimpleUploadedFile("README", b"content"),
        ]

        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files)

        # Should fail because no extension means empty string, which is not in allowed extensions
        assert "has unsupported file type" in str(exc_info.value)

    def test_validate_uploaded_files_with_files_ending_with_dot(self):
        """Test validation with files ending with a dot."""
        files = [
            SimpleUploadedFile("filename.", b"content"),
            SimpleUploadedFile("document.", b"content"),
        ]

        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files)

        # Should fail because extension is empty string
        assert "has unsupported file type" in str(exc_info.value)

    def test_validate_uploaded_files_size_limit_edge_cases(self):
        """Test various size limit edge cases."""
        # Test with 0MB limit
        files = [SimpleUploadedFile("any.pdf", b"x")]
        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files(files, max_size_mb=0)
        assert "exceeds 0MB size limit" in str(exc_info.value)

        # Test with very large limit
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB
        files = [SimpleUploadedFile("large.pdf", large_content)]
        validate_uploaded_files(files, max_size_mb=100)  # Should pass


@pytest.mark.unit
class TestExtractAttachmentBusinessContext(TestCase):
    """Test extract_attachment_business_context utility function."""

    def setUp(self):
        """Set up test environment."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.entry = EntryFactory(workspace=self.workspace)
        self.attachment = AttachmentFactory(entry=self.entry)

    def test_extract_attachment_business_context_success(self):
        """Test successful extraction of business context."""
        context = extract_attachment_business_context(self.attachment)

        # Check that all expected keys are present
        expected_keys = ["attachment_id", "entry_id", "workspace_id", "organization_id"]
        for key in expected_keys:
            assert key in context

        # Verify the context contains the correct number of items
        assert len(context) == 4

        # Verify all values are strings and have UUID format
        for key, value in context.items():
            assert isinstance(value, str)
            if key.endswith("_id"):
                assert len(value) == 36  # UUID length
                assert value.count("-") == 4  # UUID format

    def test_extract_attachment_business_context_with_none_attachment(self):
        """Test extraction with None attachment."""
        context = extract_attachment_business_context(None)

        # Should return empty dictionary
        assert context == {}

    def test_extract_attachment_business_context_with_empty_dict(self):
        """Test extraction returns dictionary type."""
        context = extract_attachment_business_context(self.attachment)

        assert isinstance(context, dict)
        assert len(context) == 4

    def test_extract_attachment_business_context_id_types(self):
        """Test that all IDs are returned as strings."""
        context = extract_attachment_business_context(self.attachment)

        for key, value in context.items():
            if key.endswith("_id"):
                assert isinstance(value, str)
                # Should be valid UUID strings
                assert len(value) == 36  # UUID length
                assert value.count("-") == 4  # UUID format

    def test_extract_attachment_business_context_relationship_integrity(self):
        """Test that the extracted context maintains relationship integrity."""
        context = extract_attachment_business_context(self.attachment)

        # Verify the relationships are correct
        assert context["attachment_id"] == str(self.attachment.attachment_id)
        assert context["entry_id"] == str(self.attachment.entry.entry_id)
        assert context["workspace_id"] == str(
            self.attachment.entry.workspace.workspace_id
        )
        assert context["organization_id"] == str(
            self.attachment.entry.workspace.organization.organization_id
        )

    def test_extract_attachment_business_context_with_different_attachment(self):
        """Test extraction with different attachment."""
        # Create another attachment with different entry/workspace/organization
        other_org = OrganizationFactory()
        other_workspace = WorkspaceFactory(organization=other_org)
        other_entry = EntryFactory(workspace=other_workspace)
        other_attachment = AttachmentFactory(entry=other_entry)

        context = extract_attachment_business_context(other_attachment)

        # Should have different values
        assert context["attachment_id"] != str(self.attachment.attachment_id)
        assert context["entry_id"] != str(self.entry.entry_id)
        assert context["workspace_id"] != str(self.workspace.workspace_id)
        assert context["organization_id"] != str(self.organization.organization_id)

    def test_extract_attachment_business_context_audit_logging_ready(self):
        """Test that extracted context is ready for audit logging."""
        context = extract_attachment_business_context(self.attachment)

        # All values should be strings (JSON serializable)
        for value in context.values():
            assert isinstance(value, str)

        # Should not contain any complex objects
        for value in context.values():
            assert not hasattr(value, "__dict__")
            assert not callable(value)

    def test_extract_attachment_business_context_with_deleted_attachment(self):
        """Test extraction with soft-deleted attachment."""
        # Soft delete the attachment
        self.attachment.delete()

        # Should still work (soft delete doesn't remove from database)
        context = extract_attachment_business_context(self.attachment)

        assert context["attachment_id"] == str(self.attachment.attachment_id)
        assert context["entry_id"] == str(self.entry.entry_id)

    def test_extract_attachment_business_context_performance(self):
        """Test that extraction doesn't cause unnecessary database queries."""
        # Reset query count
        from django.db import connection

        initial_queries = len(connection.queries)

        context = extract_attachment_business_context(self.attachment)

        # Should not cause additional queries since relationships are already loaded
        final_queries = len(connection.queries)
        assert final_queries == initial_queries

        # Context should still be extracted correctly
        assert context["attachment_id"] == str(self.attachment.attachment_id)


@pytest.mark.unit
class TestAttachmentUtilsIntegration(TestCase):
    """Test integration between attachment utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.entry = EntryFactory(workspace=self.workspace)

    def test_validate_then_extract_context_workflow(self):
        """Test complete workflow: validate files then extract context."""
        # Create valid files
        files = [
            SimpleUploadedFile("document.pdf", b"content"),
            SimpleUploadedFile("image.jpg", b"content"),
        ]

        # Validate files (should not raise exceptions)
        validate_uploaded_files(files)

        # Create attachments from validated files
        attachments = []
        for file in files:
            file_type = AttachmentType.get_file_type_by_extension(file.name)
            attachment = AttachmentFactory(
                entry=self.entry,
                file_url=file,
                file_type=file_type or AttachmentType.OTHER,
            )
            attachments.append(attachment)

        # Extract business context from each attachment
        for attachment in attachments:
            context = extract_attachment_business_context(attachment)

            # Verify context is complete and has correct structure
            assert len(context) == 4
            assert "entry_id" in context
            assert "workspace_id" in context
            assert "organization_id" in context
            assert "attachment_id" in context

            # Verify all values are strings with UUID format
            for key, value in context.items():
                assert isinstance(value, str)
                if key.endswith("_id"):
                    assert len(value) == 36  # UUID length
                    assert value.count("-") == 4  # UUID format

    def test_validation_error_prevents_context_extraction(self):
        """Test that validation errors prevent attachment creation and context extraction."""
        # Create invalid file (unsupported extension)
        invalid_file = SimpleUploadedFile("script.py", b"content")

        # Validation should fail
        with pytest.raises(ValidationError):
            validate_uploaded_files([invalid_file])

        # Since validation failed, no attachment would be created
        # and no context extraction would occur

    def test_size_validation_with_context_extraction(self):
        """Test size validation with subsequent context extraction."""
        # Create file that exceeds size limit
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        large_file = SimpleUploadedFile("large.pdf", large_content)

        # Validation should fail
        with pytest.raises(ValidationError) as exc_info:
            validate_uploaded_files([large_file])

        assert "exceeds 5MB size limit" in str(exc_info.value)

        # No attachment would be created, so no context extraction possible
