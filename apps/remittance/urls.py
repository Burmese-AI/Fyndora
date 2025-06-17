from django.urls import path

from .views import RemittanceConfirmPaymentView, RemittanceListView

app_name = "remittance"

urlpatterns = [
    path("<uuid:workspace_id>/", RemittanceListView.as_view(), name="remittance_list"),
    path(
        "<uuid:workspace_id>/<uuid:remittance_id>/confirm/",
        RemittanceConfirmPaymentView.as_view(),
        name="remittance_confirm_payment",
    ),
]
