from django.db import models
from django.utils import timezone
from .managers import SoftDeleteManager, AllObjectsManager, DeletedObjectsManager


class baseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Default manager: only not-deleted
    objects = SoftDeleteManager()

    # Extra managers for flexibility
    all_objects = AllObjectsManager()
    deleted_objects = DeletedObjectsManager()
    
    class Meta:
        abstract = True
        
    def delete(self, *args, **kwargs):
        """Soft delete (mark as inactive instead of actual deletion)"""
        self.deleted_at = timezone.now()
        self.save()
    
    def hard_delete(self, *args, **kwargs):
        """Permanently delete from database"""
        super().delete(*args, **kwargs)
    
    def restore(self):
        """Restore a soft-deleted instance"""
        self.deleted_at = None
        self.save()
