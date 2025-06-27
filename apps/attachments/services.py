from django.contrib import messages
from .models import Attachment

def delete_attachment_logic(attachment_id, request):
    
    try:
        attachment = Attachment.objects.select_related('entry').get(pk=attachment_id)
    except Attachment.DoesNotExist:
        messages.error(request, "Attachment not found.")
        return False, None
    
    attachments = attachment.entry.attachments.all()
    
    if attachments.count() == 1:
        messages.error(request, "You cannot delete the last attachment")
        return False, None

    try:
        attachment.delete()
        messages.success(request, f"Attachment, {attachment.file_url}, deleted successfully")
    except Exception as e:
        messages.error(request, "Failed to delete attachment.")
        return False, None

    return True, attachments