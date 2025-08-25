"""
Unit tests for core utility functions.

Tests model_update utility function validation and update behavior.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.utils import model_update
from apps.entries.models import Entry
from tests.factories import EntryFactory
from django.test import RequestFactory
from apps.core.utils import permission_denied_view
from django.http import HttpResponse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect



@pytest.mark.unit
@pytest.mark.django_db
#initially, ko swam used org models to test the decimal field by using the expense field of the org model.However , as we removed the expense field from the org model, we are using the entry model to test the decimal field.
class TestModelUpdateUtility:
    """Test model_update utility function."""

    def test_model_update_valid_data(self):
        """Test model_update with valid data."""
        # Use Entry model as it already exists with decimal fields
        test_model = EntryFactory(amount=Decimal("100.00"))

        updated_model = model_update(
            instance=test_model,
            data={
                "description": "Updated Description",
                "amount": Decimal("200.00"),
            },
            update_fields=["description", "amount"],
        )

        assert updated_model.description == "Updated Description"
        assert updated_model.amount == Decimal("200.00")

        # Verify it was saved
        updated_model.refresh_from_db()
        assert updated_model.description == "Updated Description"
        assert updated_model.amount == Decimal("200.00")

    def test_model_update_with_validation_error(self):
        """Test model_update with data that fails validation."""
        test_model = EntryFactory(amount=Decimal("100.00"))

        # Try to update with negative amount (should fail validation)
        with pytest.raises(ValidationError):
            model_update(
                instance=test_model,
                data={"amount": Decimal("-100.00")},
                update_fields=["amount"],
            )

    def test_model_update_without_update_fields(self):
        """Test model_update without specifying update_fields."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        updated_model = model_update(instance=test_model, data={"description": "Updated Description"})

        assert updated_model.description == "Updated Description"

        # Verify it was saved (all fields)
        updated_model.refresh_from_db()
        assert updated_model.description == "Updated Description"

    def test_model_update_partial_fields(self):
        """Test model_update with only specific fields."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        updated_model = model_update(
            instance=test_model,
            data={
                "description": "Updated Description",
                "amount": Decimal("200.00"),
            },
            update_fields=["description"],  # Only update description
        )

        assert updated_model.description == "Updated Description"
        assert updated_model.amount == Decimal("200.00")  # In memory

        # Verify only description was saved to database
        updated_model.refresh_from_db()
        assert updated_model.description == "Updated Description"
        # Note: Since we only updated description field, amount change may not persist
        # This depends on Django's update_fields behavior

    def test_model_update_empty_data(self):
        """Test model_update with empty data."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))
        original_description = test_model.description

        updated_model = model_update(instance=test_model, data={}, update_fields=[])

        # Should remain unchanged
        assert updated_model.description == original_description

        updated_model.refresh_from_db()
        assert updated_model.description == original_description

    def test_model_update_returns_instance(self):
        """Test that model_update returns the updated instance."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        result = model_update(
            instance=test_model, data={"description": "New Description"}, update_fields=["description"]
        )

        # Should return the same instance
        assert result is test_model
        assert result.description == "New Description"

    def test_model_update_calls_full_clean(self):
        """Test that model_update calls full_clean for validation."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        # This should trigger validation and fail
        with pytest.raises(ValidationError):
            model_update(
                instance=test_model,
                data={
                    "amount": Decimal("-50.00")
                },  # Negative amount fails validation
                update_fields=["amount"],
            )

        # Original instance should be unchanged since validation failed
        test_model.refresh_from_db()
        assert test_model.amount == Decimal("100.00")  # Original value

    def test_model_update_with_multiple_field_types(self):
        """Test model_update with different field types."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        updated_model = model_update(
            instance=test_model,
            data={
                "description": "New Description",
                "amount": Decimal("250.50"),
                "is_flagged": True,
            },
            update_fields=["description", "amount", "is_flagged"],
        )

        assert updated_model.description == "New Description"
        assert updated_model.amount == Decimal("250.50")
        assert updated_model.is_flagged == True

        # Verify persistence
        updated_model.refresh_from_db()
        assert updated_model.description == "New Description"
        assert updated_model.amount == Decimal("250.50")
        assert updated_model.is_flagged == True






