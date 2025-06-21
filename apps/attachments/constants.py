from django.db import models
import os


class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    PDF = "pdf", "PDF"
    SPREADSHEET = "spreadsheet", "Spreadsheet"

    @classmethod
    def get_extension_map(cls):
        return {
            cls.IMAGE: [".jpg", ".jpeg", ".png"],
            cls.PDF: [".pdf"],
            cls.SPREADSHEET: [".xls", ".xlsx", ".csv"],
        }

    @classmethod
    def get_file_type_by_extension(cls, filename):
        ext = os.path.splitext(filename)[1].lower()
        extension_map = cls.get_extension_map()
        for file_type, ext_list in extension_map.items():
            if ext in ext_list:
                return file_type
        return None

    @classmethod
    def allowed_extensions(cls):
        extension_map = cls.get_extension_map()
        return [ext for ext_list in extension_map.values() for ext in ext_list]
