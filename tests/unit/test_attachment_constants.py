"""
Unit tests for Attachment constants.

Tests AttachmentType choices, extension mapping, and utility methods.
"""

import pytest
from django.test import TestCase

from apps.attachments.constants import AttachmentType


@pytest.mark.unit
class TestAttachmentType(TestCase):
    """Test AttachmentType constants and choices."""

    def test_attachment_type_choices(self):
        """Test that AttachmentType has correct choices."""
        expected_choices = [
            ("image", "Image"),
            ("pdf", "PDF"),
            ("spreadsheet", "Spreadsheet"),
            ("other", "Other"),
        ]

        assert AttachmentType.choices == expected_choices

    def test_attachment_type_values(self):
        """Test that AttachmentType has correct values."""
        assert AttachmentType.IMAGE == "image"
        assert AttachmentType.PDF == "pdf"
        assert AttachmentType.SPREADSHEET == "spreadsheet"
        assert AttachmentType.OTHER == "other"

    def test_attachment_type_labels(self):
        """Test that AttachmentType has correct labels."""
        assert AttachmentType.IMAGE.label == "Image"
        assert AttachmentType.PDF.label == "PDF"
        assert AttachmentType.SPREADSHEET.label == "Spreadsheet"
        assert AttachmentType.OTHER.label == "Other"

    def test_attachment_type_names(self):
        """Test that AttachmentType has correct names."""
        assert AttachmentType.IMAGE.name == "IMAGE"
        assert AttachmentType.PDF.name == "PDF"
        assert AttachmentType.SPREADSHEET.name == "SPREADSHEET"
        assert AttachmentType.OTHER.name == "OTHER"


@pytest.mark.unit
class TestAttachmentTypeExtensionMap(TestCase):
    """Test AttachmentType extension mapping functionality."""

    def test_get_extension_map(self):
        """Test that get_extension_map returns correct mapping."""
        expected_map = {
            AttachmentType.IMAGE: [".jpg", ".jpeg", ".png"],
            AttachmentType.PDF: [".pdf"],
            AttachmentType.SPREADSHEET: [".xls", ".xlsx", ".csv"],
        }

        extension_map = AttachmentType.get_extension_map()
        assert extension_map == expected_map

    def test_extension_map_structure(self):
        """Test that extension map has correct structure."""
        extension_map = AttachmentType.get_extension_map()

        # Check that all expected file types are present
        assert AttachmentType.IMAGE in extension_map
        assert AttachmentType.PDF in extension_map
        assert AttachmentType.SPREADSHEET in extension_map

        # Check that OTHER is not in extension map (as expected)
        assert AttachmentType.OTHER not in extension_map

    def test_extension_map_values_are_lists(self):
        """Test that all extension map values are lists."""
        extension_map = AttachmentType.get_extension_map()

        for file_type, extensions in extension_map.items():
            assert isinstance(extensions, list)
            assert len(extensions) > 0

    def test_extension_map_extensions_are_strings(self):
        """Test that all extensions in the map are strings."""
        extension_map = AttachmentType.get_extension_map()

        for file_type, extensions in extension_map.items():
            for extension in extensions:
                assert isinstance(extension, str)
                assert extension.startswith(".")


@pytest.mark.unit
class TestAttachmentTypeFileTypeByExtension(TestCase):
    """Test get_file_type_by_extension method."""

    def test_get_file_type_by_extension_image_formats(self):
        """Test that image extensions return correct file type."""
        assert (
            AttachmentType.get_file_type_by_extension("photo.jpg")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension("photo.jpeg")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension("photo.png")
            == AttachmentType.IMAGE
        )

    def test_get_file_type_by_extension_pdf_format(self):
        """Test that PDF extension returns correct file type."""
        assert (
            AttachmentType.get_file_type_by_extension("document.pdf")
            == AttachmentType.PDF
        )

    def test_get_file_type_by_extension_spreadsheet_formats(self):
        """Test that spreadsheet extensions return correct file type."""
        assert (
            AttachmentType.get_file_type_by_extension("data.xls")
            == AttachmentType.SPREADSHEET
        )
        assert (
            AttachmentType.get_file_type_by_extension("data.xlsx")
            == AttachmentType.SPREADSHEET
        )
        assert (
            AttachmentType.get_file_type_by_extension("data.csv")
            == AttachmentType.SPREADSHEET
        )

    def test_get_file_type_by_extension_case_insensitive(self):
        """Test that extension matching is case insensitive."""
        assert (
            AttachmentType.get_file_type_by_extension("photo.JPG")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension("photo.JPEG")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension("photo.PNG")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension("document.PDF")
            == AttachmentType.PDF
        )
        assert (
            AttachmentType.get_file_type_by_extension("data.XLS")
            == AttachmentType.SPREADSHEET
        )
        assert (
            AttachmentType.get_file_type_by_extension("data.XLSX")
            == AttachmentType.SPREADSHEET
        )
        assert (
            AttachmentType.get_file_type_by_extension("data.CSV")
            == AttachmentType.SPREADSHEET
        )

    def test_get_file_type_by_extension_unknown_formats(self):
        """Test that unknown extensions return None."""
        assert AttachmentType.get_file_type_by_extension("file.txt") is None
        assert AttachmentType.get_file_type_by_extension("file.doc") is None
        assert AttachmentType.get_file_type_by_extension("file.docx") is None
        assert AttachmentType.get_file_type_by_extension("file.ppt") is None
        assert AttachmentType.get_file_type_by_extension("file.mp4") is None

    def test_get_file_type_by_extension_no_extension(self):
        """Test that files without extensions return None."""
        assert AttachmentType.get_file_type_by_extension("filename") is None
        assert AttachmentType.get_file_type_by_extension("filename.") is None

    def test_get_file_type_by_extension_complex_filenames(self):
        """Test that complex filenames with extensions work correctly."""
        assert (
            AttachmentType.get_file_type_by_extension("my.photo.2023.jpg")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension("report.final.v2.pdf")
            == AttachmentType.PDF
        )
        assert (
            AttachmentType.get_file_type_by_extension("data.quarterly.Q1.xlsx")
            == AttachmentType.SPREADSHEET
        )

    def test_get_file_type_by_extension_paths(self):
        """Test that filenames with paths work correctly."""
        assert (
            AttachmentType.get_file_type_by_extension("/path/to/photo.jpg")
            == AttachmentType.IMAGE
        )
        assert (
            AttachmentType.get_file_type_by_extension(
                "C:\\Users\\Documents\\report.pdf"
            )
            == AttachmentType.PDF
        )
        assert (
            AttachmentType.get_file_type_by_extension("./data/spreadsheet.xlsx")
            == AttachmentType.SPREADSHEET
        )


