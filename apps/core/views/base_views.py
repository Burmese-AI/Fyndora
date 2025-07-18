from typing import Any
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from .mixins import HtmxModalFormInvalidFormResponseMixin

class BaseGetModalView():
    
    """
        Base class for getting modal view.
        Comptaible with:
            - Create View
            - Update View
        Required in the subclass:
            - modal_template_name
            - get_post_url()
        Optional: 
            - get_modal_title()
    """
    
    modal_template_name = None

    def get_post_url(self) -> str:
        raise NotImplementedError("You must implement get_post_url() in the subclass")

    def get_modal_title(self) -> str:
        return ""

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = None
        form = hasattr(self, "form_class")
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

class BaseGetModalFormView(
    BaseGetModalView, 
    HtmxModalFormInvalidFormResponseMixin
):
    form_class = None