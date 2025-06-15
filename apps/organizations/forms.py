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
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea-bordered w-full",
                "placeholder": "Description",
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

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if Organization.objects.filter(title=title).exists():
            raise forms.ValidationError("Organization with this title already exists.")
        return title

    class Meta:
        model = Organization
        fields = ("title", "description", "status")