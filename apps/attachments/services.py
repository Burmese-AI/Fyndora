from django.contrib import messages
from .models import Attachment
from .constants import AttachmentType



def delete_attachment(attachment_id, request):
    try:
        attachment = Attachment.objects.select_related("entry").get(pk=attachment_id)
    except Attachment.DoesNotExist:
        messages.error(request, "Attachment not found.")
        return False, None

    attachments = attachment.entry.attachments.all()

    if attachments.count() == 1:
        messages.error(request, "You cannot delete the last attachment")
        return False, None

    try:
        attachment.delete()
        messages.success(
            request, f"Attachment, {attachment.file_url}, deleted successfully"
        )
    except Exception:
        messages.error(request, "Failed to delete attachment.")
        return False, None

    return True, attachments



def replace_or_append_attachments(
    *,
    entry,
    attachments,
    replace_attachments: bool,
):
    if replace_attachments:
        # Soft delete all existing attachments
        entry.attachments.all().delete()
    # Create New Attachments linked to the Entry
    for file in attachments:
        file_type = AttachmentType.get_file_type_by_extension(file.name)
        Attachment.objects.create(
            entry=entry,
            file_url=file,
            file_type=file_type or AttachmentType.OTHER,
        )


def create_attachments(*, entry, attachments):
    # Create New Attachments linked to the Entry
    prepared_attachments = [
        Attachment(
            entry=entry,
            file_url=attachment,
            file_type=AttachmentType.get_file_type_by_extension(attachment.name)
            or AttachmentType.OTHER,
        )
        for attachment in attachments
    ]

    # Bulk Create the Attachments
    Attachment.objects.bulk_create(prepared_attachments)

    return prepared_attachments

