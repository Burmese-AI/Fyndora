from django import forms
from .models import Organization
from .constants import StatusChoices


class OrganizationForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "Contact Name",
            }
        )
    )

    description = forms.CharField(
        widget=forms.EmailInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "Email Address",
            }
        )
    )

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full",
            }
        )
    )

    class Meta:
        model = Organization
        fields = ("title", "description", "status")