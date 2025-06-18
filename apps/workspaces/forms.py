from django import forms
from .models import Workspace
from apps.organizations.models import OrganizationMember
from apps.workspaces.selectors import get_organization_members_by_organization_id
from apps.teams.models import Team
from apps.organizations.models import Organization
from apps.workspaces.models import WorkspaceTeam
from apps.workspaces.selectors import get_teams_by_organization_id
from django.core.exceptions import ValidationError

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
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        if self.organization:
            self.fields[
                "workspace_admin"
            ].queryset = get_organization_members_by_organization_id(
                self.organization.organization_id
            )

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
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base mt-4",
            }
        ),
    )

    class Meta:
        model = WorkspaceTeam
        fields = ["team"]

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.workspace = kwargs.pop("workspace", None)
        super().__init__(*args, **kwargs)

        if self.organization:
            self.fields["team"].queryset = get_teams_by_organization_id(self.organization.organization_id)
            self.fields["team"].label = f"Select Team from {self.organization.title}"


    def clean_team(self):
        team = self.cleaned_data.get("team")
        team_exists = WorkspaceTeam.objects.filter(team=team, workspace_id=self.workspace.workspace_id).exists()
        if team_exists:
            raise ValidationError("Team already exists in this workspace.")
        return team

    def clean(self):
        cleaned_data = super().clean()
        team = cleaned_data.get("team")