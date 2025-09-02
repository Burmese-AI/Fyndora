"""
Unit tests for apps.core.services.file_export_services
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from django.http import HttpResponse

from apps.core.services.file_export_services import CsvExporter, PdfExporter


@pytest.mark.unit
class TestCsvExporter:
    def test_export_with_table_block(self):
        blocks = [
            {
                "type": "table",
                "columns": [("name", "Name"), ("age", "Age")],
                "rows": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
            }
        ]
        exporter = CsvExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)
            assert response["Content-Type"] == "text/csv"
            assert 'attachment; filename="test-2024-01-01.csv"' in response["Content-Disposition"]

    def test_export_with_paragraph_block(self):
        blocks = [{"type": "paragraph", "text": "This is a test paragraph"}]
        exporter = CsvExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)
            assert response["Content-Type"] == "text/csv"

    def test_export_with_table_and_footer(self):
        blocks = [
            {
                "type": "table",
                "columns": [("amount", "Amount")],
                "rows": [{"amount": 100}, {"amount": 200}],
                "footer": [{"amount": 300}],
            }
        ]
        exporter = CsvExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)

    def test_export_with_missing_row_keys(self):
        blocks = [
            {
                "type": "table",
                "columns": [("name", "Name"), ("age", "Age")],
                "rows": [{"name": "John"}],  # Missing age key
            }
        ]
        exporter = CsvExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)


@pytest.mark.unit
class TestPdfExporter:
    def test_export_with_table_block(self):
        blocks = [
            {
                "type": "table",
                "columns": [("name", "Name"), ("age", "Age")],
                "rows": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
            }
        ]
        exporter = PdfExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)
            assert response["Content-Type"] == "application/pdf"
            assert 'attachment; filename="test-2024-01-01.pdf"' in response["Content-Disposition"]

    def test_export_with_paragraph_block(self):
        blocks = [{"type": "paragraph", "text": "This is a test paragraph"}]
        exporter = PdfExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)
            assert response["Content-Type"] == "application/pdf"

    def test_export_with_table_and_footer(self):
        blocks = [
            {
                "type": "table",
                "columns": [("amount", "Amount")],
                "rows": [{"amount": 100}, {"amount": 200}],
                "footer": [{"amount": 300}],
            }
        ]
        exporter = PdfExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)

    def test_calculate_col_widths_with_scale(self):
        exporter = PdfExporter("test", [])
        
        # Mock PDF object
        mock_pdf = Mock()
        mock_pdf.get_string_width.return_value = 10
        mock_pdf.w = 100
        mock_pdf.l_margin = 10
        
        columns = [("name", "Name"), ("age", "Age")]
        rows = [{"name": "John", "age": 30}]
        footer_rows = []
        
        widths = exporter._calculate_col_widths(mock_pdf, columns, rows, footer_rows)
        
        assert len(widths) == 2
        assert all(w > 0 for w in widths)

    def test_calculate_col_widths_without_scale(self):
        exporter = PdfExporter("test", [])
        
        # Mock PDF object with wide page
        mock_pdf = Mock()
        mock_pdf.get_string_width.return_value = 5
        mock_pdf.w = 1000  # Very wide page
        mock_pdf.l_margin = 10
        
        columns = [("name", "Name")]
        rows = [{"name": "John"}]
        footer_rows = []
        
        widths = exporter._calculate_col_widths(mock_pdf, columns, rows, footer_rows)
        
        assert len(widths) == 1
        assert widths[0] > 0

    def test_export_with_missing_row_keys(self):
        blocks = [
            {
                "type": "table",
                "columns": [("name", "Name"), ("age", "Age")],
                "rows": [{"name": "John"}],  # Missing age key
            }
        ]
        exporter = PdfExporter("test", blocks)
        
        with patch("apps.core.services.file_export_services.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = "2024-01-01"
            
            response = exporter.export()
            
            assert isinstance(response, HttpResponse)
