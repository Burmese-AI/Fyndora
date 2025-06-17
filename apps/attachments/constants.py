from django.db import models


class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    PDF = "pdf", "PDF"
    SPREADSHEET = "spreadsheet", "Spreadsheet"
