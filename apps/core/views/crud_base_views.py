from typing import Any
from django.views.generic import CreateView, ListView, UpdateView
from django.http import HttpResponse
from apps.core.constants import PAGINATION_SIZE
from .mixins import HtmxOobResponseMixin

class BaseListView(ListView):
    """
        Base class for list view.
        Required:
            - model
            - context_object_name
            - table_template_name
    """
    model = None
    context_object_name = None
    table_template_name = None
    paginate_by = PAGINATION_SIZE

    def render_to_response(
        self, context: dict[str, Any], **response_kwargs: Any
    ) -> HttpResponse:
        if self.request.htmx:
            return render(self.request, self.table_template_name, context)
        return super().render_to_response(context, **response_kwargs)
    
class BaseCreateView(HtmxOobResponseMixin, CreateView):
    model = None
    form_class = None
    
    def form_valid(self, form):
        raise NotImplementedError("form_valid must be implemented")
    
class BaseUpdateView(HtmxOobResponseMixin, UpdateView):
    model = None
    form_class = None
    
    def form_valid(self, form):
        raise NotImplementedError("form_valid must be implemented")
    
