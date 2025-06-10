from django.urls import path
from . import views

urlpatterns = [
    path('', views.team_list, name='team_list'),
]