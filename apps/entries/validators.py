from django.core.exceptions import ValidationError

from apps.teams.constants import TeamMemberRole
from .constants import EntryStatus, EntryType
from .models import Entry
from datetime import date


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
        is_team_coordinator,
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
                raise ValidationError("You are not allowed to update entry status.")

    def validate_workspace_period(self, occurred_at):
        today = date.today()

        if not (self.workspace.start_date <= today <= self.workspace.end_date):
            raise ValidationError(
                "Entries can only be submitted during the workspace period."
            )

        if occurred_at and not (
            self.workspace.start_date <= occurred_at <= self.workspace.end_date
        ):
            raise ValidationError(
                "The occurred date must be within the workspace period."
            )

    def validate_team_remittance(self):
        if self.workspace_team.remittance.confirmed_by:
            raise ValidationError(
                "Remittance for this workspace team is already confirmed."
            )

    def validate_entry_create_authorization(self, entry_type: EntryType):
        if entry_type in [
            EntryType.INCOME,
            EntryType.DISBURSEMENT,
        ] and not (
            self.is_org_admin
            or self.is_team_coordinator
            or self.workspace_team_role == TeamMemberRole.SUBMITTER
        ):
            raise ValidationError(
                "Only Admin, Team Coordinators, and Submitters are authorized for this action."
            )

        if entry_type == EntryType.REMITTANCE and not (
            self.is_team_coordinator or self.is_org_admin
        ):
            raise ValidationError(
                "Only Admin and Team Coordinator are authorized for this action."
            )

    def validate_entry_update(self, entry: Entry, new_status=None, occurred_at=None):
        self.validate_team_remittance()
        date_for_period_validation = (
            occurred_at if occurred_at is not None else entry.occurred_at
        )
        self.validate_workspace_period(date_for_period_validation)

        if new_status is not None:
            self.validate_status_transition(new_status)

        return True

    def validate_entry_create(self, entry_type: EntryType, occurred_at):
        self.validate_workspace_period(occurred_at)
        self.validate_entry_create_authorization(entry_type)
