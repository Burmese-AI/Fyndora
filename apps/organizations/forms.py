from django import forms
from .models import Organization
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
        )
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
        if Organization.objects.filter(title=title).exists():
            raise forms.ValidationError("Organization with this title already exists.")
        return title

    class Meta:
        model = Organization
        fields = ("title", "description", "status")
