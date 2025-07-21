from django import forms
from .models import Organization, OrganizationExchangeRate
from .constants import StatusChoices
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.currencies.models import Currency

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


class OrganizationExchangeRateForm(forms.ModelForm):
    currency_code = forms.CharField(
        label="Currency Code",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            "placeholder": "Enter currency code (e.g., USD)",
        })
    )

    # ✅ The key fix: declare DateField with correct widget + format
    effective_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            },
            format="%Y-%m-%d"
        ),
        initial=timezone.now().date(),
    )

    class Meta:
        model = OrganizationExchangeRate
        fields = ["rate", "effective_date", "note"]
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
        }


class OrganizationExchangeRateUpdateForm(forms.ModelForm):
    class Meta:
        model = OrganizationExchangeRate
        fields = ["note"]
        widgets = {
            "note": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Optional note...",
                }
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"Init note value: {self.instance.note}")