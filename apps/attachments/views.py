from django.http import HttpResponse
from django.views.generic import DeleteView
from django.views.decorators.http import require_http_methods
from .models import Attachment
from django.template.loader import render_to_string
from django.contrib.messages import get_messages

from .services import delete_attachment


@require_http_methods(["DELETE"])
def delete_attachment_view(request, attachment_id):
    success, attachments = delete_attachment(attachment_id, request)
    context = {"is_oob": True, "messages": get_messages(request)}
    attachment_html = ""

    if success:
        success_context = {
            **context,
            "attachments": attachments,
        }
        attachment_html = render_to_string(
            "attachments/partials/table.html", context=success_context, request=request
        )

    # Render attachment table and message with OOB
    message_html = render_to_string(
        "includes/message.html", context=context, request=request
    )
    response = HttpResponse(f"{message_html}{attachment_html}")

    return response


class AttachmentDeleteView(DeleteView):
    model = Attachment
    template_name = "attachments/delete_attachment.html"
    success_url = ""
