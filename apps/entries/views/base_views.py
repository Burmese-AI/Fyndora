from typing import Any
from django.views.generic import ListView, CreateView, UpdateView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, DeleteView
from apps.core.constants import PAGINATION_SIZE
from ..models import Entry
from ..constants import CONTEXT_OBJECT_NAME, DETAIL_CONTEXT_OBJECT_NAME
from .mixins import (
    EntryRequiredMixin,
    HtmxModalFormInvalidFormResponseMixin,
    CreateEntryFormMixin,
    HtmxOobResponseMixin,
    UpdateEntryFormMixin,
    EntryUrlIdentifierMixin,
)


class BaseEntryListView(EntryUrlIdentifierMixin, ListView):
    model = Entry
    paginate_by = PAGINATION_SIZE
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"

    def render_to_response(
        self, context: dict[str, Any], **response_kwargs: Any
    ) -> HttpResponse:
        if self.request.htmx:
            return render(self.request, self.table_template_name, context)
        return super().render_to_response(context, **response_kwargs)


class EntryModalFormViewBase(HtmxModalFormInvalidFormResponseMixin):
    modal_template_name = None

    def get_post_url(self) -> str:
        raise NotImplementedError("You must implement get_post_url() in the subclass")

    def get_modal_title(self) -> str:
        return ""

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = None
        form = self.get_form()
        context = self.get_context_data()
        context.update(
            {
                "form": form,
                "is_oob": False,
                "custom_title": self.get_modal_title(),
                "post_url": self.get_post_url(),
            }
        )
        return render(request, self.modal_template_name, context)


class BaseEntryCreateView(
    EntryModalFormViewBase,
    CreateEntryFormMixin,
    HtmxOobResponseMixin,
    EntryUrlIdentifierMixin,
    CreateView,
):
    modal_template_name = "entries/components/create_modal.html"


class BaseEntryUpdateView(
    EntryRequiredMixin,
    EntryModalFormViewBase, 
    UpdateEntryFormMixin,
    HtmxOobResponseMixin,
    EntryUrlIdentifierMixin,
    UpdateView,
):
    modal_template_name = "entries/components/update_modal.html"

    def form_valid(self, form):
        # Update org exp entry along with attachements if provided
        from ..services import update_entry_with_attachments

        update_entry_with_attachments(
            entry=self.entry,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            status=form.cleaned_data["status"],
            reviewed_by=self.org_member,
            review_notes=form.cleaned_data["review_notes"],
            attachments=form.cleaned_data["attachment_files"],
            replace_attachments=form.cleaned_data["replace_attachments"],
        )

        messages.success(
            self.request, f"Expense entry {self.entry.pk} updated successfully"
        )
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        row_html = render_to_string(
            "entries/partials/row.html", context=base_context, request=self.request
        )

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        response = HttpResponse(f"{message_html}<table>{row_html}</table>")
        response["HX-trigger"] = "success"
        return response


class BaseEntryDeleteView(
    EntryRequiredMixin,
    HtmxOobResponseMixin,
    DeleteView,
):
    
    def get_queryset(self):
        raise NotImplementedError("You must implement get_queryset() in the subclass")

    def form_valid(self, form):
        from ..services import delete_entry
        delete_entry(self.entry)
        messages.success(self.request, f"Entry {self.entry.pk} deleted successfully")
        return self._render_htmx_success_response()
    
    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()
        from apps.core.utils import get_paginated_context
        
        entries = self.get_queryset()
        table_context = get_paginated_context(
            queryset=entries,
            context=base_context,
            object_name=CONTEXT_OBJECT_NAME,
        )
        
        table_html = render_to_string(
            "entries/partials/table.html", context=table_context, request=self.request
        )
        
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{table_html}")
        return response
    

class BaseEntryDetailView(
    LoginRequiredMixin,
    EntryRequiredMixin,
    DetailView,
):
    model = Entry
    template_name = "entries/components/detail_modal.html"
    context_object_name = DETAIL_CONTEXT_OBJECT_NAME
