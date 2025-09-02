"""
Unit tests for apps.entries.validators
"""

import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from apps.entries.validators import TeamEntryValidator
from apps.entries.constants import EntryStatus, EntryType
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    EntryFactory,
    OrganizationFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
    OrganizationMemberFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestTeamEntryValidator:
    """Test TeamEntryValidator class."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
        )
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created

    def test_validator_initialization(self):
        """Test validator initialization with all parameters."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        assert validator.organization == self.organization
        assert validator.workspace == self.workspace
        assert validator.workspace_team == self.workspace_team
        assert validator.workspace_team_role == TeamMemberRole.SUBMITTER
        assert validator.is_org_admin is False
        assert validator.is_workspace_admin is False
        assert validator.is_operation_reviewer is False
        assert validator.is_team_coordinator is False


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateStatusTransition:
    """Test validate_status_transition method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created

    def test_validate_status_transition_approved_by_org_admin(self):
        """Test approving entry as org admin."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_status_transition(EntryStatus.APPROVED)

    def test_validate_status_transition_approved_by_operation_reviewer(self):
        """Test approving entry as operation reviewer."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=True,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_status_transition(EntryStatus.APPROVED)

    def test_validate_status_transition_approved_by_unauthorized_user(self):
        """Test approving entry by unauthorized user (missing lines 33-34)."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Only Admin and Operation Reviewer can approve entries.",
        ):
            validator.validate_status_transition(EntryStatus.APPROVED)

    def test_validate_status_transition_other_status_by_authorized_user(self):
        """Test updating to other status by authorized user."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_status_transition(EntryStatus.REVIEWED)

    def test_validate_status_transition_other_status_by_unauthorized_user(self):
        """Test updating to other status by unauthorized user (missing line 44)."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError, match="You are not allowed to update entry status."
        ):
            validator.validate_status_transition(EntryStatus.REVIEWED)

    def test_validate_status_transition_other_status_by_team_coordinator(self):
        """Test updating to other status by team coordinator."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.TEAM_COORDINATOR,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=True,
        )

        # Should not raise any exception
        validator.validate_status_transition(EntryStatus.REVIEWED)

    def test_validate_status_transition_other_status_by_workspace_admin(self):
        """Test updating to other status by workspace admin."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=True,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_status_transition(EntryStatus.REJECTED)


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateWorkspacePeriod:
    """Test validate_workspace_period method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
        )
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created

    def test_validate_workspace_period_valid_today(self):
        """Test validation with valid today date."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_workspace_period(date.today())

    def test_validate_workspace_period_valid_occurred_at(self):
        """Test validation with valid occurred_at date."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        valid_date = date.today() - timedelta(days=15)
        # Should not raise any exception
        validator.validate_workspace_period(valid_date)

    def test_validate_workspace_period_invalid_today_before_start(self):
        """Test validation when today is before workspace start date (missing line 50)."""
        # Create workspace that starts in the future
        future_workspace = WorkspaceFactory(
            organization=self.organization,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=40),
        )
        future_workspace_team = WorkspaceTeamFactory(workspace=future_workspace)

        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=future_workspace,
            workspace_team=future_workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Entries can only be submitted during the workspace period.",
        ):
            validator.validate_workspace_period(date.today())

    def test_validate_workspace_period_invalid_today_after_end(self):
        """Test validation when today is after workspace end date."""
        # Create workspace that ended in the past
        past_workspace = WorkspaceFactory(
            organization=self.organization,
            start_date=date.today() - timedelta(days=40),
            end_date=date.today() - timedelta(days=10),
        )
        past_workspace_team = WorkspaceTeamFactory(workspace=past_workspace)

        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=past_workspace,
            workspace_team=past_workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Entries can only be submitted during the workspace period.",
        ):
            validator.validate_workspace_period(date.today())

    def test_validate_workspace_period_invalid_occurred_at_before_start(self):
        """Test validation when occurred_at is before workspace start date (missing line 57)."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        invalid_date = date.today() - timedelta(days=40)  # Before workspace start

        with pytest.raises(
            ValidationError,
            match="The occurred date must be within the workspace period.",
        ):
            validator.validate_workspace_period(invalid_date)

    def test_validate_workspace_period_invalid_occurred_at_after_end(self):
        """Test validation when occurred_at is after workspace end date."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        invalid_date = date.today() + timedelta(days=40)  # After workspace end

        with pytest.raises(
            ValidationError,
            match="The occurred date must be within the workspace period.",
        ):
            validator.validate_workspace_period(invalid_date)


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateTeamRemittance:
    """Test validate_team_remittance method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created

    def test_validate_team_remittance_not_confirmed(self):
        """Test validation when remittance is not confirmed."""
        # Use the existing remittance from setup (already has confirmed_by=None)

        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_team_remittance()

    def test_validate_team_remittance_already_confirmed(self):
        """Test validation when remittance is already confirmed (missing line 63)."""
        # Update the existing remittance to be confirmed
        org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace_team.remittance.confirmed_by = org_member
        self.workspace_team.remittance.save()

        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Remittance for this workspace team is already confirmed.",
        ):
            validator.validate_team_remittance()


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateEntryCreateAuthorization:
    """Test validate_entry_create_authorization method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created

    def test_validate_entry_create_authorization_income_by_org_admin(self):
        """Test income entry creation by org admin."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_entry_create_authorization(EntryType.INCOME)

    def test_validate_entry_create_authorization_income_by_team_coordinator(self):
        """Test income entry creation by team coordinator."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.TEAM_COORDINATOR,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=True,
        )

        # Should not raise any exception
        validator.validate_entry_create_authorization(EntryType.INCOME)

    def test_validate_entry_create_authorization_income_by_submitter(self):
        """Test income entry creation by submitter."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_entry_create_authorization(EntryType.INCOME)

    def test_validate_entry_create_authorization_income_by_unauthorized_user(self):
        """Test income entry creation by unauthorized user."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.AUDITOR,  # Not authorized
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Only Admin, Team Coordinators, and Submitters are authorized for this action.",
        ):
            validator.validate_entry_create_authorization(EntryType.INCOME)

    def test_validate_entry_create_authorization_disbursement_by_org_admin(self):
        """Test disbursement entry creation by org admin."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_entry_create_authorization(EntryType.DISBURSEMENT)

    def test_validate_entry_create_authorization_remittance_by_org_admin(self):
        """Test remittance entry creation by org admin."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_entry_create_authorization(EntryType.REMITTANCE)

    def test_validate_entry_create_authorization_remittance_by_team_coordinator(self):
        """Test remittance entry creation by team coordinator."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.TEAM_COORDINATOR,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=True,
        )

        # Should not raise any exception
        validator.validate_entry_create_authorization(EntryType.REMITTANCE)

    def test_validate_entry_create_authorization_remittance_by_unauthorized_user(self):
        """Test remittance entry creation by unauthorized user (missing line 81)."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,  # Not authorized for remittance
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Only Admin and Team Coordinator are authorized for this action.",
        ):
            validator.validate_entry_create_authorization(EntryType.REMITTANCE)

    def test_validate_entry_create_authorization_workspace_expense(self):
        """Test workspace expense entry creation (no restrictions)."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.AUDITOR,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception (no restrictions for workspace expense)
        validator.validate_entry_create_authorization(EntryType.WORKSPACE_EXP)

    def test_validate_entry_create_authorization_org_expense(self):
        """Test organization expense entry creation (no restrictions)."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.AUDITOR,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception (no restrictions for org expense)
        validator.validate_entry_create_authorization(EntryType.ORG_EXP)


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateEntryUpdate:
    """Test validate_entry_update method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
        )
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created
        self.entry = EntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            occurred_at=date.today(),
        )

    def test_validate_entry_update_success(self):
        """Test successful entry update validation."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        result = validator.validate_entry_update(
            entry=self.entry, new_status=EntryStatus.APPROVED, occurred_at=date.today()
        )

        assert result is True

    def test_validate_entry_update_with_remittance_confirmed(self):
        """Test entry update when remittance is confirmed."""
        # Set remittance as confirmed
        org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace_team.remittance.confirmed_by = org_member
        self.workspace_team.remittance.save()

        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Remittance for this workspace team is already confirmed.",
        ):
            validator.validate_entry_update(entry=self.entry)

    def test_validate_entry_update_with_invalid_occurred_at(self):
        """Test entry update with invalid occurred_at date."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=True,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        invalid_date = date.today() + timedelta(days=40)  # After workspace end

        with pytest.raises(
            ValidationError,
            match="The occurred date must be within the workspace period.",
        ):
            validator.validate_entry_update(entry=self.entry, occurred_at=invalid_date)

    def test_validate_entry_update_with_unauthorized_status_change(self):
        """Test entry update with unauthorized status change."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError, match="You are not allowed to update entry status."
        ):
            validator.validate_entry_update(
                entry=self.entry, new_status=EntryStatus.REVIEWED
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateEntryCreate:
    """Test validate_entry_create method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
        )
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        # Remittance is automatically created by signals when WorkspaceTeam is created

    def test_validate_entry_create_success(self):
        """Test successful entry creation validation."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        # Should not raise any exception
        validator.validate_entry_create(
            entry_type=EntryType.INCOME, occurred_at=date.today()
        )

    def test_validate_entry_create_with_invalid_occurred_at(self):
        """Test entry creation with invalid occurred_at date."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        invalid_date = date.today() + timedelta(days=40)  # After workspace end

        with pytest.raises(
            ValidationError,
            match="The occurred date must be within the workspace period.",
        ):
            validator.validate_entry_create(
                entry_type=EntryType.INCOME, occurred_at=invalid_date
            )

    def test_validate_entry_create_with_unauthorized_user(self):
        """Test entry creation by unauthorized user."""
        validator = TeamEntryValidator(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.AUDITOR,  # Not authorized
            is_org_admin=False,
            is_workspace_admin=False,
            is_operation_reviewer=False,
            is_team_coordinator=False,
        )

        with pytest.raises(
            ValidationError,
            match="Only Admin, Team Coordinators, and Submitters are authorized for this action.",
        ):
            validator.validate_entry_create(
                entry_type=EntryType.INCOME, occurred_at=date.today()
            )
