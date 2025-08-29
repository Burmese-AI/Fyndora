"""
Unit tests for workspace constants.

Tests cover:
- Status choices and their values
- Context object names
- Constants validation
"""

import pytest
from django.test import TestCase
from django.db import models

from apps.workspaces.constants import (
    WORKSPACE_CONTEXT_OBJECT_NAME,
    WORKSPACE_DETAIL_CONTEXT_OBJECT_NAME,
    StatusChoices,
)


@pytest.mark.unit
class TestWorkspaceConstants(TestCase):
    """Test workspace constants."""

    def test_workspace_context_object_names(self):
        """Test that context object names are correctly defined."""
        self.assertEqual(WORKSPACE_CONTEXT_OBJECT_NAME, "workspaces")
        self.assertEqual(WORKSPACE_DETAIL_CONTEXT_OBJECT_NAME, "workspace")

        # Test that they are strings
        self.assertIsInstance(WORKSPACE_CONTEXT_OBJECT_NAME, str)
        self.assertIsInstance(WORKSPACE_DETAIL_CONTEXT_OBJECT_NAME, str)

        # Test that they are not empty
        self.assertGreater(len(WORKSPACE_CONTEXT_OBJECT_NAME), 0)
        self.assertGreater(len(WORKSPACE_DETAIL_CONTEXT_OBJECT_NAME), 0)

    def test_status_choices_inheritance(self):
        """Test that StatusChoices inherits from TextChoices."""
        self.assertTrue(issubclass(StatusChoices, models.TextChoices))

        # Test that it's a proper Django choices class
        self.assertTrue(hasattr(StatusChoices, "choices"))
        self.assertTrue(hasattr(StatusChoices, "values"))
        self.assertTrue(hasattr(StatusChoices, "names"))

    def test_status_choices_values(self):
        """Test that StatusChoices has the correct values."""
        # Test all expected statuses exist
        self.assertTrue(hasattr(StatusChoices, "ACTIVE"))
        self.assertTrue(hasattr(StatusChoices, "ARCHIVED"))
        self.assertTrue(hasattr(StatusChoices, "CLOSED"))

        # Test the actual values
        self.assertEqual(StatusChoices.ACTIVE, "active")
        self.assertEqual(StatusChoices.ARCHIVED, "archived")
        self.assertEqual(StatusChoices.CLOSED, "closed")

    def test_status_choices_labels(self):
        """Test that StatusChoices has the correct labels."""
        # Test the labels (human-readable names)
        self.assertEqual(StatusChoices.ACTIVE.label, "Active")
        self.assertEqual(StatusChoices.ARCHIVED.label, "Archived")
        self.assertEqual(StatusChoices.CLOSED.label, "Closed")

    def test_status_choices_choices_property(self):
        """Test that StatusChoices.choices returns the correct tuples."""
        expected_choices = [
            ("active", "Active"),
            ("archived", "Archived"),
            ("closed", "Closed"),
        ]

        # Test that all expected choices are present
        for expected_value, expected_label in expected_choices:
            self.assertIn((expected_value, expected_label), StatusChoices.choices)

        # Test that the length is correct
        self.assertEqual(len(StatusChoices.choices), 3)

    def test_status_choices_values_property(self):
        """Test that StatusChoices.values returns the correct values."""
        expected_values = ["active", "archived", "closed"]

        # Test that all expected values are present
        for expected_value in expected_values:
            self.assertIn(expected_value, StatusChoices.values)

        # Test that the length is correct
        self.assertEqual(len(StatusChoices.values), 3)

    def test_status_choices_names_property(self):
        """Test that StatusChoices.names returns the correct names."""
        expected_names = ["ACTIVE", "ARCHIVED", "CLOSED"]

        # Test that all expected names are present
        for expected_name in expected_names:
            self.assertIn(expected_name, StatusChoices.names)

        # Test that the length is correct
        self.assertEqual(len(StatusChoices.names), 3)

    def test_status_choices_string_representation(self):
        """Test string representation of StatusChoices values."""
        # Test that values can be used as strings
        active_status = StatusChoices.ACTIVE
        self.assertEqual(str(active_status), "active")
        self.assertEqual(active_status, "active")

        # Test comparison with strings
        self.assertTrue(active_status == "active")
        self.assertFalse(active_status == "archived")

    def test_status_choices_in_model_usage(self):
        """Test that StatusChoices can be used in model fields."""

        # Create a simple test model to verify choices work
        class TestModel(models.Model):
            status = models.CharField(
                max_length=20,
                choices=StatusChoices.choices,
                default=StatusChoices.ACTIVE,
            )

            class Meta:
                app_label = "test"

        # Test that the field has the correct choices
        status_field = TestModel._meta.get_field("status")
        self.assertEqual(status_field.choices, StatusChoices.choices)
        self.assertEqual(status_field.default, StatusChoices.ACTIVE)

    def test_status_choices_validation(self):
        """Test that StatusChoices values are valid."""
        # Test that all values are lowercase
        for value in StatusChoices.values:
            self.assertEqual(value, value.lower())

        # Test that all labels start with capital letter
        for label in [choice[1] for choice in StatusChoices.choices]:
            self.assertEqual(label[0], label[0].upper())

        # Test that values don't contain spaces
        for value in StatusChoices.values:
            self.assertNotIn(" ", value)

    def test_status_choices_completeness(self):
        """Test that StatusChoices covers all expected workspace states."""
        # These are the typical states a workspace can have
        expected_states = {
            "active": "Active",  # Workspace is currently active
            "archived": "Archived",  # Workspace is archived but preserved
            "closed": "Closed",  # Workspace is closed/completed
        }

        # Test that all expected states are present
        for expected_value, expected_label in expected_states.items():
            self.assertIn(expected_value, StatusChoices.values)
            self.assertIn(
                expected_label, [choice[1] for choice in StatusChoices.choices]
            )

    def test_status_choices_consistency(self):
        """Test that StatusChoices maintains consistency between values and labels."""
        # Test that the number of values equals the number of labels
        self.assertEqual(
            len(StatusChoices.values),
            len([choice[1] for choice in StatusChoices.choices]),
        )

        # Test that each value has a corresponding label
        for value in StatusChoices.values:
            labels = [
                choice[1] for choice in StatusChoices.choices if choice[0] == value
            ]
            self.assertEqual(
                len(labels), 1, f"Value '{value}' should have exactly one label"
            )

        # Test that each label has a corresponding value
        for choice in StatusChoices.choices:
            value, label = choice
            self.assertIn(
                value,
                StatusChoices.values,
                f"Label '{label}' should have a corresponding value",
            )
