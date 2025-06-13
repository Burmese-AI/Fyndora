from django.shortcuts import render

def close_modal(request):
    return render(request, "components/modal_placeholder.html")