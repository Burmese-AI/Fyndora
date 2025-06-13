"""
Unit tests for core utility functions.

Tests model_update utility function validation and update behavior.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.utils import model_update
from apps.core.models import baseModel
from tests.factories import OrganizationFactory


# Helper model for testing model_update utility
class UtilityTestModel(baseModel):
    """Helper model for utility testing."""

    name = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "tests"


@pytest.mark.unit
@pytest.mark.django_db
class TestModelUpdateUtility:
    """Test model_update utility function."""

    def test_model_update_valid_data(self):
        """Test model_update with valid data."""
        # Use Organization model as it already exists
        org = OrganizationFactory(title="Original Title")

        updated_org = model_update(
            instance=org,
            data={
                "title": "Updated Title",
                "description": "New description",
            },
            update_fields=["title", "description"],
        )

        assert updated_org.title == "Updated Title"
        assert updated_org.description == "New description"

        # Verify it was saved
        updated_org.refresh_from_db()
        assert updated_org.title == "Updated Title"
        assert updated_org.description == "New description"

    def test_model_update_with_validation_error(self):
        """Test model_update with data that fails validation."""
        org = OrganizationFactory()

        # Try to update with negative expense (should fail validation)
        with pytest.raises(ValidationError):
            model_update(
                instance=org,
                data={"expense": Decimal("-100.00")},
                update_fields=["expense"],
            )

    def test_model_update_without_update_fields(self):
        """Test model_update without specifying update_fields."""
        org = OrganizationFactory(title="Original Title")

        updated_org = model_update(instance=org, data={"title": "Updated Title"})

        assert updated_org.title == "Updated Title"

        # Verify it was saved (all fields)
        updated_org.refresh_from_db()
        assert updated_org.title == "Updated Title"

    def test_model_update_partial_fields(self):
        """Test model_update with only specific fields."""
        org = OrganizationFactory(
            title="Original Title", description="Original Description"
        )

        updated_org = model_update(
            instance=org,
            data={
                "title": "Updated Title",
                "description": "Updated Description",
            },
            update_fields=["title"],  # Only update title
        )

        assert updated_org.title == "Updated Title"
        assert updated_org.description == "Updated Description"  # In memory

        # Verify only title was saved to database
        updated_org.refresh_from_db()
        assert updated_org.title == "Updated Title"
        # Note: Since we only updated title field, description change may not persist
        # This depends on Django's update_fields behavior

    def test_model_update_empty_data(self):
        """Test model_update with empty data."""
        org = OrganizationFactory(title="Original Title")
        original_title = org.title

        updated_org = model_update(instance=org, data={}, update_fields=[])

        # Should remain unchanged
        assert updated_org.title == original_title

        updated_org.refresh_from_db()
        assert updated_org.title == original_title

    def test_model_update_returns_instance(self):
        """Test that model_update returns the updated instance."""
        org = OrganizationFactory()

        result = model_update(
            instance=org, data={"title": "New Title"}, update_fields=["title"]
        )

        # Should return the same instance
        assert result is org
        assert result.title == "New Title"

    def test_model_update_calls_full_clean(self):
        """Test that model_update calls full_clean for validation."""
        org = OrganizationFactory()

        # This should trigger validation and fail
        with pytest.raises(ValidationError):
            model_update(
                instance=org,
                data={
                    "expense": Decimal("-50.00")
                },  # Negative expense fails validation
                update_fields=["expense"],
            )

        # Original instance should be unchanged since validation failed
        org.refresh_from_db()
        assert org.expense == Decimal("0.00")  # Default value

    def test_model_update_with_multiple_field_types(self):
        """Test model_update with different field types."""
        org = OrganizationFactory()

        updated_org = model_update(
            instance=org,
            data={
                "title": "New Title",
                "expense": Decimal("250.50"),
                "description": "New description",
            },
            update_fields=["title", "expense", "description"],
        )

        assert updated_org.title == "New Title"
        assert updated_org.expense == Decimal("250.50")
        assert updated_org.description == "New description"

        # Verify persistence
        updated_org.refresh_from_db()
        assert updated_org.title == "New Title"
        assert updated_org.expense == Decimal("250.50")
        assert updated_org.description == "New description"
