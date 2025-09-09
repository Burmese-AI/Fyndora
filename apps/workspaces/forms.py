from django import forms
from .models import Workspace, WorkspaceExchangeRate
from apps.organizations.models import OrganizationMember, OrganizationExchangeRate
from apps.teams.models import Team
from apps.workspaces.models import WorkspaceTeam
from apps.workspaces.selectors import get_teams_by_organization_id
from apps.currencies.forms import BaseExchangeRateCreateForm, BaseExchangeRateUpdateForm
from django.core.exceptions import ValidationError
from apps.core.selectors import get_org_members_without_owner
from datetime import datetime


class WorkspaceForm(forms.ModelForm):
    workspace_admin = forms.ModelChoiceField(
        queryset=OrganizationMember.objects.none(),  # Will be initialized in __init__
        required=False,  # allow for null values and can also be assigned later
        label="Select Workspace Admin",
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base "
            }
        ),
    )

    operations_reviewer = forms.ModelChoiceField(
        queryset=OrganizationMember.objects.none(),
        required=False,
        label="Select Operations Reviewer",
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base "
            }
        ),
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
            "operations_reviewer",
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
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base pr-12",
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base pr-12",
                    "type": "date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.can_change_workspace_admin = kwargs.pop("can_change_workspace_admin", True)
        super().__init__(*args, **kwargs)

        if self.organization:
            self.fields["workspace_admin"].queryset = get_org_members_without_owner(
                self.organization
            )

        if self.organization:
            self.fields["operations_reviewer"].queryset = get_org_members_without_owner(
                self.organization
            )

        if not self.can_change_workspace_admin:
            self.fields["workspace_admin"].widget.attrs["disabled"] = True

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title or not title.strip():
            raise forms.ValidationError("Title cannot be blank or only whitespace.")
        return title

    def clean_remittance_rate(self):
        remittance_rate = self.cleaned_data.get("remittance_rate")
        if remittance_rate < 0 or remittance_rate > 100:
            raise forms.ValidationError("Remittance rate must be between 0 and 100.")
        return remittance_rate

    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get("title")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        workspace_admin = cleaned_data.get("workspace_admin")
        operations_reviewer = cleaned_data.get("operations_reviewer")

        now = datetime.now().date()
        if end_date and end_date < now:
            raise forms.ValidationError("You cannot edit a workspace that has ended.")

        # to make sure the workspace admin and operations reviewer are not the same person
        if workspace_admin and operations_reviewer:
            if workspace_admin == operations_reviewer:
                raise forms.ValidationError(
                    "Workspace admin and operations reviewer cannot be the same person."
                )

        if title and self.organization:
            # Create a queryset excluding the current instance (if editing)
            workspace_queryset = Workspace.objects.filter(
                title=title, organization=self.organization
            )

            # If this is an edit operation (instance exists), exclude the current instance
            if self.instance and self.instance.pk:
                workspace_queryset = workspace_queryset.exclude(pk=self.instance.pk)

            if workspace_queryset.exists():
                raise forms.ValidationError(
                    "A workspace with this title already exists in this organization."
                )

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be earlier than start date.")

        return cleaned_data


class AddTeamToWorkspaceForm(forms.ModelForm):
    team = forms.ModelChoiceField(
        queryset=Team.objects.none(),
        required=True,
        label="Select Team",  # Temporary label, will be overwritten in __init__
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
            }
        ),
    )

    class Meta:
        model = WorkspaceTeam
        fields = ["team", "custom_remittance_rate", "syned_with_workspace_remittance_rate"]
        widgets = {
            "custom_remittance_rate": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter remittance rate (0-100)",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
            "syned_with_workspace_remittance_rate": forms.CheckboxInput(
                attrs={
                    "class": "checkbox checkbox-bordered rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)

        if self.organization:
            self.fields["team"].queryset = get_teams_by_organization_id(
                self.organization.organization_id
            )
            self.fields["team"].label = f"Select Team from {self.organization.title}"

    def clean_team(self):
        team = self.cleaned_data.get("team")
        team_exists = WorkspaceTeam.objects.filter(
            team=team, workspace_id=self.workspace.workspace_id
        ).exists()
        if team_exists:
            raise ValidationError("Team already exists in this workspace.")
        return team


class ChangeWorkspaceTeamRemittanceRateForm(forms.ModelForm):
    class Meta:
        model = WorkspaceTeam
        fields = ["custom_remittance_rate"]
        widgets = {
            "custom_remittance_rate": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter remittance rate (0-100) % (optional)",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)

    def clean_custom_remittance_rate(self):
        custom_remittance_rate = self.cleaned_data.get("custom_remittance_rate")
        if custom_remittance_rate is not None and (
            custom_remittance_rate < 0 or custom_remittance_rate > 100
        ):
            raise forms.ValidationError("Remittance rate must be between 0 and 100.")
        return custom_remittance_rate

    def clean(self):
        # to make sure the remittance rate is not changed after the workspace has ended
        now = datetime.now().date()
        workspace_end_date = self.workspace.end_date
        if workspace_end_date and workspace_end_date < now:
            raise forms.ValidationError(
                "You cannot change the remittance rate of a workspace that has ended."
            )
        return self.cleaned_data


class WorkspaceExchangeRateCreateForm(BaseExchangeRateCreateForm):
    class Meta(BaseExchangeRateCreateForm.Meta):
        model = WorkspaceExchangeRate
        fields = BaseExchangeRateCreateForm.Meta.fields
        widgets = BaseExchangeRateCreateForm.Meta.widgets

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # Check if an org exchange rate with this provided currency already exists
        currency_code = cleaned_data.get("currency_code")
        org_exchange_rate_exists = OrganizationExchangeRate.objects.filter(
            organization=self.organization,
            currency__code__iexact=currency_code,
        ).exists()
        if not org_exchange_rate_exists:
            raise ValidationError(
                "Organization exchange rate with this currency does not exist."
            )
        return cleaned_data


class WorkspaceExchangeRateUpdateForm(BaseExchangeRateUpdateForm):
    class Meta(BaseExchangeRateUpdateForm.Meta):
        model = WorkspaceExchangeRate
        fields = BaseExchangeRateUpdateForm.Meta.fields + ["is_approved"]
        widgets = {
            **BaseExchangeRateUpdateForm.Meta.widgets,
            "is_approved": forms.CheckboxInput(
                attrs={
                    "class": "checkbox checkbox-bordered rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)
