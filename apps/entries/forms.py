import os
from django import forms
from .models import Entry
from apps.core.forms import MultipleFileField, MultipleFileInput
from apps.attachments.utils import validate_uploaded_files
from .constants import EntryStatus, EntryType
from apps.teams.constants import TeamMemberRole
from apps.currencies.models import Currency
from apps.currencies.selectors import get_org_defined_currencies
from .validators import TeamEntryValidator


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

    class Meta:
        model = Entry
        fields = ["amount", "description", "currency", "occurred_at"]
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
            "occurred_at": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "required": True,
                },
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
        self.fields["currency"].queryset = get_org_defined_currencies(self.organization)

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
        self.validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=self.workspace_team_role,
            is_org_admin=self.is_org_admin,
            is_workspace_admin=self.is_workspace_admin,
            is_operation_reviewer=self.is_operation_reviewer,
            is_team_coordinator=self.is_team_coordinator,
        )

    def clean(self):
        cleaned_data = super().clean()

        occurred_at = cleaned_data.get("occurred_at")
        entry_type = cleaned_data.get("entry_type")
        try:
            self.validator.validate_entry_create(entry_type, occurred_at)
        except Exception as e:
            raise forms.ValidationError(e)

        return cleaned_data

    def get_allowed_entry_types(self):
        # If team coordinator, return Income, disbursement, remittance
        if self.is_org_admin or self.is_team_coordinator:
            return [
                (EntryType.INCOME, "Income"),
                (EntryType.DISBURSEMENT, "Disbursement"),
                (EntryType.REMITTANCE, "Remittance"),
            ]

        # If submitter, return Income, disbursement
        elif self.workspace_team_role == TeamMemberRole.SUBMITTER:
            return [
                (EntryType.INCOME, "Income"),
                (EntryType.DISBURSEMENT, "Disbursement"),
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
        # Get allowed statuses
        self.fields["status"].choices = self.get_allowed_statuses()
        # Don't Allow Amount, Description and Attachments to be changed if the status is not PENDING
        if self.instance.status != EntryStatus.PENDING:
            self.fields["amount"].disabled = True
            self.fields["description"].disabled = True
            self.fields["attachment_files"].disabled = True
            self.fields["replace_attachments"].disabled = True
            self.fields["currency"].disabled = True
            self.fields["occurred_at"].disabled = True
        # Disable status and status note
        # for submitter
        # for TC on remittance entry type
        if (self.workspace_team_role == TeamMemberRole.SUBMITTER) or (
            self.is_team_coordinator
            and self.instance.entry_type == EntryType.REMITTANCE
        ):
            self.fields["status"].disabled = True
            self.fields["status_note"].disabled = True

    def get_allowed_statuses(self):
        # OA, WA, OR => ALL STATUSES
        if self.is_org_admin or self.is_workspace_admin or self.is_operation_reviewer:
            allowed_statuses = EntryStatus.values
        # TC => PENDING, REVIEWED, REJECTED
        elif self.is_team_coordinator:
            allowed_statuses = [
                EntryStatus.PENDING,
                EntryStatus.REVIEWED,
                EntryStatus.REJECTED,
            ]
        # Others => None
        else:
            allowed_statuses = []

        # Convert codes into (value, label) tuples using EntryStatus.labels
        return [
            (status, dict(EntryStatus.choices)[status]) for status in allowed_statuses
        ]


class UpdateWorkspaceTeamEntryForm(BaseUpdateEntryForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=self.workspace_team_role,
            is_org_admin=self.is_org_admin,
            is_workspace_admin=self.is_workspace_admin,
            is_operation_reviewer=self.is_operation_reviewer,
            is_team_coordinator=self.is_team_coordinator,
        )

    def clean(self):
        cleaned_data = super().clean()

        new_status = cleaned_data.get("status")
        occurred_at = cleaned_data.get("occurred_at")

        try:
            self.validator.validate_entry_update(
                entry=self.instance,
                new_status=new_status,
                occurred_at=occurred_at,
            )
        except Exception as e:
            raise forms.ValidationError(e)

        return cleaned_data


class BaseImportEntryForm(forms.Form):
    file = forms.FileField(
        label="Import File",
        widget=forms.ClearableFileInput(attrs={
            "class": "file-input file-input-bordered file-input-sm w-full"
        }),
    )
    status = forms.ChoiceField(
        choices=EntryStatus.choices,
        required=True,
        widget=forms.Select(attrs={
            "class": "select select-bordered w-full",
            "placeholder": "Select Status",
        }),
    )
    backup_description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full",
            "placeholder": "Brief description of the expense",
        }),
    )
    status_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "textarea textarea-bordered w-full",
            "placeholder": "Leave notes for the status update",
            "rows": 3,
        }),
        label="Status Notes",  # Optional
        help_text="Optional notes about this status update."  # Optional
    )
    
    # TODO: Refactoring Required 
    def __init__(self, *args, **kwargs):
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
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = self.get_allowed_statuses()

    # TODO: Refactoring Required
    def get_allowed_statuses(self):
        # OA, WA, OR => ALL STATUSES
        print(self.is_org_admin, self.is_workspace_admin, self.is_operation_reviewer)
        if self.is_org_admin or self.is_workspace_admin or self.is_operation_reviewer:
            allowed_statuses = EntryStatus.values
        # TC => PENDING, REVIEWED, REJECTED
        elif self.is_team_coordinator:
            allowed_statuses = [
                EntryStatus.PENDING,
                EntryStatus.REVIEWED,
                EntryStatus.REJECTED,
            ]
        # Others => None
        else:
            allowed_statuses = []

        # Convert codes into (value, label) tuples using EntryStatus.labels
        return [
            (status, dict(EntryStatus.choices)[status]) for status in allowed_statuses
        ]

    def clean(self):
        cleaned_data = super().clean()
        #Validate File type (Allow only CSV)
        uploaded_file = self.cleaned_data.get("file")
        if uploaded_file:
            file_name, file_extension = os.path.splitext(uploaded_file.name)
            if file_extension.lower() not in [".csv"]:
                raise forms.ValidationError("Only CSV file is allowed.")
        
        return cleaned_data
        