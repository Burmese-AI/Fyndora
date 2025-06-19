"""
Unit tests for the core app models.

Following the test plan: Core App (apps.core)
- baseModel Tests
  - Test automatic timestamp fields (created_at, updated_at)
  - Test model inheritance
"""

import pytest
from django.test import TestCase, TransactionTestCase
from django.db import models, connection

from apps.core.models import baseModel


# Create a concrete test model to test the abstract baseModel
class CoreTestModel(baseModel):
    """Concrete model for testing baseModel functionality."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


@pytest.mark.unit
class TestBaseModel(TestCase):
    """Test the baseModel abstract model - only essential functionality."""

    def test_basemodel_is_abstract(self):
        """Test that baseModel is properly configured as abstract."""
        self.assertTrue(baseModel._meta.abstract)

    def test_basemodel_has_correct_timestamp_fields(self):
        """Test that baseModel has properly configured timestamp fields."""
        created_field = baseModel._meta.get_field("created_at")
        updated_field = baseModel._meta.get_field("updated_at")

        # Check field types and configuration
        self.assertIsInstance(created_field, models.DateTimeField)
        self.assertIsInstance(updated_field, models.DateTimeField)
        self.assertTrue(created_field.auto_now_add)
        self.assertTrue(updated_field.auto_now)


@pytest.mark.unit
class TestBaseModelTimestamps(TransactionTestCase):
    """Test baseModel timestamp behavior with dynamic table creation."""

    # Mark as django_db to ensure DB access and create tables for test models
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create table for test model
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(CoreTestModel)

    @classmethod
    def tearDownClass(cls):
        # Drop table for test model
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(CoreTestModel)
        super().tearDownClass()

    @pytest.mark.django_db
    def test_timestamp_behavior_works(self):
        """Test that timestamp fields work correctly in concrete models."""
        # Create instance
        instance = CoreTestModel.objects.create(name="Test")

        # Verify timestamps are set
        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.updated_at)

        # Verify update behavior
        original_created = instance.created_at
        import time

        time.sleep(0.01)

        instance.name = "Updated"
        instance.save()
        instance.refresh_from_db()

        # created_at unchanged, updated_at changed
        self.assertEqual(instance.created_at, original_created)
        self.assertGreater(instance.updated_at, original_created)
