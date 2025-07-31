from typing import Any
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
    DetailView,
)
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.constants import PAGINATION_SIZE
from .mixins import HtmxInvalidResponseMixin, HtmxOobResponseMixin
from django.shortcuts import render


class BaseListView(LoginRequiredMixin, HtmxOobResponseMixin, ListView):
    """
    Base class for list view.
    Required:
        - model
        - context_object_name
        - table_template_name
    """

    model = None
    context_object_name = None
    template_name = None
    table_template_name = None
    paginate_by = PAGINATION_SIZE

    def render_to_response(
        self, context: dict[str, Any], **response_kwargs: Any
    ) -> HttpResponse:
        if self.request.htmx:
            return render(self.request, self.table_template_name, context)
        return super().render_to_response(context, **response_kwargs)


class BaseCreateView(LoginRequiredMixin, HtmxOobResponseMixin, CreateView):
    model = None
    form_class = None


class BaseUpdateView(LoginRequiredMixin, HtmxOobResponseMixin, UpdateView):
    model = None
    form_class = None

    def form_valid(self, form):
        raise NotImplementedError("form_valid must be implemented")


class BaseDetailView(
    LoginRequiredMixin,
    DetailView,
):
    model = None
    template_name = None
    context_object_name = None


class BaseDeleteView(
    LoginRequiredMixin,
    HtmxInvalidResponseMixin,
    HtmxOobResponseMixin,
    DeleteView,
):
    model = None

    def get_queryset(self):
        raise NotImplementedError("get_queryset must be implemented")

    def form_valid(self, form):
        raise NotImplementedError("form_valid must be implemented")
