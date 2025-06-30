from django.views.generic import ListView, CreateView, UpdateView
from ..models import Entry
from apps.core.constants import PAGINATION_SIZE
from ..constants import CONTEXT_OBJECT_NAME
from .base import HtmxModalFormInvalidFormResponseMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing import Any

class BaseEntryListView(ListView):
    model = Entry
    paginate_by = PAGINATION_SIZE
    context_object_name = CONTEXT_OBJECT_NAME
    
    
class BaseEntryCreateView(HtmxModalFormInvalidFormResponseMixin, CreateView):
    modal_template_name = "entries/components/create_modal.html"
    
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = None
        form = self.get_form()
        context = self.get_context_data()
        context["form"] = form
        context["is_oob"] = (
            False  # Overriding the default value from HtmxOobResponseMixin context data
        )
        return render(request, self.modal_template_name, context)
    
class BaseEntryUpdateView(HtmxModalFormInvalidFormResponseMixin, UpdateView):
    modal_template_name = "entries/components/update_modal.html"
    
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = None
        form = self.get_form()
        context = self.get_context_data()
        context["form"] = form
        context["is_oob"] = (
            False  # Overriding the default value from HtmxOobResponseMixin context data
        )
        return render(request, self.modal_template_name, context)
