from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages

class HtmxCreateServiceMixin:
    context_object_name = None
    table_template_name = None

    def get_queryset(self):
        raise NotImplementedError("get_queryset() must be implemented")

    def perform_create_service(self, form):
        """
        Override this to run your service logic.
        Should raise Exception if something goes wrong.
        """
        raise NotImplementedError("perform_create_service() must be implemented")

    def get_partial_templates(self, context) -> list[tuple[str, dict]]:
        """
        Optionally return additional templates to render as part of the success response.
        Should return a list of (template_path, context) tuples.
        """
        return []

    def form_valid(self, form):
        try:
            print("============ FORM VALID ====")
            self.perform_create_service(form)
        except Exception as e:
            messages.error(self.request, str(e))
            return self._render_htmx_error_response(form)

        messages.success(self.request, "Entry created successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()
        extra_html = ""

        # Optional partial templates rendering
        for template_path, context in self.get_partial_templates(base_context):
            extra_html += render_to_string(template_path, context=context, request=self.request)

        from apps.core.utils import get_paginated_context

        queryset = self.get_queryset()
        table_context = get_paginated_context(
            queryset=queryset,
            context=base_context,
            object_name=self.context_object_name,
        )

        table_html = render_to_string(
            self.table_template_name, context=table_context, request=self.request
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        response = HttpResponse(f"{message_html}{extra_html}{table_html}")
        response["HX-trigger"] = "success"
        return response
