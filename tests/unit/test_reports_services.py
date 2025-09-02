"""
Unit tests for apps.reports.services
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal

from apps.reports.services import export_overview_finance_report
from apps.core.services.base_services import BaseFileExporter


@pytest.mark.unit
class TestExportOverviewFinanceReport:
    def test_export_overview_finance_report_with_org_level(self):
        """Test export with organization level data."""
        context = {
            "report_data": {
                "title": "Test Organization",
                "level": "org",
                "total_income": Decimal("1000.00"),
                "total_expense": Decimal("200.00"),
                "org_share": Decimal("800.00"),
                "parent_lvl_total_expense": Decimal("50.00"),
                "final_net_profit": Decimal("750.00"),
                "children": [
                    {
                        "title": "Workspace 1",
                        "level": "workspace",
                        "total_income": Decimal("500.00"),
                        "total_expense": Decimal("100.00"),
                        "org_share": Decimal("400.00"),
                        "parent_lvl_total_expense": Decimal("25.00"),
                        "final_net_profit": Decimal("375.00"),
                        "children": [
                            {
                                "title": "Team 1",
                                "total_income": Decimal("300.00"),
                                "total_expense": Decimal("50.00"),
                                "net_income": Decimal("250.00"),
                                "remittance_rate": 90,
                                "org_share": Decimal("225.00"),
                            }
                        ]
                    }
                ]
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_team_leaf_node(self):
        """Test export with team leaf node (no children)."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": Decimal("100.00"),
                "total_expense": Decimal("20.00"),
                "net_income": Decimal("80.00"),
                "remittance_rate": 85,
                "org_share": Decimal("68.00"),
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_missing_optional_fields(self):
        """Test export with missing optional fields."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": Decimal("100.00"),
                "total_expense": Decimal("20.00"),
                # Missing net_income, remittance_rate, org_share
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_none_remittance_rate(self):
        """Test export with None remittance_rate."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": Decimal("100.00"),
                "total_expense": Decimal("20.00"),
                "remittance_rate": None,
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_zero_remittance_rate(self):
        """Test export with zero remittance_rate."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": Decimal("100.00"),
                "total_expense": Decimal("20.00"),
                "remittance_rate": 0,
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_workspace_level(self):
        """Test export with workspace level data."""
        context = {
            "report_data": {
                "title": "Test Workspace",
                "level": "workspace",
                "total_income": Decimal("500.00"),
                "total_expense": Decimal("100.00"),
                "org_share": Decimal("400.00"),
                "parent_lvl_total_expense": Decimal("25.00"),
                "final_net_profit": Decimal("375.00"),
                "children": [
                    {
                        "title": "Team 1",
                        "total_income": Decimal("300.00"),
                        "total_expense": Decimal("50.00"),
                        "net_income": Decimal("250.00"),
                        "remittance_rate": 90,
                        "org_share": Decimal("225.00"),
                    }
                ]
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_team_level(self):
        """Test export with team level data."""
        context = {
            "report_data": {
                "title": "Test Team",
                "level": "team",
                "total_income": Decimal("300.00"),
                "total_expense": Decimal("50.00"),
                "net_income": Decimal("250.00"),
                "org_share": Decimal("225.00"),
                "parent_lvl_total_expense": Decimal("10.00"),
                "final_net_profit": Decimal("215.00"),
                "children": []
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_multiple_children(self):
        """Test export with multiple children at different levels."""
        context = {
            "report_data": {
                "title": "Test Organization",
                "level": "org",
                "total_income": Decimal("1000.00"),
                "total_expense": Decimal("200.00"),
                "org_share": Decimal("800.00"),
                "parent_lvl_total_expense": Decimal("50.00"),
                "final_net_profit": Decimal("750.00"),
                "children": [
                    {
                        "title": "Workspace 1",
                        "level": "workspace",
                        "total_income": Decimal("500.00"),
                        "total_expense": Decimal("100.00"),
                        "org_share": Decimal("400.00"),
                        "parent_lvl_total_expense": Decimal("25.00"),
                        "final_net_profit": Decimal("375.00"),
                        "children": [
                            {
                                "title": "Team 1",
                                "total_income": Decimal("300.00"),
                                "total_expense": Decimal("50.00"),
                                "net_income": Decimal("250.00"),
                                "remittance_rate": 90,
                                "org_share": Decimal("225.00"),
                            },
                            {
                                "title": "Team 2",
                                "total_income": Decimal("200.00"),
                                "total_expense": Decimal("50.00"),
                                "net_income": Decimal("150.00"),
                                "remittance_rate": 85,
                                "org_share": Decimal("127.50"),
                            }
                        ]
                    },
                    {
                        "title": "Workspace 2",
                        "level": "workspace",
                        "total_income": Decimal("500.00"),
                        "total_expense": Decimal("100.00"),
                        "org_share": Decimal("400.00"),
                        "parent_lvl_total_expense": Decimal("25.00"),
                        "final_net_profit": Decimal("375.00"),
                        "children": []
                    }
                ]
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_empty_children(self):
        """Test export with empty children list."""
        context = {
            "report_data": {
                "title": "Test Organization",
                "level": "org",
                "total_income": Decimal("1000.00"),
                "total_expense": Decimal("200.00"),
                "org_share": Decimal("800.00"),
                "parent_lvl_total_expense": Decimal("50.00"),
                "final_net_profit": Decimal("750.00"),
                "children": []
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_missing_children_key(self):
        """Test export with missing children key (treated as leaf node)."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": Decimal("100.00"),
                "total_expense": Decimal("20.00"),
                "net_income": Decimal("80.00"),
                "remittance_rate": 85,
                "org_share": Decimal("68.00"),
                # No children key
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_exporter_class_parameters(self):
        """Test that exporter class is called with correct parameters."""
        context = {
            "report_data": {
                "title": "Test Organization",
                "total_income": Decimal("1000.00"),
                "total_expense": Decimal("200.00"),
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        # Verify exporter class was called with correct parameters
        mock_exporter_class.assert_called_once()
        call_args = mock_exporter_class.call_args[0]
        assert call_args[0] == "overview-finance-report"
        assert isinstance(call_args[1], list)  # blocks parameter
        assert len(call_args[1]) == 2  # paragraph and table blocks

    def test_export_overview_finance_report_blocks_structure(self):
        """Test that blocks are structured correctly."""
        context = {
            "report_data": {
                "title": "Test Organization",
                "total_income": Decimal("1000.00"),
                "total_expense": Decimal("200.00"),
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        export_overview_finance_report(context, mock_exporter_class)
        
        # Get the blocks passed to exporter
        call_args = mock_exporter_class.call_args[0]
        blocks = call_args[1]
        
        # Check paragraph block
        paragraph_block = blocks[0]
        assert paragraph_block["type"] == "paragraph"
        assert paragraph_block["text"] == "Report for Test Organization"
        
        # Check table block
        table_block = blocks[1]
        assert table_block["type"] == "table"
        assert "columns" in table_block
        assert "rows" in table_block
        
        # Check columns structure
        expected_columns = [
            ("name", "Name"),
            ("total_income", "Total Income"),
            ("total_disbursement", "Total Disbursement"),
            ("wt_net_income", "WT Net Income"),
            ("workspace_net_income", "Workspace Net Income"),
            ("org_net_income", "Org Net Income"),
            ("remittance_rate", "Remittance Rate"),
            ("expense_amount", "Expense Amount"),
            ("org_share", "Org Share"),
        ]
        assert table_block["columns"] == expected_columns

    def test_export_overview_finance_report_with_decimal_values(self):
        """Test export with Decimal values in data."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": Decimal("123.45"),
                "total_expense": Decimal("67.89"),
                "net_income": Decimal("55.56"),
                "remittance_rate": 90,
                "org_share": Decimal("50.00"),
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_string_values(self):
        """Test export with string values in data."""
        context = {
            "report_data": {
                "title": "Test Team",
                "total_income": "100.00",
                "total_expense": "20.00",
                "net_income": "80.00",
                "remittance_rate": 85,
                "org_share": "68.00",
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.return_value = "exported_data"
        
        result = export_overview_finance_report(context, mock_exporter_class)
        
        assert result == "exported_data"
        mock_exporter_class.assert_called_once()
        mock_exporter.export.assert_called_once()

    def test_export_overview_finance_report_with_exporter_exception(self):
        """Test export when exporter raises an exception."""
        context = {
            "report_data": {
                "title": "Test Organization",
                "total_income": Decimal("1000.00"),
                "total_expense": Decimal("200.00"),
            }
        }
        
        mock_exporter_class = Mock()
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.export.side_effect = Exception("Export failed")
        
        with pytest.raises(Exception, match="Export failed"):
            export_overview_finance_report(context, mock_exporter_class)

    def test_export_overview_finance_report_with_none_context(self):
        """Test export with None context."""
        context = None
        
        with pytest.raises(TypeError):
            export_overview_finance_report(context, Mock())

    def test_export_overview_finance_report_with_missing_report_data(self):
        """Test export with missing report_data key."""
        context = {}
        
        with pytest.raises(KeyError):
            export_overview_finance_report(context, Mock())
