import pytest
from decimal import Decimal

from apps.entries.services import entry_create
from apps.remittance.models import Remittance
from apps.workspaces.models import WorkspaceTeam
from tests.factories import (
    TeamMemberFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.fixture
def remittance_test_data():
    """Provides a team and a submitter for remittance tests."""
    team = TeamFactory(title="Test Team")
    submitter = TeamMemberFactory(team=team)

    workspace = submitter.organization_member.organization.workspaces.first()
    if not workspace:
        workspace = WorkspaceFactory(
            organization=submitter.organization_member.organization
        )

    WorkspaceTeamFactory(team=team, workspace=workspace)
    return submitter, team


@pytest.mark.unit
@pytest.mark.django_db
class TestRemittanceSignal:
    """Test remittance signal business logic."""

    def test_remittance_creation_on_income_entry(self, remittance_test_data):
        """Test that a remittance record is created when a new income entry is saved."""
        submitter, _ = remittance_test_data

        assert Remittance.objects.count() == 0

        entry_create(
            entry_type="income",
            amount=Decimal("1000.00"),
            submitted_by=submitter,
            description="Test Income Entry",
        )

        assert Remittance.objects.count() == 1
        remittance = Remittance.objects.first()
        assert remittance.due_amount == Decimal("900.00")  # 90% of 1000
        assert remittance.status == "pending"

    def test_remittance_not_created_for_non_income_entry(self, remittance_test_data):
        """Test that no remittance is created for non-income entries."""
        submitter, _ = remittance_test_data
        entry_create(
            entry_type="disbursement",
            amount=Decimal("500.00"),
            submitted_by=submitter,
            description="Test Expense Entry",
        )
        assert Remittance.objects.count() == 0

    def test_remittance_not_created_on_entry_update(self, remittance_test_data):
        """Test that the signal does not trigger on entry updates."""
        submitter, _ = remittance_test_data
        entry = entry_create(
            entry_type="income",
            amount=Decimal("1000.00"),
            submitted_by=submitter,
            description="Test Income Entry",
        )
        assert Remittance.objects.count() == 1
        initial_due_amount = Remittance.objects.first().due_amount

        # Update the entry
        entry.amount = Decimal("2000.00")
        entry.save()

        # The signal only runs on creation, so the remittance record should not be updated.
        assert Remittance.objects.count() == 1
        assert Remittance.objects.first().due_amount == initial_due_amount

    def test_custom_remittance_rate_is_used(self):
        """Test that the team's custom remittance rate is used if available."""
        team = TeamFactory(title="Test Team", custom_remittance_rate=15.00)
        submitter = TeamMemberFactory(team=team)

        workspace = submitter.organization_member.organization.workspaces.first()
        if not workspace:
            workspace = WorkspaceFactory(
                organization=submitter.organization_member.organization
            )
        WorkspaceTeamFactory(team=team, workspace=workspace)

        entry_create(
            entry_type="income",
            amount=Decimal("1000.00"),
            submitted_by=submitter,
            description="Test Income Entry",
        )

        assert Remittance.objects.count() == 1
        remittance = Remittance.objects.first()
        assert remittance.due_amount == Decimal("150.00")  # 15% of 1000

    def test_no_remittance_if_workspace_team_does_not_exist(self, remittance_test_data):
        """Test that no remittance is created if the team is not associated with the workspace."""
        submitter, team = remittance_test_data

        # Ensure the WorkspaceTeam link is removed to test the signal's early exit
        WorkspaceTeam.objects.filter(
            team=team,
            workspace__organization=submitter.organization_member.organization,
        ).delete()

        assert Remittance.objects.count() == 0

        entry_create(
            entry_type="income",
            amount=Decimal("1000.00"),
            submitted_by=submitter,
            description="Test Income Entry",
        )

        assert Remittance.objects.count() == 0
