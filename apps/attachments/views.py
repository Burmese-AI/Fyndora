from django.http import HttpResponse, FileResponse, Http404
import os
from django.views.decorators.http import require_http_methods

from apps.attachments.selectors import get_attachment
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


def download_attachment(request, attachment_id):
    attachment = get_attachment(attachment_id)
    file_path = attachment.file_url.path

    if not os.path.exists(file_path):
        raise Http404("File not found")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=os.path.basename(attachment.file_url.name),
    )
