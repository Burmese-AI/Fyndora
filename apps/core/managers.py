from django.db import models
from .querysets import SoftDeleteQuerySet


class SoftDeleteManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        # Only return objects that are not soft-deleted
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        # Return all objects, including soft-deleted ones
        return SoftDeleteQuerySet(self.model, using=self._db)


class DeletedObjectsManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        # Return only soft-deleted objects
        return SoftDeleteQuerySet(self.model, using=self._db).dead()
