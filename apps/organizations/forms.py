from django import forms
from django.forms import widgets
from .models import Organization, OrganizationExchangeRate
from .constants import StatusChoices
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.currencies.models import Currency
from apps.currencies.forms import BaseExchangeRateCreateForm, BaseExchangeRateUpdateForm

class OrganizationForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                "placeholder": "Enter organization title",
            }
        )
    )

    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                "placeholder": "Enter organization description (optional)",
                "rows": 2,
            }
        ),
        required=False,
    )

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            }
        ),
    )

    def clean_title(self):
        title = self.cleaned_data.get("title")

        if self.instance and not self.instance._state.adding:
            print("EDIT MODE")
            organization_queryset = Organization.objects.filter(title=title).exclude(
                pk=self.instance.pk
            )
        else:
            print("CREATE MODE")
            organization_queryset = Organization.objects.filter(title=title)

        if organization_queryset.exists():
            raise forms.ValidationError("Organization with this title already exists.")

        return title

    class Meta:
        model = Organization
        fields = ("title", "description", "status")


class OrganizationExchangeRateCreateForm(BaseExchangeRateCreateForm):
    class Meta:
        model = OrganizationExchangeRate
        fields = BaseExchangeRateCreateForm.Meta.fields
        widgets = BaseExchangeRateCreateForm.Meta.widgets
        
class OrganizationExchangeRateUpdateForm(BaseExchangeRateUpdateForm):
    class Meta(BaseExchangeRateUpdateForm.Meta):
        model = OrganizationExchangeRate
        fields = BaseExchangeRateUpdateForm.Meta.fields
        widgets = BaseExchangeRateUpdateForm.Meta.widgets
   