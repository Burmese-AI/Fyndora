from django.shortcuts import render

# Create your views here.
def profileTest(request):
    return render(request, "accounts/profile_test.html")