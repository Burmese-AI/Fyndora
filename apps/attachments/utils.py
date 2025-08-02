import os

from django.core.exceptions import ValidationError

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


def extract_attachment_business_context(attachment):
    """
    Extract business context from an attachment for audit logging.
    """
    if not attachment:
        return {}

    return {
        "attachment_id": str(attachment.attachment_id),
        "entry_id": str(attachment.entry.entry_id),
        "workspace_id": str(attachment.entry.workspace.workspace_id),
        "organization_id": str(attachment.entry.workspace.organization.organization_id),
    }
