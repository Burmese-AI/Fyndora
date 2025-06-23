from django import forms
from .models import Entry
from apps.core.forms import MultipleFileField, MultipleFileInput
from apps.attachments.utils import validate_uploaded_files


class OrganizationExpenseEntryForm(forms.ModelForm):
    attachment_files = MultipleFileField(
        label="Attachments",
        required=True,
        widget=MultipleFileInput(
            attrs={
                "class": "file-input file-input-neutral w-full text-sm",
            }
        ),
    )

    class Meta:
        model = Entry
        fields = ["amount", "description", "attachment_files"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter amount (e.g., 25.99)",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Brief description of the expense",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        print("Full kwargs received:", kwargs)  # 👈 Debugging line
        self.org_member = kwargs.pop("org_member", None)
        self.organization = kwargs.pop("organization", None)
        self.is_update = kwargs.pop("is_update", False)
        super().__init__(*args, **kwargs)
        self.fields["attachment_files"].required = not self.is_update
        print(f"Is Update Mode: {self.is_update}")
        print(f"Attachment Required: {self.fields['attachment_files'].required}")

    def clean(self):
        cleaned_data = super().clean()

        # If org member is None, raise validation error
        if not self.org_member:
            raise forms.ValidationError(
                "The current user is not a member of the organization"
            )

        # If the org member object is not the same as the owner object of the provided organization, raise validation error
        if not self.org_member.is_org_owner:
            raise forms.ValidationError(
                "Only the owner of the organization can submit expenses."
            )
            
        validate_uploaded_files(cleaned_data.get("attachment_files"))

        return cleaned_data
