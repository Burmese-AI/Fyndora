from django.urls import path
from . import views

urlpatterns = [
    path('', views.TeamListView.as_view(), name='team_list'),
]