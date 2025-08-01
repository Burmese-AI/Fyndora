"""
Unit tests for Attachment constants and utilities.

Tests attachment type constants, file extension mapping, and utility functions.
"""

import pytest

from apps.attachments.constants import AttachmentType


@pytest.mark.unit
class TestAttachmentTypeConstants:
    """Test AttachmentType constants and choices."""

    def test_attachment_type_choices(self):
        """Test that all attachment types are properly defined."""
        expected_choices = [
            ("image", "Image"),
            ("pdf", "PDF"),
            ("spreadsheet", "Spreadsheet"),
            ("other", "Other"),
        ]

        assert AttachmentType.choices == expected_choices

    def test_attachment_type_values(self):
        """Test individual attachment type values."""
        assert AttachmentType.IMAGE == "image"
        assert AttachmentType.PDF == "pdf"
        assert AttachmentType.SPREADSHEET == "spreadsheet"
        assert AttachmentType.OTHER == "other"

    def test_attachment_type_labels(self):
        """Test attachment type display labels."""
        assert AttachmentType.IMAGE.label == "Image"
        assert AttachmentType.PDF.label == "PDF"
        assert AttachmentType.SPREADSHEET.label == "Spreadsheet"
        assert AttachmentType.OTHER.label == "Other"


@pytest.mark.unit
class TestAttachmentTypeExtensionMapping:
    """Test file extension mapping functionality."""

    def test_get_extension_map(self):
        """Test extension mapping for all file types."""
        extension_map = AttachmentType.get_extension_map()

        expected_map = {
            AttachmentType.IMAGE: [".jpg", ".jpeg", ".png"],
            AttachmentType.PDF: [".pdf"],
            AttachmentType.SPREADSHEET: [".xls", ".xlsx", ".csv"],
        }

        assert extension_map == expected_map

    def test_get_extension_map_structure(self):
        """Test that extension map has correct structure."""
        extension_map = AttachmentType.get_extension_map()

        # Should be a dictionary
        assert isinstance(extension_map, dict)

        # Should have entries for main file types (excluding OTHER)
        assert AttachmentType.IMAGE in extension_map
        assert AttachmentType.PDF in extension_map
        assert AttachmentType.SPREADSHEET in extension_map

        # OTHER type should not be in extension map
        assert AttachmentType.OTHER not in extension_map

        # All values should be lists
        for file_type, extensions in extension_map.items():
            assert isinstance(extensions, list)
            assert len(extensions) > 0

            # All extensions should start with dot
            for ext in extensions:
                assert ext.startswith(".")


@pytest.mark.unit
class TestGetFileTypeByExtension:
    """Test file type detection by extension."""

    def test_image_file_detection(self):
        """Test detection of image files."""
        image_files = [
            "photo.jpg",
            "picture.jpeg",
            "graphic.png",
            "PHOTO.JPG",  # Test case insensitive
            "image.PNG",
        ]

        for filename in image_files:
            file_type = AttachmentType.get_file_type_by_extension(filename)
            assert file_type == AttachmentType.IMAGE, f"Failed for {filename}"

    def test_pdf_file_detection(self):
        """Test detection of PDF files."""
        pdf_files = [
            "document.pdf",
            "report.PDF",  # Test case insensitive
            "file.Pdf",
        ]

        for filename in pdf_files:
            file_type = AttachmentType.get_file_type_by_extension(filename)
            assert file_type == AttachmentType.PDF, f"Failed for {filename}"

    def test_spreadsheet_file_detection(self):
        """Test detection of spreadsheet files."""
        spreadsheet_files = [
            "data.xls",
            "analysis.xlsx",
            "export.csv",
            "DATA.XLS",  # Test case insensitive
            "report.XLSX",
            "data.CSV",
        ]

        for filename in spreadsheet_files:
            file_type = AttachmentType.get_file_type_by_extension(filename)
            assert file_type == AttachmentType.SPREADSHEET, f"Failed for {filename}"

    def test_unknown_file_detection(self):
        """Test detection of unknown file types."""
        unknown_files = [
            "readme.txt",
            "config.json",
            "script.py",
            "data.xml",
            "file.doc",
            "presentation.ppt",
            "noextension",
            "",
        ]

        for filename in unknown_files:
            file_type = AttachmentType.get_file_type_by_extension(filename)
            assert file_type is None, f"Should return None for {filename}"

    def test_file_with_multiple_dots(self):
        """Test files with multiple dots in filename."""
        test_cases = [
            ("backup.data.xlsx", AttachmentType.SPREADSHEET),
            ("report.final.pdf", AttachmentType.PDF),
            ("image.thumb.jpg", AttachmentType.IMAGE),
            ("config.backup.txt", None),
        ]

        for filename, expected_type in test_cases:
            file_type = AttachmentType.get_file_type_by_extension(filename)
            assert file_type == expected_type, f"Failed for {filename}"

    def test_file_with_path(self):
        """Test files with full paths."""
        test_cases = [
            ("/path/to/document.pdf", AttachmentType.PDF),
            ("C:\\Users\\user\\image.jpg", AttachmentType.IMAGE),
            ("./relative/path/data.xlsx", AttachmentType.SPREADSHEET),
            ("/path/to/unknown.txt", None),
        ]

        for filepath, expected_type in test_cases:
            file_type = AttachmentType.get_file_type_by_extension(filepath)
            assert file_type == expected_type, f"Failed for {filepath}"

    def test_edge_cases(self):
        """Test edge cases for file type detection."""
        edge_cases = [
            # Directory references
            (".", None),
            ("..", None),
            # Hidden files without extensions
            (".hidden", None),
            (".gitignore", None),
            (".env", None),
            # Files ending with dots (no extension)
            ("file.", None),
            ("document.", None),
            # Hidden files that look like extensions (but aren't)
            (
                ".pdf",
                None,
            ),  # Hidden file - os.path.splitext treats this as filename, not extension
            (
                ".jpg",
                None,
            ),  # Hidden file - os.path.splitext treats this as filename, not extension
            # Empty and whitespace
            ("", None),
            ("   ", None),
            # Files with only dots
            ("...", None),
            ("....", None),
        ]

        for filename, expected_type in edge_cases:
            file_type = AttachmentType.get_file_type_by_extension(filename)
            assert file_type == expected_type, f"Failed for {filename}"


