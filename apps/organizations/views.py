from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from apps.organizations.models import Organization

# Create your views here.


class HomeView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/home.html"
    context_object_name = "organizations"

    #After created OrgnaizationMember table , i will display the organizations that the user is a member of
    


