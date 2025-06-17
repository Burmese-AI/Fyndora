from django.db import models
from apps.entries.models import Entry
from uuid import uuid4
from apps.core.models import baseModel
from .constants import AttachmentType


class Attachment(baseModel):
    attachment_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    entry = models.ForeignKey(
        Entry, on_delete=models.CASCADE, related_name="attachments"
    )
    file_url = models.FileField(upload_to="attachments/")
    file_type = models.CharField(max_length=20, choices=AttachmentType.choices)

    class Meta:
        verbose_name_plural = "Attachments"

    def __str__(self):
        return f"{self.file_type} - {self.file_url.name} - {self.entry.pk}"
