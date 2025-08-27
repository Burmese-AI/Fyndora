from typing import Any
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from .mixins import HtmxModalFormInvalidFormResponseMixin


class BaseGetModalView:
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

    # modal_template_name = None

    def get_post_url(self) -> str:
        raise NotImplementedError("You must implement get_post_url() in the subclass")

    def get_modal_title(self) -> str:
        return ""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["custom_title"] = self.get_modal_title()
        context["post_url"] = self.get_post_url()
        return context

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data()
        context["is_oob"] = False
        return render(request, self.modal_template_name, context)


class BaseGetModalFormView(BaseGetModalView, HtmxModalFormInvalidFormResponseMixin):
    form_class = None

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = None
        form_kwargs = self.get_form_kwargs()
        if hasattr(self, "instance"):
            form_kwargs["instance"] = self.instance
            print(f"base instance => {self.instance}")
        form = self.form_class(**form_kwargs)
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
