"""
Unit tests for Remittance constants.
"""

from django.test import TestCase
from apps.remittance.constants import RemittanceStatus


class RemittanceStatusTest(TestCase):
    """Test cases for RemittanceStatus constants."""

    def test_remittance_status_choices_exist(self):
        """Test that all expected remittance status choices exist."""
        expected_statuses = ["pending", "partial", "paid", "overpaid", "overdue", "canceled"]

        for status in expected_statuses:
            assert hasattr(RemittanceStatus, status.upper())

    def test_remittance_status_values(self):
        """Test that remittance status values are correct."""
        assert RemittanceStatus.PENDING.value == "pending"
        assert RemittanceStatus.PARTIAL.value == "partial"
        assert RemittanceStatus.PAID.value == "paid"
        assert RemittanceStatus.OVERPAID.value == "overpaid"
        assert RemittanceStatus.OVERDUE.value == "overdue"
        assert RemittanceStatus.CANCELED.value == "canceled"

    def test_remittance_status_labels(self):
        """Test that remittance status labels are correct."""
        assert RemittanceStatus.PENDING.label == "Pending"
        assert RemittanceStatus.PARTIAL.label == "Partially Paid"
        assert RemittanceStatus.PAID.label == "Paid"
        assert RemittanceStatus.OVERPAID.label == "Overpaid"
        assert RemittanceStatus.OVERDUE.label == "Overdue"
        assert RemittanceStatus.CANCELED.label == "Canceled"

    def test_remittance_status_choices_structure(self):
        """Test that choices have the correct structure."""
        choices = RemittanceStatus.choices

        # Check that choices is a list of tuples
        assert isinstance(choices, list)

        # Check that each choice is a tuple with 2 elements
        for choice in choices:
            assert isinstance(choice, tuple)
            assert len(choice) == 2

        # Check that first element is the value, second is the label
        for value, label in choices:
            assert isinstance(value, str)
            assert isinstance(label, str)

    def test_remittance_status_names(self):
        """Test that remittance status names are correct."""
        assert RemittanceStatus.PENDING.name == "PENDING"
        assert RemittanceStatus.PARTIAL.name == "PARTIAL"
        assert RemittanceStatus.PAID.name == "PAID"
        assert RemittanceStatus.OVERPAID.name == "OVERPAID"
        assert RemittanceStatus.OVERDUE.name == "OVERDUE"
        assert RemittanceStatus.CANCELED.name == "CANCELED"

    def test_remittance_status_choices_contains_all_statuses(self):
        """Test that choices contains all defined statuses."""
        expected_choices = [
            ("pending", "Pending"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
            ("overpaid", "Overpaid"),
            ("overdue", "Overdue"),
            ("canceled", "Canceled"),
        ]

        for expected_choice in expected_choices:
            assert expected_choice in RemittanceStatus.choices

    def test_remittance_status_choices_length(self):
        """Test that there are exactly 6 status choices."""
        assert len(RemittanceStatus.choices) == 6

    def test_remittance_status_values_are_strings(self):
        """Test that all status values are strings."""
        for status in RemittanceStatus:
            assert isinstance(status.value, str)

    def test_remittance_status_labels_are_strings(self):
        """Test that all status labels are strings."""
        for status in RemittanceStatus:
            assert isinstance(status.label, str)

    def test_remittance_status_names_are_strings(self):
        """Test that all status names are strings."""
        for status in RemittanceStatus:
            assert isinstance(status.name, str)

    def test_remittance_status_immutability(self):
        """Test that status values cannot be modified."""
        try:
            RemittanceStatus.PENDING.value = "new_value"
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass

    def test_remittance_status_enumeration(self):
        """Test that statuses can be enumerated."""
        statuses = list(RemittanceStatus)
        assert len(statuses) == 6

        # Check that all expected statuses are present
        status_values = [status.value for status in statuses]
        expected_values = ["pending", "partial", "paid", "overpaid", "overdue", "canceled"]

        for expected_value in expected_values:
            assert expected_value in status_values

    def test_remittance_status_choice_validation(self):
        """Test that status choices can be used for validation."""
        # Valid choices should work
        valid_choices = ["pending", "partial", "paid", "overpaid", "overdue", "canceled"]

        for choice in valid_choices:
            assert choice in [status.value for status in RemittanceStatus]

        # Invalid choices should not be in choices
        invalid_choices = ["invalid_status", "completed", "rejected", "draft"]

        for choice in invalid_choices:
            assert choice not in [status.value for status in RemittanceStatus]

    def test_remittance_status_display_values(self):
        """Test that status display values are human-readable."""
        # Check that labels are human-readable and not just the raw values
        assert RemittanceStatus.PENDING.label != RemittanceStatus.PENDING.value
        assert RemittanceStatus.PARTIAL.label != RemittanceStatus.PARTIAL.value
        assert RemittanceStatus.PAID.label != RemittanceStatus.PAID.value
        assert RemittanceStatus.OVERPAID.label != RemittanceStatus.OVERPAID.value
        assert RemittanceStatus.OVERDUE.label != RemittanceStatus.OVERDUE.value
        assert RemittanceStatus.CANCELED.label != RemittanceStatus.CANCELED.value

        # Check that labels have proper capitalization
        assert RemittanceStatus.PENDING.label[0].isupper()
        assert RemittanceStatus.PARTIAL.label[0].isupper()
        assert RemittanceStatus.PAID.label[0].isupper()
        assert RemittanceStatus.OVERPAID.label[0].isupper()
        assert RemittanceStatus.OVERDUE.label[0].isupper()
        assert RemittanceStatus.CANCELED.label[0].isupper()

    def test_remittance_status_choices_uniqueness(self):
        """Test that all status values and labels are unique."""
        values = [status.value for status in RemittanceStatus]
        labels = [status.label for status in RemittanceStatus]
        
        # Check that values are unique
        assert len(values) == len(set(values))
        
        # Check that labels are unique
        assert len(labels) == len(set(labels))

    def test_remittance_status_inheritance(self):
        """Test that RemittanceStatus inherits from models.TextChoices."""
        from django.db import models
        assert issubclass(RemittanceStatus, models.TextChoices)
