from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import DeleteView
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from apps.entries.models import Entry
from .models import Attachment

@require_http_methods(["DELETE"])
def delete_attachment(request, organization_id, entry_id, attachment_id):
    
    entry = get_object_or_404(Entry, pk=entry_id)
    
    if entry.attachments.count() == 1:
        # Leave Error Message
        return HttpResponse(status=400)

    attachment = entry.attachments.get(pk=attachment_id)
    # Soft Delete
    attachment.delete()
    #Leave Success Message
    
    #Render message with OOB
    #Partially Render the Attachment Display
    return HttpResponse(status=204)

class AttachmentDeleteView(DeleteView):
    model = Attachment
    template_name = "attachments/delete_attachment.html"
    success_url = ""
    