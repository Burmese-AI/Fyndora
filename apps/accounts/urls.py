from django.urls import path
from . import views

urlpatterns = [
    path("profile-test/", views.profileTest, name="profile-test"),
]