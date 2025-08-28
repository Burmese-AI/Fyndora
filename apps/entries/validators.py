from django.core.exceptions import ValidationError
from .constants import EntryStatus
from django import forms
from .models import Entry
from apps.core.forms import MultipleFileField, MultipleFileInput
from apps.attachments.utils import validate_uploaded_files
from .constants import EntryStatus, EntryType
from apps.teams.constants import TeamMemberRole
from datetime import date
from apps.currencies.models import Currency
from apps.currencies.selectors import get_org_defined_currencies


class TeamEntryValidator:
    def __init__(
        self, 
        *,
        organization, 
        workspace, 
        workspace_team, 
        workspace_team_role,
        is_org_admin,
        is_workspace_admin,
        is_operation_reviewer,
        is_team_coordinator
    ):
        self.organization = organization
        self.workspace = workspace
        self.workspace_team = workspace_team
        self.workspace_team_role = workspace_team_role
        self.is_org_admin = is_org_admin
        self.is_workspace_admin = is_workspace_admin
        self.is_operation_reviewer = is_operation_reviewer
        self.is_team_coordinator = is_team_coordinator
        
    def validate_status_transition(self, new_status):
        if new_status == EntryStatus.APPROVED:
            if not (self.is_org_admin or self.is_operation_reviewer):
                raise ValidationError(
                    "Only Admin and Operation Reviewer can approve entries."
                )
        else:
            if not (
                self.is_org_admin
                or self.is_operation_reviewer
                or self.is_team_coordinator
                or self.is_workspace_admin
            ):
                raise ValidationError(
                    "You are not allowed to update entry status."
                )
                
    def validate_workspace_period(self, entry: Entry):
        today = date.today()

        if not (self.workspace.start_date <= today <= self.workspace.end_date):
            raise ValidationError(
                "Entries can only be submitted during the workspace period."
            )

        if entry.occurred_at and not (
            self.workspace.start_date <= entry.occurred_at <= self.workspace.end_date
        ):
            raise ValidationError(
                "The occurred date must be within the workspace period."
            )
            
    def validate_team_remittance(self):
        if self.workspace_team.remittance.confirmed_by:
            raise ValidationError(
                "Remittance for this workspace team is already confirmed."
            )
            
    def validate_entry_update(self, entry: Entry, new_status=None):
        self.validate_team_remittance()
        self.validate_workspace_period(entry)

        if new_status is not None:
            self.validate_status_transition(new_status)

        return True