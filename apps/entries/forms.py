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
        fields = ["amount", "description", "currency"]
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
    
class CreateWorkspaceTeamEntryForm(BaseEntryForm):
    class Meta(BaseEntryForm.Meta):
        fields = BaseEntryForm.Meta.fields + ["entry_type"]
        widgets = {
            **BaseEntryForm.Meta.widgets,
            "entry_type": forms.Select(
                attrs={
                    "class": "select select-bordered w-full",
                    "placeholder": "Select entry type",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["entry_type"].choices = self.get_allowed_entry_types()

    def clean(self):
        cleaned_data = super().clean()

        # If today is after the end date of workspace, don't allow to create Income, Disbursement Entries
        if (
            cleaned_data["entry_type"] in [EntryType.INCOME, EntryType.DISBURSEMENT]
            and self.workspace.end_date
            and date.today() > self.workspace.end_date
        ):
            raise forms.ValidationError(
                "No more entries can be created for this workspace"
            )

        # If today is before end date of workspace, don't allow remittance entries to create
        if (
            cleaned_data["entry_type"] == EntryType.REMITTANCE
            and self.workspace.end_date
            and date.today() < self.workspace.end_date
        ):
            raise forms.ValidationError(
                "Remittance Entries are not allowed to be uploaded yet"
            )

        # Only team coordinator is allowed to create remittance entries
        if (
            cleaned_data["entry_type"] == EntryType.REMITTANCE
            and not self.is_team_coordinator
        ):
            raise forms.ValidationError(
                "You are not authorized to create remittance entries"
            )

        # Only team coordinator and submitter are allowed to upload entries
        # if (
        #     cleaned_data["entry_type"] in [EntryType.INCOME, EntryType.DISBURSEMENT]
        #     and not self.is_team_coordinator
        #     and not self.workspace_team_role == TeamMemberRole.SUBMITTER
        # ):
        #     raise forms.ValidationError(
        #         "You are not authorized to create entries for this workspace team"
        #     )

        return cleaned_data

    def get_allowed_entry_types(self):
        # If submitter, return Income, disbursement
        if self.workspace_team_role == TeamMemberRole.SUBMITTER:
            return [
                (EntryType.INCOME, "Income"),
                (EntryType.DISBURSEMENT, "Disbursement"),
            ]
        # If team coordinator, return Income, disbursement, remittance
        elif self.org_member == self.workspace_team.team.team_coordinator:
            return [
                (EntryType.INCOME, "Income"),
                (EntryType.DISBURSEMENT, "Disbursement"),
                (EntryType.REMITTANCE, "Remittance"),
            ]
        else:
            return []
    
class BaseUpdateEntryForm(BaseEntryForm):
    replace_attachments = forms.BooleanField(
        label="Replace existing attachments",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "checkbox checkbox-neutral checkbox-xs"}
        ),
    )
    
    class Meta(BaseEntryForm.Meta):
        fields = BaseEntryForm.Meta.fields + ["status", "status_note"]
        widgets = {
            **BaseEntryForm.Meta.widgets,
            "status": forms.Select(
                attrs={
                    "class": "select select-bordered w-full",
                    "placeholder": "Select status",
                    "choices": EntryStatus.choices,
                }
            ),
            "status_note": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "placeholder": "Leave notes for the status update",
                }
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = self.get_allowed_statuses(self.instance.status)
        # Don't Allow Amount, Description and Attachments to be changed if the status is not PENDING
        if self.instance.status != EntryStatus.PENDING:
            self.fields["amount"].disabled = True
            self.fields["description"].disabled = True
            self.fields["attachment_files"].disabled = True
            self.fields["replace_attachments"].disabled = True
            
    def get_allowed_statuses(self, current_status):
        transitions = {
            EntryStatus.PENDING: [
                EntryStatus.PENDING,
                EntryStatus.REVIEWED,
                EntryStatus.REJECTED,
            ],
            EntryStatus.REVIEWED: [
                EntryStatus.REVIEWED,
                EntryStatus.APPROVED,
                EntryStatus.REJECTED,
            ],
            EntryStatus.REJECTED: [
                EntryStatus.REJECTED,
                EntryStatus.PENDING,
                EntryStatus.REVIEWED,
            ],
            EntryStatus.APPROVED: [EntryStatus.APPROVED, EntryStatus.REJECTED],
        }

        allowed_statuses = transitions.get(current_status, [])

        # Convert codes into (value, label) tuples using EntryStatus.labels
        return [
            (status, dict(EntryStatus.choices)[status]) for status in allowed_statuses
        ]

class UpdateOrganizationExpenseEntryForm(BaseUpdateEntryForm):
    def clean(self):
        cleaned_data = super().clean()

        # If the user is not an org admin, raise validation error
        if not self.is_org_admin:
            raise forms.ValidationError(
                "You are not authorized to update organization expenses"
            )

        return cleaned_data
    
