"""
Unit tests for apps.core.services.base_services
"""

import pytest

from apps.core.services.base_services import BaseFileExporter


@pytest.mark.unit
class TestBaseFileExporter:
    def test_init_sets_attributes(self):
        filename_prefix = "test_prefix"
        blocks = [{"type": "header"}, {"type": "data"}]

        exporter = BaseFileExporter(filename_prefix, blocks)

        assert exporter.filename_prefix == filename_prefix
        assert exporter.blocks == blocks

    def test_export_raises_not_implemented_error(self):
        exporter = BaseFileExporter("prefix", [])

        with pytest.raises(
            NotImplementedError, match="Subclasses must implement export\\(\\)"
        ):
            exporter.export()

    def test_export_with_different_blocks(self):
        # Test with empty blocks
        exporter_empty = BaseFileExporter("empty", [])
        with pytest.raises(NotImplementedError):
            exporter_empty.export()

        # Test with multiple blocks
        exporter_many = BaseFileExporter("many", [{"a": 1}, {"b": 2}, {"c": 3}])
        with pytest.raises(NotImplementedError):
            exporter_many.export()
