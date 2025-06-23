from django.core.exceptions import ValidationError
import os
from .constants import AttachmentType


def validate_uploaded_files(files, *, max_size_mb=5):
    # Get a list of allowed file extensions
    allowed_exts = AttachmentType.allowed_extensions()

    for file in files:
        # Comparing byte sizes
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(f"{file.name} exceeds {max_size_mb}MB size limit.")

        # Get File Extension
        ext = os.path.splitext(file.name)[1].lower()

        if ext not in allowed_exts:
            raise ValidationError(f"{file.name} has unsupported file type: {ext}")
