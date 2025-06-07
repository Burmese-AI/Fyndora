from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("show-text", views.show_text, name="show_text"),
]
