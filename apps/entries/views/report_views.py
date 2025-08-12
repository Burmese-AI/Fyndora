from django.views.generic import TemplateView
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    HtmxOobResponseMixin
)

class EntryReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    HtmxOobResponseMixin,
    TemplateView
):
    
    template_name = "entries/overview_report_index.html"