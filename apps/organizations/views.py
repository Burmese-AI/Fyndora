from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.


@login_required
def home(request):
    return render(request, "organizations/home.html")


def show_text(request):
    return render(request, "organizations/show_text.html")
