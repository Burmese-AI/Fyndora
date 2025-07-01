from django import forms
from .models import Team
from apps.organizations.models import OrganizationMember
from apps.workspaces.selectors import get_organization_members_by_organization_id
from apps.teams.models import TeamMember
from apps.teams.constants import TeamMemberRole


class TeamForm(forms.ModelForm):
    team_coordinator = forms.ModelChoiceField(
        queryset=OrganizationMember.objects.none(),  # Will be initialized in __init__
        required=False,  # allow for null values and can also be assigned later
        label="Select Team Coordinator",
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base "
            }
        ),
    )

    class Meta:
        model = Team
        fields = ["title", "description", "team_coordinator", "custom_remittance_rate"]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter team title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base min-h-[60px]",
                    "rows": 2,
                    "placeholder": "Describe your team (optional)",
                }
            ),
            "custom_remittance_rate": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base",
                    "placeholder": "Enter remittance rate (0-100)",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if self.organization:
            self.fields[
                "team_coordinator"
            ].queryset = get_organization_members_by_organization_id(
                self.organization.organization_id
            )

    def clean_title(self):
        title = self.cleaned_data.get("title")
        # Use the organization from the form instance if available, otherwise use the one passed to __init__
        organization = getattr(self.instance, "organization", None) or self.organization

        if not organization:
            raise forms.ValidationError("Organization is required for team creation")

        if Team.objects.filter(title=title, organization=organization).exists():
            raise forms.ValidationError(
                "Team with this title already exists in this organization"
            )
        return title


class TeamMemberForm(forms.ModelForm):
    organization_member = forms.ModelChoiceField(
        queryset=OrganizationMember.objects.none(),
        required=True,
        label="Select Organization Member",
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base"
            }
        ),
    )
    role = forms.ChoiceField(
        choices=TeamMemberRole.choices,
        required=True,
        label="Select Role",
        widget=forms.Select(
            attrs={
                "class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base"
            }
        ),
    )

    class Meta:
        model = TeamMember
        fields = ["organization_member", "role"]

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.team = kwargs.pop("team", None)
        super().__init__(*args, **kwargs)

        if self.organization:
            self.fields[
                "organization_member"
            ].queryset = get_organization_members_by_organization_id(
                self.organization.organization_id
            )

    def clean(self):
        cleaned_data = super().clean()
        organization_member = cleaned_data.get("organization_member")
        team = self.team or getattr(self.instance, "team", None)

        if organization_member and team:
            # Check if this member is already in the team
            if TeamMember.objects.filter(
                team=team, organization_member=organization_member
            ).exists():
                raise forms.ValidationError("This member is already part of this team")

        return cleaned_data


class EditTeamMemberRoleForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ["role"]

    role = forms.ChoiceField(
        choices=TeamMemberRole.choices,
        required=True,
        label="Select Role",
        widget=forms.Select(
            attrs={"class": "select select-bordered w-full rounded-lg shadow focus:outline-none focus:ring-2 focus:ring-primary text-base"}
        ),
    )

    def clean_role(self):
        role = self.cleaned_data.get("role")
        print(role)
        print(self.instance.role)
        if role == self.instance.role:
            raise forms.ValidationError("New role cannot be the same as the current role")
        return role
    