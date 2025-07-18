from django import forms
from .models import Organization, OrganizationExchangeRate
from .constants import StatusChoices


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
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                "placeholder": "Enter currency code",
            }
        )
    )
    
    class Meta:
        model = OrganizationExchangeRate
        fields = ["rate", "effective_date", "note"]
        widgets = {
            "rate": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter exchange rate",
                }
            ),
            "effective_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter effective date",
                }
            ),
            "note": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter note (optional)",
                }
            ),
        }
    