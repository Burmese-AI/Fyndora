from django import forms
from .models import Organization, OrganizationExchangeRate
from .constants import StatusChoices
from apps.currencies.forms import BaseExchangeRateCreateForm, BaseExchangeRateUpdateForm


class OrganizationForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-input input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                "placeholder": "Enter organization title",
            }
        )
    )

    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
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
                "class": "form-select select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            }
        ),
    )

    def clean_title(self):
        title = self.cleaned_data.get("title")

        # if the instance is not adding, we are in edit mode
        if self.instance and not self.instance._state.adding:
            organization_queryset = Organization.objects.filter(title=title).exclude(
                pk=self.instance.pk
            )
        else:
            # if the instance is adding, we are in create mode
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
