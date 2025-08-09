from django.urls import path
from .views import remittance_list_view


urlpatterns = [
    path("", remittance_list_view, name="remittance_list"),
]
