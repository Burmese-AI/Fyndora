from django import forms
from .models import Entry
from apps.core.forms import MultipleFileField, MultipleFileInput
from apps.attachments.utils import validate_uploaded_files
from .constants import EntryStatus, EntryType
from apps.teams.constants import TeamMemberRole
from datetime import date
from pprint import pprint
from apps.currencies.models import Currency
from apps.organizations.models import OrganizationExchangeRate
from django.utils import timezone

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
    
    currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        required=True,
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full",
                "placeholder": "Select Currency",
            }
        ),
    )
    
    occurred_at = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            },
        ),
        initial=timezone.now().date,
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
                    "required": True,
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Brief description of the expense",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # print("+++++++++++++ DEBUGGING +++++++++++++")
        # pprint(kwargs)
        self.org_member = kwargs.pop("org_member", None)
        self.organization = kwargs.pop("organization", None)
        self.workspace = kwargs.pop("workspace", None)
        self.workspace_team = kwargs.pop("workspace_team", None)
        self.workspace_team_role = kwargs.pop("workspace_team_role", None)
        self.workspace_team_member = kwargs.pop("workspace_team_member", None)
        self.is_org_admin = kwargs.pop("is_org_admin", None)
        self.is_workspace_admin = kwargs.pop("is_workspace_admin", None)
        self.is_operation_reviewer = kwargs.pop("is_operation_reviewer", None)
        self.is_team_coordinator = kwargs.pop("is_team_coordinator", None)
        # Initializes all the form fields from the model or declared fields to modify them
        super().__init__(*args, **kwargs)
        # Set the queryset for the currency field to only include currencies defined for the organization
        self.fields["currency"].queryset = self.get_org_defined_currencies()

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate Currency
        currency = cleaned_data.get("currency")
        if not currency:
            raise forms.ValidationError("Currency is required.")
                
        # Validate attachment files
        attachment_files = cleaned_data.get("attachment_files")
        if attachment_files:
            validate_uploaded_files(attachment_files)

        return cleaned_data
    
    def get_org_defined_currencies(self):
        return Currency.objects.filter(
            organizations_organizationexchangerate__organization=self.organization,
        )
    
class CreateOrganizationExpenseEntryForm(BaseEntryForm):
    def clean(self):
        cleaned_data = super().clean()
        if not self.is_org_admin:
            raise forms.ValidationError(
                "You are not authorized to create organization expenses"
            )
        return cleaned_data