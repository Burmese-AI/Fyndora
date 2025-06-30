from django import forms
from .models import Entry
from apps.core.forms import MultipleFileField, MultipleFileInput
from apps.attachments.utils import validate_uploaded_files
from .constants import EntryStatus
from pprint import pprint

class BaseEntryForm(forms.ModelForm):
    attachment_files = MultipleFileField(
        label="Attachments",
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "file-input file-input-neutral w-full text-sm",
            }
        ),
    )
    
    class Meta:
        model = Entry
        fields = ["amount", "description"]
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
        self.org_member = kwargs.pop("org_member", None)
        self.organization = kwargs.pop("organization", None)
        # Initializes all the form fields from the model or declared fields to modify them
        super().__init__(*args, **kwargs)
        
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
            
        print(f"debugging: {cleaned_data}")

        attachment_files = cleaned_data.get("attachment_files")
        if attachment_files:
            validate_uploaded_files(attachment_files)

        return cleaned_data
    
class CreateEntryForm(BaseEntryForm):
    pass

class UpdateEntryForm(BaseEntryForm):
    replace_attachments = forms.BooleanField(
        label="Replace existing attachments",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "checkbox checkbox-neutral checkbox-xs"}
        ),
    )
    
    class Meta(BaseEntryForm.Meta):
        fields = BaseEntryForm.Meta.fields + ["status", "review_notes"]
        widgets = {
            **BaseEntryForm.Meta.widgets,
            "status": forms.Select(
                attrs={
                    "class": "select select-bordered w-full",
                    "placeholder": "Select status",
                    "choices": EntryStatus.choices,
                }
            ),
            "review_notes": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "placeholder": "Leave notes for the status update",
                }
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = self.get_allowed_statuses(self.instance.status)
        # Don't Allow Amount, Description and Attachments to be changed if the status is not PENDING_REVIEW
        if self.instance.status != EntryStatus.PENDING_REVIEW:
            self.fields["amount"].disabled = True
            self.fields["description"].disabled = True
            self.fields["attachment_files"].disabled = True
            self.fields["replace_attachments"].disabled = True

        
    def get_allowed_statuses(self, current_status):
        transitions = {
            EntryStatus.PENDING_REVIEW: [EntryStatus.PENDING_REVIEW, EntryStatus.REVIEWED, EntryStatus.REJECTED],
            EntryStatus.REVIEWED: [EntryStatus.REVIEWED, EntryStatus.APPROVED, EntryStatus.REJECTED],
            EntryStatus.REJECTED: [EntryStatus.REJECTED, EntryStatus.PENDING_REVIEW, EntryStatus.REVIEWED],
            EntryStatus.APPROVED: [EntryStatus.APPROVED, EntryStatus.REJECTED],
        }

        allowed_statuses = transitions.get(current_status, [])

        # Convert codes into (value, label) tuples using EntryStatus.labels
        return [
            (status, dict(EntryStatus.choices)[status]) for status in allowed_statuses
        ]
        
    
                