@pytest.mark.unit
class TestAttachmentTypeAllowedExtensions(TestCase):
    """Test allowed_extensions method."""

    def test_allowed_extensions(self):
        """Test that allowed_extensions returns all supported extensions."""
        expected_extensions = [".jpg", ".jpeg", ".png", ".pdf", ".xls", ".xlsx", ".csv"]

        allowed_extensions = AttachmentType.allowed_extensions()
        assert set(allowed_extensions) == set(expected_extensions)

    def test_allowed_extensions_structure(self):
        """Test that allowed_extensions returns a list."""
        allowed_extensions = AttachmentType.allowed_extensions()
        assert isinstance(allowed_extensions, list)

    def test_allowed_extensions_all_start_with_dot(self):
        """Test that all allowed extensions start with a dot."""
        allowed_extensions = AttachmentType.allowed_extensions()

        for extension in allowed_extensions:
            assert extension.startswith(".")

    def test_allowed_extensions_no_duplicates(self):
        """Test that allowed_extensions has no duplicate extensions."""
        allowed_extensions = AttachmentType.allowed_extensions()
        assert len(allowed_extensions) == len(set(allowed_extensions))

    def test_allowed_extensions_contains_all_mapped_extensions(self):
        """Test that allowed_extensions contains all extensions from the extension map."""
        extension_map = AttachmentType.get_extension_map()
        allowed_extensions = AttachmentType.allowed_extensions()

        for file_type, extensions in extension_map.items():
            for extension in extensions:
                assert extension in allowed_extensions


@pytest.mark.unit
class TestAttachmentTypeIntegration(TestCase):
    """Test integration between different AttachmentType methods."""

    def test_extension_map_and_file_type_consistency(self):
        """Test that extension map and file type detection are consistent."""
        extension_map = AttachmentType.get_extension_map()

        for file_type, extensions in extension_map.items():
            for extension in extensions:
                detected_type = AttachmentType.get_file_type_by_extension(
                    f"test{extension}"
                )
                assert detected_type == file_type, (
                    f"Extension {extension} should map to {file_type}"
                )

    def test_allowed_extensions_and_file_type_consistency(self):
        """Test that allowed extensions and file type detection are consistent."""
        allowed_extensions = AttachmentType.allowed_extensions()

        for extension in allowed_extensions:
            detected_type = AttachmentType.get_file_type_by_extension(
                f"test{extension}"
            )
            assert detected_type is not None, (
                f"Extension {extension} should be detected"
            )

    def test_choices_and_extension_map_consistency(self):
        """Test that choices and extension map are consistent."""
        choices = [choice[0] for choice in AttachmentType.choices]
        extension_map_keys = list(AttachmentType.get_extension_map().keys())

        # All extension map keys should be valid choices
        for key in extension_map_keys:
            assert key in choices

    def test_round_trip_file_type_detection(self):
        """Test round-trip file type detection with various extensions."""
        test_cases = [
            ("image.jpg", AttachmentType.IMAGE),
            ("document.pdf", AttachmentType.PDF),
            ("data.xlsx", AttachmentType.SPREADSHEET),
        ]

        for filename, expected_type in test_cases:
            detected_type = AttachmentType.get_file_type_by_extension(filename)
            assert detected_type == expected_type, f"Failed for {filename}"

            # Test reverse lookup
            if detected_type in AttachmentType.get_extension_map():
                extensions = AttachmentType.get_extension_map()[detected_type]
                # Extract extension from filename
                import os

                ext = os.path.splitext(filename)[1].lower()
                assert ext in extensions, (
                    f"Extension {ext} should be in {detected_type} extensions"
                )
