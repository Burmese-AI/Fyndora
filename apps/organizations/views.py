from django.shortcuts import render

# Create your views here.


def home(request):
    return render(request, "organizations/home.html")

def show_text(request):
    return render(request, "organizations/show_text.html")