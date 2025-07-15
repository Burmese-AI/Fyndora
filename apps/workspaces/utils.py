from django.contrib import messages
from django.shortcuts import redirect
from django_htmx.http import HttpResponseClientRedirect


def permission_denied_view(request, message):
    messages.error(request, message)
    if request.headers.get("HX-Request"):
        return HttpResponseClientRedirect("/403")
    else:
        return redirect("permission_denied")