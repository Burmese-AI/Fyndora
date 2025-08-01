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
    currency = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.Select(
            attrs={
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.currencies.models import Currency

        self.fields["currency"].queryset = Currency.objects.all()
        # Remove currency_code field since we're using currency instead
        if "currency_code" in self.fields:
            del self.fields["currency_code"]

    class Meta:
        model = OrganizationExchangeRate
        fields = ["currency", "rate", "effective_date", "note"]
        widgets = {
            "rate": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter exchange rate",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "note": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Optional note...",
                }
            ),
            "effective_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                },
                format="%Y-%m-%d",
            ),
        }


class OrganizationExchangeRateUpdateForm(BaseExchangeRateUpdateForm):
    rate = forms.DecimalField(
        widget=forms.NumberInput(
            attrs={
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                "placeholder": "Enter exchange rate",
                "step": "0.01",
                "min": "0.01",
            }
        ),
    )

    class Meta(BaseExchangeRateUpdateForm.Meta):
        model = OrganizationExchangeRate
        fields = ["rate", "note"]
        widgets = {
            "note": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Optional note...",
                }
            ),
        }
