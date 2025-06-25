from django.shortcuts import render


def close_modal(request):
    return render(request, "components/modal_placeholder.html")


def permission_denied_view(request):
    return render(request, "components/permission_error_page.html")