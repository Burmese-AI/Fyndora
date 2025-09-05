"""
Unit tests for core querysets.

Tests cover:
- SoftDeleteQuerySet methods
- QuerySet functionality for soft delete operations
"""

import pytest
from django.db import models
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.core.querysets import SoftDeleteQuerySet
from apps.core.models import SoftDeleteModel


class SoftDeleteTestModel(SoftDeleteModel):
    """Test model that uses SoftDeleteModel."""
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'core'


@pytest.mark.unit
class TestSoftDeleteQuerySet(TestCase):
    """Test SoftDeleteQuerySet functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test instances
        self.test_model1 = SoftDeleteTestModel.objects.create(name="Test 1")
        self.test_model2 = SoftDeleteTestModel.objects.create(name="Test 2")
        self.test_model3 = SoftDeleteTestModel.objects.create(name="Test 3")
        
        # Soft delete one instance
        self.test_model2.delete()  # This calls the soft delete
        
        # Get querysets
        self.queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default')

    @pytest.mark.django_db
    def test_delete_soft_delete(self):
        """Test that delete() performs soft delete."""
        # Get a fresh instance that hasn't been soft deleted
        test_model = SoftDeleteTestModel.objects.create(name="Test Delete")
        original_count = SoftDeleteTestModel.all_objects.count()
        
        # Use the queryset delete method
        queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default').filter(id=test_model.id)
        result = queryset.delete()
        
        # Verify soft delete occurred
        self.assertEqual(result, 1)  # One object was "deleted"
        self.assertEqual(SoftDeleteTestModel.all_objects.count(), original_count)  # Still exists in DB
        self.assertIsNotNone(SoftDeleteTestModel.all_objects.get(id=test_model.id).deleted_at)
        
        # Verify it's not in the regular objects queryset
        self.assertFalse(SoftDeleteTestModel.objects.filter(id=test_model.id).exists())

    @pytest.mark.django_db
    def test_hard_delete(self):
        """Test that hard_delete() performs actual deletion (covers line 10)."""
        # Get a fresh instance
        test_model = SoftDeleteTestModel.objects.create(name="Test Hard Delete")
        original_count = SoftDeleteTestModel.all_objects.count()
        
        # Use the queryset hard_delete method
        queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default').filter(id=test_model.id)
        result = queryset.hard_delete()
        
        # Verify actual deletion occurred
        self.assertEqual(result, (1, {'core.SoftDeleteTestModel': 1}))  # Django delete returns (count, {model: count})
        self.assertEqual(SoftDeleteTestModel.all_objects.count(), original_count - 1)  # Actually removed from DB
        
        # Verify it's completely gone
        self.assertFalse(SoftDeleteTestModel.all_objects.filter(id=test_model.id).exists())

    @pytest.mark.django_db
    def test_alive_filter(self):
        """Test that alive() returns only non-deleted objects."""
        alive_objects = self.queryset.alive()
        
        # Should return 2 objects (test_model1 and test_model3)
        self.assertEqual(alive_objects.count(), 2)
        
        # Verify specific objects
        alive_ids = list(alive_objects.values_list('id', flat=True))
        self.assertIn(self.test_model1.id, alive_ids)
        self.assertIn(self.test_model3.id, alive_ids)
        self.assertNotIn(self.test_model2.id, alive_ids)

    @pytest.mark.django_db
    def test_dead_filter(self):
        """Test that dead() returns only soft-deleted objects (covers line 16)."""
        dead_objects = self.queryset.dead()
        
        # Should return 1 object (test_model2)
        self.assertEqual(dead_objects.count(), 1)
        
        # Verify specific object
        dead_ids = list(dead_objects.values_list('id', flat=True))
        self.assertIn(self.test_model2.id, dead_ids)
        self.assertNotIn(self.test_model1.id, dead_ids)
        self.assertNotIn(self.test_model3.id, dead_ids)

    @pytest.mark.django_db
    def test_delete_multiple_objects(self):
        """Test delete() on multiple objects."""
        # Create additional test objects
        test_model4 = SoftDeleteTestModel.objects.create(name="Test 4")
        test_model5 = SoftDeleteTestModel.objects.create(name="Test 5")
        
        # Soft delete multiple objects
        queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default').filter(
            id__in=[test_model4.id, test_model5.id]
        )
        result = queryset.delete()
        
        # Verify both were soft deleted
        self.assertEqual(result, 2)
        
        # Verify they're soft deleted
        test_model4.refresh_from_db()
        test_model5.refresh_from_db()
        self.assertIsNotNone(test_model4.deleted_at)
        self.assertIsNotNone(test_model5.deleted_at)
        
        # Verify they're not in regular objects
        self.assertFalse(SoftDeleteTestModel.objects.filter(id__in=[test_model4.id, test_model5.id]).exists())

    @pytest.mark.django_db
    def test_hard_delete_multiple_objects(self):
        """Test hard_delete() on multiple objects."""
        # Create additional test objects
        test_model4 = SoftDeleteTestModel.objects.create(name="Test 4")
        test_model5 = SoftDeleteTestModel.objects.create(name="Test 5")
        original_count = SoftDeleteTestModel.all_objects.count()
        
        # Hard delete multiple objects
        queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default').filter(
            id__in=[test_model4.id, test_model5.id]
        )
        result = queryset.hard_delete()
        
        # Verify both were actually deleted
        self.assertEqual(result, (2, {'core.SoftDeleteTestModel': 2}))
        self.assertEqual(SoftDeleteTestModel.all_objects.count(), original_count - 2)
        
        # Verify they're completely gone
        self.assertFalse(SoftDeleteTestModel.all_objects.filter(id__in=[test_model4.id, test_model5.id]).exists())

    @pytest.mark.django_db
    def test_alive_and_dead_chain(self):
        """Test chaining alive() and dead() methods."""
        # Test alive() on queryset with mixed objects
        all_objects = SoftDeleteQuerySet(SoftDeleteTestModel, using='default')
        alive_count = all_objects.alive().count()
        dead_count = all_objects.dead().count()
        
        self.assertEqual(alive_count, 2)  # test_model1 and test_model3
        self.assertEqual(dead_count, 1)   # test_model2

    @pytest.mark.django_db
    def test_queryset_with_filters(self):
        """Test queryset methods work with additional filters."""
        # Test alive() with name filter
        alive_objects = self.queryset.alive().filter(name="Test 1")
        self.assertEqual(alive_objects.count(), 1)
        self.assertEqual(alive_objects.first().name, "Test 1")
        
        # Test dead() with name filter
        dead_objects = self.queryset.dead().filter(name="Test 2")
        self.assertEqual(dead_objects.count(), 1)
        self.assertEqual(dead_objects.first().name, "Test 2")

    @pytest.mark.django_db
    def test_empty_queryset_operations(self):
        """Test operations on empty querysets."""
        # Test delete on empty queryset
        empty_queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default').filter(name="NonExistent")
        result = empty_queryset.delete()
        self.assertEqual(result, 0)
        
        # Test hard_delete on empty queryset
        result = empty_queryset.hard_delete()
        self.assertEqual(result, (0, {}))
        
        # Test alive() on empty queryset
        alive_count = empty_queryset.alive().count()
        self.assertEqual(alive_count, 0)
        
        # Test dead() on empty queryset
        dead_count = empty_queryset.dead().count()
        self.assertEqual(dead_count, 0)

    @pytest.mark.django_db
    def test_queryset_inheritance(self):
        """Test that SoftDeleteQuerySet properly inherits from QuerySet."""
        # Test that it has QuerySet methods
        queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default')
        
        # Test basic QuerySet functionality
        self.assertTrue(hasattr(queryset, 'filter'))
        self.assertTrue(hasattr(queryset, 'exclude'))
        self.assertTrue(hasattr(queryset, 'order_by'))
        self.assertTrue(hasattr(queryset, 'values'))
        self.assertTrue(hasattr(queryset, 'count'))
        
        # Test that our custom methods are present
        self.assertTrue(hasattr(queryset, 'delete'))
        self.assertTrue(hasattr(queryset, 'hard_delete'))
        self.assertTrue(hasattr(queryset, 'alive'))
        self.assertTrue(hasattr(queryset, 'dead'))

    @pytest.mark.django_db
    def test_soft_delete_timestamp(self):
        """Test that soft delete sets the correct timestamp."""
        test_model = SoftDeleteTestModel.objects.create(name="Test Timestamp")
        before_delete = timezone.now()
        
        # Soft delete
        queryset = SoftDeleteQuerySet(SoftDeleteTestModel, using='default').filter(id=test_model.id)
        queryset.delete()
        
        after_delete = timezone.now()
        
        # Check timestamp
        test_model.refresh_from_db()
        self.assertIsNotNone(test_model.deleted_at)
        self.assertGreaterEqual(test_model.deleted_at, before_delete)
        self.assertLessEqual(test_model.deleted_at, after_delete)