@pytest.mark.unit
class TestAllowedExtensions:
    """Test allowed extensions functionality."""

    def test_allowed_extensions_list(self):
        """Test that allowed extensions returns all supported extensions."""
        allowed = AttachmentType.allowed_extensions()

        expected_extensions = [
            ".jpg",
            ".jpeg",
            ".png",  # Images
            ".pdf",  # PDF
            ".xls",
            ".xlsx",
            ".csv",  # Spreadsheets
        ]

        # Should contain all expected extensions
        for ext in expected_extensions:
            assert ext in allowed, f"Missing extension: {ext}"

        # Should not contain duplicates
        assert len(allowed) == len(set(allowed))

    def test_allowed_extensions_structure(self):
        """Test structure of allowed extensions list."""
        allowed = AttachmentType.allowed_extensions()

        # Should be a list
        assert isinstance(allowed, list)

        # Should not be empty
        assert len(allowed) > 0

        # All items should be strings starting with dot
        for ext in allowed:
            assert isinstance(ext, str)
            assert ext.startswith(".")
            assert len(ext) > 1  # More than just the dot

    def test_allowed_extensions_completeness(self):
        """Test that allowed extensions includes all mapped extensions."""
        allowed = set(AttachmentType.allowed_extensions())
        extension_map = AttachmentType.get_extension_map()

        # Collect all extensions from the map
        mapped_extensions = set()
        for ext_list in extension_map.values():
            mapped_extensions.update(ext_list)

        # Allowed extensions should match mapped extensions
        assert allowed == mapped_extensions


@pytest.mark.unit
class TestAttachmentTypeUtilityIntegration:
    """Test integration between different utility methods."""

    def test_extension_detection_consistency(self):
        """Test consistency between extension mapping and detection."""
        extension_map = AttachmentType.get_extension_map()

        # Test each mapped extension
        for file_type, extensions in extension_map.items():
            for ext in extensions:
                # Create a test filename
                test_filename = f"test{ext}"

                # Should detect the correct file type
                detected_type = AttachmentType.get_file_type_by_extension(test_filename)
                assert detected_type == file_type, f"Inconsistent detection for {ext}"

    def test_allowed_extensions_detection_consistency(self):
        """Test that all allowed extensions can be detected."""
        allowed_extensions = AttachmentType.allowed_extensions()

        for ext in allowed_extensions:
            test_filename = f"test{ext}"
            detected_type = AttachmentType.get_file_type_by_extension(test_filename)

            # Should detect a valid type (not None)
            assert detected_type is not None, (
                f"Cannot detect type for allowed extension {ext}"
            )

            # Should be one of the defined types (excluding OTHER)
            assert detected_type in [
                AttachmentType.IMAGE,
                AttachmentType.PDF,
                AttachmentType.SPREADSHEET,
            ], f"Unexpected type {detected_type} for extension {ext}"

    def test_case_insensitive_consistency(self):
        """Test case insensitive behavior across all methods."""
        test_extensions = [".jpg", ".pdf", ".xlsx"]

        for ext in test_extensions:
            base_filename = f"test{ext}"
            upper_filename = f"test{ext.upper()}"
            mixed_filename = f"test{ext.capitalize()}"

            # All should detect the same type
            base_type = AttachmentType.get_file_type_by_extension(base_filename)
            upper_type = AttachmentType.get_file_type_by_extension(upper_filename)
            mixed_type = AttachmentType.get_file_type_by_extension(mixed_filename)

            assert base_type == upper_type == mixed_type, (
                f"Inconsistent case handling for {ext}"
            )

    def test_comprehensive_file_type_coverage(self):
        """Test that all file types have proper extension mappings."""
        # Get all defined file types except OTHER
        defined_types = [
            AttachmentType.IMAGE,
            AttachmentType.PDF,
            AttachmentType.SPREADSHEET,
        ]

        extension_map = AttachmentType.get_extension_map()

        # Each defined type should have extensions
        for file_type in defined_types:
            assert file_type in extension_map, f"No extensions defined for {file_type}"
            assert len(extension_map[file_type]) > 0, (
                f"Empty extensions for {file_type}"
            )

        # OTHER type should not have extensions (it's the fallback)
        assert AttachmentType.OTHER not in extension_map
