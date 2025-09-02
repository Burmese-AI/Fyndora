"""
Unit tests for apps.core.templatetags.millify_filters
"""

import pytest
from unittest.mock import patch

from apps.core.templatetags.millify_filters import millify_number


@pytest.mark.unit
class TestMillifyNumberFilter:
    def test_millify_number_with_integer(self):
        """Test millify_number with integer values."""
        result = millify_number(1000)
        assert result == "1k"

    def test_millify_number_with_float(self):
        """Test millify_number with float values."""
        result = millify_number(1500.5)
        assert result == "1.5k"

    def test_millify_number_with_string_number(self):
        """Test millify_number with string numbers."""
        result = millify_number("2000")
        assert result == "2k"

    def test_millify_number_with_precision(self):
        """Test millify_number with custom precision."""
        result = millify_number(1234, precision=2)
        assert result == "1.23k"

    def test_millify_number_with_zero_precision(self):
        """Test millify_number with zero precision."""
        result = millify_number(1234, precision=0)
        assert result == "1k"

    def test_millify_number_with_large_numbers(self):
        """Test millify_number with large numbers."""
        result = millify_number(1000000)
        assert result == "1M"

        result = millify_number(1500000000)
        assert result == "1.5B"

    def test_millify_number_with_small_numbers(self):
        """Test millify_number with small numbers."""
        result = millify_number(500)
        assert result == "500"

        result = millify_number(999)
        assert result == "999"

    def test_millify_number_with_negative_numbers(self):
        """Test millify_number with negative numbers."""
        result = millify_number(-1000)
        assert result == "-1k"

        result = millify_number(-1500.5)
        assert result == "-1.5k"

    def test_millify_number_with_zero(self):
        """Test millify_number with zero."""
        result = millify_number(0)
        assert result == "0"

    def test_millify_number_with_decimal(self):
        """Test millify_number with decimal values."""
        result = millify_number(0.5)
        assert result == "0.5"

        result = millify_number(0.001)
        assert result == "0"

    def test_millify_number_with_invalid_string(self):
        """Test millify_number with invalid string input."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number("invalid")
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_none(self):
        """Test millify_number with None input."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number(None)
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_empty_string(self):
        """Test millify_number with empty string."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number("")
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_boolean(self):
        """Test millify_number with boolean values."""
        result = millify_number(True)
        assert result == "1"

        result = millify_number(False)
        assert result == "0"

    def test_millify_number_with_very_large_precision(self):
        """Test millify_number with very large precision."""
        result = millify_number(1234.56789, precision=10)
        assert result == "1.23456789k"

    def test_millify_number_with_negative_precision(self):
        """Test millify_number with negative precision."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number(1234, precision=-1)
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_string_precision(self):
        """Test millify_number with string precision."""
        result = millify_number(1234, precision="2")
        assert result == "1.23k"

    def test_millify_number_with_invalid_precision(self):
        """Test millify_number with invalid precision."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number(1234, precision="invalid")
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_millify_exception(self):
        """Test millify_number when millify function raises exception."""
        with patch("apps.core.templatetags.millify_filters.millify") as mock_millify:
            mock_millify.side_effect = Exception("Test exception")

            with patch("apps.core.templatetags.millify_filters.print") as mock_print:
                result = millify_number(1000)
                assert result is None
                mock_print.assert_called_once_with(
                    "Error in millify_number: Test exception"
                )

    def test_millify_number_with_float_conversion_exception(self):
        """Test millify_number when float conversion fails."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number("not_a_number")
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_int_conversion_exception(self):
        """Test millify_number when int conversion for precision fails."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number(1000, precision="not_a_number")
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_complex_numbers(self):
        """Test millify_number with complex number-like strings."""
        with patch("apps.core.templatetags.millify_filters.print") as mock_print:
            result = millify_number("1+2j")
            assert result is None
            mock_print.assert_called_once()

    def test_millify_number_with_scientific_notation(self):
        """Test millify_number with scientific notation."""
        result = millify_number("1e3")
        assert result == "1k"

        result = millify_number("1.5e6")
        assert result == "1.5M"

    def test_millify_number_with_very_small_numbers(self):
        """Test millify_number with very small numbers."""
        result = millify_number(0.0001)
        assert result == "0"

        result = millify_number(0.00001)
        assert result == "0"
