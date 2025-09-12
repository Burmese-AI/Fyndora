from django.contrib import messages

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.entries.utils import extract_entry_business_context

from .utils import extract_attachment_business_context
from .constants import AttachmentType
from .models import Attachment


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

    # Extract business context for audit logging
    business_context = extract_attachment_business_context(attachment)

    try:
        # Set audit context to prevent duplicate logging from signal handlers
        if request and hasattr(request, "user") and request.user.is_authenticated:
            attachment._audit_user = request.user
        
        attachment.delete()
        messages.success(
            request, f"Attachment, {attachment.file_url}, deleted successfully"
        )

        # Business logic logging: Log file operations with business context
        if request and hasattr(request, "user") and request.user.is_authenticated:
            BusinessAuditLogger.log_file_operation(
                user=request.user,
                file_obj=attachment,
                operation="delete",
                request=request,
                **business_context,
            )
        # General CRUD logging handled by signal handlers

    except Exception:
        messages.error(request, "Failed to delete attachment.")
        return False, None

    return True, attachments


def replace_or_append_attachments(
    *,
    entry,
    attachments,
    replace_attachments: bool,
    user=None,
    request=None,
):
    # Store existing attachments for audit logging if replacing
    existing_attachments = []
    if replace_attachments:
        existing_attachments = list(entry.attachments.all())
            # Set audit context for bulk deletion
        if user:
            for att in existing_attachments:
                att._audit_user = user
        # Soft delete all existing attachments
        entry.attachments.all().delete()

        # Business logic logging: Log bulk attachment removal
        if user and existing_attachments:
            entry_context = extract_entry_business_context(entry)
            BusinessAuditLogger.log_bulk_operation(
                user=user,
                operation_type="attachment_replacement_deletion",
                affected_objects=existing_attachments,
                request=request,
                replaced_count=len(existing_attachments),
                **entry_context,
            )
        # General CRUD logging handled by signal handlers

    # Create New Attachments linked to the Entry
    created_attachments = []
    for file in attachments:
        file_type = AttachmentType.get_file_type_by_extension(file.name)
        attachment = Attachment.objects.create(
            entry=entry,
            file_url=file,
            file_type=file_type or AttachmentType.OTHER,
        )
        # Set audit context to prevent duplicate logging from signal handlers
        if user:
            attachment._audit_user = user
        created_attachments.append(attachment)

        # Business logic logging: Log file operations with context
        if user:
            attachment_context = extract_attachment_business_context(attachment)
            BusinessAuditLogger.log_file_operation(
                user=user,
                file_obj=attachment,
                operation="upload",
                request=request,
                operation_context="replace_or_append",
                is_replacement=replace_attachments,
                **attachment_context,
            )
    # General CRUD logging handled by signal handlers

    return created_attachments


def create_attachments(*, entry, attachments, user=None, request=None):
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

    print(f"prepared attachments => {prepared_attachments}")
    # Set audit context for bulk creation
    if user:
        for attachment_obj in prepared_attachments:
            attachment_obj._audit_user = user
    
    # Bulk Create the Attachments
    Attachment.objects.bulk_create(prepared_attachments)

    # Business logic logging: Log bulk file operations
    if user:
        entry_context = extract_entry_business_context(entry)
        for attachment_obj in prepared_attachments:
            BusinessAuditLogger.log_file_operation(
                user=user,
                file_obj=attachment_obj,
                operation="upload",
                request=request,
                attachment_id=str(attachment_obj.attachment_id),
                operation_context="bulk_create",
                bulk_operation=True,
                total_attachments=len(prepared_attachments),
                **entry_context,
            )

    return prepared_attachments
