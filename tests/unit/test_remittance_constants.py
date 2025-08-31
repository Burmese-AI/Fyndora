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
            self.assertTrue(hasattr(RemittanceStatus, status.upper()))

    def test_remittance_status_values(self):
        """Test that remittance status values are correct."""
        self.assertEqual(RemittanceStatus.PENDING.value, "pending")
        self.assertEqual(RemittanceStatus.PARTIAL.value, "partial")
        self.assertEqual(RemittanceStatus.PAID.value, "paid")
        self.assertEqual(RemittanceStatus.OVERPAID.value, "overpaid")
        self.assertEqual(RemittanceStatus.OVERDUE.value, "overdue")
        self.assertEqual(RemittanceStatus.CANCELED.value, "canceled")

    def test_remittance_status_labels(self):
        """Test that remittance status labels are correct."""
        self.assertEqual(RemittanceStatus.PENDING.label, "Pending")
        self.assertEqual(RemittanceStatus.PARTIAL.label, "Partially Paid")
        self.assertEqual(RemittanceStatus.PAID.label, "Paid")
        self.assertEqual(RemittanceStatus.OVERPAID.label, "Overpaid")
        self.assertEqual(RemittanceStatus.OVERDUE.label, "Overdue")
        self.assertEqual(RemittanceStatus.CANCELED.label, "Canceled")

    def test_remittance_status_choices_structure(self):
        """Test that choices have the correct structure."""
        choices = RemittanceStatus.choices

        # Check that choices is a list of tuples
        self.assertIsInstance(choices, list)

        # Check that each choice is a tuple with 2 elements
        for choice in choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)

        # Check that first element is the value, second is the label
        for value, label in choices:
            self.assertIsInstance(value, str)
            self.assertIsInstance(label, str)

    def test_remittance_status_names(self):
        """Test that remittance status names are correct."""
        self.assertEqual(RemittanceStatus.PENDING.name, "PENDING")
        self.assertEqual(RemittanceStatus.PARTIAL.name, "PARTIAL")
        self.assertEqual(RemittanceStatus.PAID.name, "PAID")
        self.assertEqual(RemittanceStatus.OVERPAID.name, "OVERPAID")
        self.assertEqual(RemittanceStatus.OVERDUE.name, "OVERDUE")
        self.assertEqual(RemittanceStatus.CANCELED.name, "CANCELED")

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
            self.assertIn(expected_choice, RemittanceStatus.choices)

    def test_remittance_status_choices_length(self):
        """Test that there are exactly 6 status choices."""
        self.assertEqual(len(RemittanceStatus.choices), 6)

    def test_remittance_status_values_are_strings(self):
        """Test that all status values are strings."""
        for status in RemittanceStatus:
            self.assertIsInstance(status.value, str)

    def test_remittance_status_labels_are_strings(self):
        """Test that all status labels are strings."""
        for status in RemittanceStatus:
            self.assertIsInstance(status.label, str)

    def test_remittance_status_names_are_strings(self):
        """Test that all status names are strings."""
        for status in RemittanceStatus:
            self.assertIsInstance(status.name, str)

    def test_remittance_status_immutability(self):
        """Test that status values cannot be modified."""
        with self.assertRaises(AttributeError):
            RemittanceStatus.PENDING.value = "new_value"

    def test_remittance_status_enumeration(self):
        """Test that statuses can be enumerated."""
        statuses = list(RemittanceStatus)
        self.assertEqual(len(statuses), 6)

        # Check that all expected statuses are present
        status_values = [status.value for status in statuses]
        expected_values = ["pending", "partial", "paid", "overpaid", "overdue", "canceled"]

        for expected_value in expected_values:
            self.assertIn(expected_value, status_values)

    def test_remittance_status_choice_validation(self):
        """Test that status choices can be used for validation."""
        # Valid choices should work
        valid_choices = ["pending", "partial", "paid", "overpaid", "overdue", "canceled"]

        for choice in valid_choices:
            self.assertIn(choice, [status.value for status in RemittanceStatus])

        # Invalid choices should not be in choices
        invalid_choices = ["invalid_status", "completed", "rejected", "draft"]

        for choice in invalid_choices:
            self.assertNotIn(choice, [status.value for status in RemittanceStatus])

    def test_remittance_status_display_values(self):
        """Test that status display values are human-readable."""
        # Check that labels are human-readable and not just the raw values
        self.assertNotEqual(
            RemittanceStatus.PENDING.label, RemittanceStatus.PENDING.value
        )
        self.assertNotEqual(
            RemittanceStatus.PARTIAL.label, RemittanceStatus.PARTIAL.value
        )
        self.assertNotEqual(
            RemittanceStatus.PAID.label, RemittanceStatus.PAID.value
        )
        self.assertNotEqual(
            RemittanceStatus.OVERPAID.label, RemittanceStatus.OVERPAID.value
        )
        self.assertNotEqual(
            RemittanceStatus.OVERDUE.label, RemittanceStatus.OVERDUE.value
        )
        self.assertNotEqual(
            RemittanceStatus.CANCELED.label, RemittanceStatus.CANCELED.value
        )

        # Check that labels have proper capitalization
        self.assertTrue(RemittanceStatus.PENDING.label[0].isupper())
        self.assertTrue(RemittanceStatus.PARTIAL.label[0].isupper())
        self.assertTrue(RemittanceStatus.PAID.label[0].isupper())
        self.assertTrue(RemittanceStatus.OVERPAID.label[0].isupper())
        self.assertTrue(RemittanceStatus.OVERDUE.label[0].isupper())
        self.assertTrue(RemittanceStatus.CANCELED.label[0].isupper())

    def test_remittance_status_choices_uniqueness(self):
        """Test that all status values and labels are unique."""
        values = [status.value for status in RemittanceStatus]
        labels = [status.label for status in RemittanceStatus]
        
        # Check that values are unique
        self.assertEqual(len(values), len(set(values)))
        
        # Check that labels are unique
        self.assertEqual(len(labels), len(set(labels)))

    def test_remittance_status_inheritance(self):
        """Test that RemittanceStatus inherits from models.TextChoices."""
        from django.db import models
        self.assertTrue(issubclass(RemittanceStatus, models.TextChoices))
