from django.urls import path

from .views import RemittanceListView

app_name = "remittance"

urlpatterns = [
    path("<uuid:workspace_id>/", RemittanceListView.as_view(), name="list"),
]
