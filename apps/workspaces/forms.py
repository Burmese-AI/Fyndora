from django import forms
from .models import Workspace
from apps.organizations.models import OrganizationMember


class WorkspaceForm(forms.ModelForm):

    workspace_admin = forms.ModelChoiceField(
        queryset=OrganizationMember.objects.none(), 
        label='Select Workspace Admin',
        widget=forms.Select(
            attrs={"class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base"}
        )
    )
    class Meta:
        model = Workspace
        fields = [
            "title",
            "description",
            "status",
            "remittance_rate",
            "start_date",
            "end_date",
            "workspace_admin",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter workspace title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base min-h-[60px]",
                    "rows": 2,
                    "placeholder": "Describe your workspace (optional)",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                }
            ),
            "remittance_rate": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter remittance rate (0-100)",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "type": "date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization:
            self.fields['workspace_admin'].queryset = OrganizationMember.objects.filter(organization=organization, is_active=True)

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title.strip():
            raise forms.ValidationError("Title cannot be blank or only whitespace.")
        return title

    def clean_remittance_rate(self):
        remittance_rate = self.cleaned_data.get("remittance_rate")
        if remittance_rate < 0 or remittance_rate > 100:
            raise forms.ValidationError("Remittance rate must be between 0 and 100.")
        return remittance_rate

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be earlier than start date.")

        return cleaned_data
