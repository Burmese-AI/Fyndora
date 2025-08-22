from django.urls import path
from .views import remittance_list_view, remittance_confirm_payment_view


urlpatterns = [
    path("", remittance_list_view, name="remittance_list"),
    path(
        "confirm-payment/<uuid:remittance_id>/",
        remittance_confirm_payment_view,
        name="remittance_confirm_payment",
    ),
]
