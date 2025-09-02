from decimal import Decimal
from datetime import date
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.entries.forms import (
    BaseEntryForm,
    CreateOrganizationExpenseEntryForm,
    CreateWorkspaceTeamEntryForm,
    BaseUpdateEntryForm,
    UpdateWorkspaceTeamEntryForm,
)
from apps.entries.constants import EntryType, EntryStatus
from apps.teams.constants import TeamMemberRole
from apps.currencies.models import Currency
from tests.factories.entry_factories import (
    PendingEntryFactory,
    ApprovedEntryFactory,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
)
from tests.factories.team_factories import TeamMemberFactory


class TestBaseEntryForm(TestCase):
    """Test cases for BaseEntryForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization exchange rate
        from apps.organizations.models import OrganizationExchangeRate

        self.org_exchange_rate = OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today(),
            rate=Decimal("1.00"),
        )

    def test_base_entry_form_valid_data(self):
        """Test that BaseEntryForm accepts valid data."""
        form_data = {
            "amount": "100.50",
            "description": "Test expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
        }

        form = BaseEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert form.is_valid(), f"Form errors: {form.errors}"
        assert form.cleaned_data["amount"] == Decimal("100.50")
        assert form.cleaned_data["description"] == "Test expense"

    def test_base_entry_form_invalid_amount(self):
        """Test that BaseEntryForm rejects invalid amount."""
        form_data = {
            "amount": "0",  # Invalid: amount must be > 0
            "description": "Test expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
        }

        form = BaseEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert not form.is_valid()
        assert "amount" in form.errors

    def test_base_entry_form_missing_required_fields(self):
        """Test that BaseEntryForm requires all fields."""
        form_data = {
            "amount": "100.50",
            # Missing description, currency, occurred_at
        }

        form = BaseEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert not form.is_valid()
        assert "description" in form.errors
        assert "currency" in form.errors
        assert "occurred_at" in form.errors

    def test_base_entry_form_currency_queryset_filtering(self):
        """Test that currency field only shows organization currencies."""
        # Create another currency not associated with organization
        other_currency = Currency.objects.create(code="EUR", name="Euro")

        form = BaseEntryForm(
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        currency_choices = list(form.fields["currency"].queryset)
        assert self.currency in currency_choices
        assert other_currency not in currency_choices

    def test_base_entry_form_attachment_validation(self):
        """Test that BaseEntryForm validates attachments."""
        # Create a test file (small enough to pass validation, with allowed extension)
        test_file = SimpleUploadedFile(
            "test.pdf", b"test file content", content_type="application/pdf"
        )

        form_data = {
            "amount": "100.50",
            "description": "Test expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
        }

        files = {"attachment_files": [test_file]}

        form = BaseEntryForm(
            data=form_data,
            files=files,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert form.is_valid(), f"Form errors: {form.errors}"


class TestCreateOrganizationExpenseEntryForm(TestCase):
    """Test cases for CreateOrganizationExpenseEntryForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization exchange rate
        from apps.organizations.models import OrganizationExchangeRate

        self.org_exchange_rate = OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today(),
            rate=Decimal("1.00"),
        )

    def test_org_expense_form_org_admin_access(self):
        """Test that org admins can create organization expenses."""
        form_data = {
            "amount": "500.00",
            "description": "Office supplies",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
        }

        form = CreateOrganizationExpenseEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            is_org_admin=True,
        )

        assert form.is_valid(), f"Form errors: {form.errors}"

    def test_org_expense_form_non_admin_access_denied(self):
        """Test that non-org admins cannot create organization expenses."""
        form_data = {
            "amount": "500.00",
            "description": "Office supplies",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
        }

        form = CreateOrganizationExpenseEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            is_org_admin=False,
        )

        assert not form.is_valid()
        assert "You are not authorized to create organization expenses" in str(
            form.errors["__all__"]
        )


class TestCreateWorkspaceTeamEntryForm(TestCase):
    """Test cases for CreateWorkspaceTeamEntryForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)

        # Set the team coordinator to the org member
        self.workspace_team.team.team_coordinator = self.org_member
        self.workspace_team.team.save()

        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization exchange rate
        from apps.organizations.models import OrganizationExchangeRate

        self.org_exchange_rate = OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today(),
            rate=Decimal("1.00"),
        )

    def test_workspace_team_form_team_coordinator_access(self):
        """Test that team coordinators can create entries with all types."""
        # Create a team member with team coordinator role
        TeamMemberFactory(
            team=self.workspace_team.team,
            organization_member=self.org_member,
            role=TeamMemberRole.TEAM_COORDINATOR,
        )

        form_data = {
            "amount": "100.00",
            "description": "Team expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
            "entry_type": "income",
        }

        form = CreateWorkspaceTeamEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_team_coordinator=True,
        )

        assert form.is_valid(), f"Form errors: {form.errors}"

    def test_workspace_team_form_submitter_access(self):
        """Test that submitters can create income and disbursement entries."""
        # Create a different organization member for submitter role to avoid unique constraint
        submitter_org_member = OrganizationMemberFactory(organization=self.organization)
        TeamMemberFactory(
            team=self.workspace_team.team,
            organization_member=submitter_org_member,
            role=TeamMemberRole.SUBMITTER,
        )

        form_data = {
            "amount": "100.00",
            "description": "Team expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
            "entry_type": "disbursement",
        }

        form = CreateWorkspaceTeamEntryForm(
            data=form_data,
            org_member=submitter_org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
        )

        assert form.is_valid(), f"Form.errors: {form.errors}"

    def test_workspace_team_form_submitter_remittance_denied(self):
        """Test that submitters cannot create remittance entries."""
        # Create a different organization member for submitter role to avoid unique constraint
        submitter_org_member = OrganizationMemberFactory(organization=self.organization)
        TeamMemberFactory(
            team=self.workspace_team.team,
            organization_member=submitter_org_member,
            role=TeamMemberRole.SUBMITTER,
        )

        form_data = {
            "amount": "100.00",
            "description": "Team expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
            "entry_type": "remittance",
        }

        form = CreateWorkspaceTeamEntryForm(
            data=form_data,
            org_member=submitter_org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
        )

        # This should fail validation due to entry type restrictions
        assert not form.is_valid()

    def test_workspace_team_form_entry_type_choices_filtering(self):
        """Test that entry type choices are filtered based on role."""
        # Create a team member with team coordinator role
        TeamMemberFactory(
            team=self.workspace_team.team,
            organization_member=self.org_member,
            role=TeamMemberRole.TEAM_COORDINATOR,
        )

        # Test team coordinator choices
        form = CreateWorkspaceTeamEntryForm(
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_team_coordinator=True,
        )

        coordinator_choices = form.get_allowed_entry_types()
        expected_coordinator_choices = [
            (EntryType.INCOME, "Income"),
            (EntryType.DISBURSEMENT, "Disbursement"),
            (EntryType.REMITTANCE, "Remittance"),
        ]
        assert coordinator_choices == expected_coordinator_choices

        # Create a different organization member for submitter role to avoid unique constraint
        submitter_org_member = OrganizationMemberFactory(organization=self.organization)
        TeamMemberFactory(
            team=self.workspace_team.team,
            organization_member=submitter_org_member,
            role=TeamMemberRole.SUBMITTER,
        )

        # Test submitter choices
        form = CreateWorkspaceTeamEntryForm(
            org_member=submitter_org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
        )

        submitter_choices = form.get_allowed_entry_types()
        expected_submitter_choices = [
            (EntryType.INCOME, "Income"),
            (EntryType.DISBURSEMENT, "Disbursement"),
        ]
        assert submitter_choices == expected_submitter_choices


class TestBaseUpdateEntryForm(TestCase):
    """Test cases for BaseUpdateEntryForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization exchange rate
        from apps.organizations.models import OrganizationExchangeRate

        self.org_exchange_rate = OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today(),
            rate=Decimal("1.00"),
        )

    def test_update_form_pending_entry_all_fields_editable(self):
        """Test that pending entries allow editing of all fields."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        form = BaseUpdateEntryForm(
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # All fields should be enabled for pending entries
        assert not form.fields["amount"].disabled
        assert not form.fields["description"].disabled
        assert not form.fields["attachment_files"].disabled
        assert not form.fields["currency"].disabled
        assert not form.fields["occurred_at"].disabled

    def test_update_form_non_pending_entry_fields_disabled(self):
        """Test that non-pending entries disable amount, description, and attachments."""
        entry = ApprovedEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        form = BaseUpdateEntryForm(
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Core fields should be disabled for non-pending entries
        assert form.fields["amount"].disabled
        assert form.fields["description"].disabled
        assert form.fields["attachment_files"].disabled
        assert form.fields["currency"].disabled
        assert form.fields["occurred_at"].disabled

    def test_update_form_submitter_status_fields_disabled(self):
        """Test that submitters cannot modify status fields."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        form = BaseUpdateEntryForm(
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
        )

        # Status fields should be disabled for submitters
        assert form.fields["status"].disabled
        assert form.fields["status_note"].disabled

    def test_update_form_team_coordinator_remittance_status_disabled(self):
        """Test that team coordinators cannot modify status for remittance entries."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
            entry_type=EntryType.REMITTANCE,
        )

        form = BaseUpdateEntryForm(
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_team_coordinator=True,
        )

        # Status fields should be disabled for team coordinators on remittance
        assert form.fields["status"].disabled
        assert form.fields["status_note"].disabled

    def test_update_form_allowed_statuses_org_admin(self):
        """Test that org admins can see all statuses."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        form = BaseUpdateEntryForm(
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_org_admin=True,
        )

        allowed_statuses = form.get_allowed_statuses()
        expected_statuses = [
            (EntryStatus.PENDING, "Pending"),
            (EntryStatus.REVIEWED, "Reviewed"),
            (EntryStatus.APPROVED, "Approved"),
            (EntryStatus.REJECTED, "Rejected"),
        ]
        assert len(allowed_statuses) == len(expected_statuses)

    def test_update_form_allowed_statuses_team_coordinator(self):
        """Test that team coordinators can see limited statuses."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        form = BaseUpdateEntryForm(
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_team_coordinator=True,
        )

        allowed_statuses = form.get_allowed_statuses()
        expected_statuses = [
            (EntryStatus.PENDING, "Pending"),
            (EntryStatus.REVIEWED, "Reviewed"),
            (EntryStatus.REJECTED, "Rejected"),
        ]
        assert len(allowed_statuses) == len(expected_statuses)
        assert (EntryStatus.APPROVED, "Approved") not in allowed_statuses


class TestUpdateWorkspaceTeamEntryForm(TestCase):
    """Test cases for UpdateWorkspaceTeamEntryForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization exchange rate
        from apps.organizations.models import OrganizationExchangeRate

        self.org_exchange_rate = OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today(),
            rate=Decimal("1.00"),
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_update_workspace_team_form_valid_update(self):
        """Test that UpdateWorkspaceTeamEntryForm accepts valid updates."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        form_data = {
            "amount": "150.00",
            "description": "Updated description",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
            "status": EntryStatus.REVIEWED,
            "status_note": "Reviewed and updated",
        }

        form = UpdateWorkspaceTeamEntryForm(
            data=form_data,
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_org_admin=True,
        )

        assert form.is_valid(), f"Form errors: {form.errors}"

    def test_update_workspace_team_form_invalid_status_transition(self):
        """Test that UpdateWorkspaceTeamEntryForm validates status transitions."""
        entry = PendingEntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        form_data = {
            "amount": "150.00",
            "description": "Updated description",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
            "status": EntryStatus.APPROVED,  # Invalid transition
            "status_note": "Approved",
        }

        form = UpdateWorkspaceTeamEntryForm(
            data=form_data,
            instance=entry,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            is_team_coordinator=True,  # Limited permissions
        )

        # This should fail validation due to status transition rules
        assert not form.is_valid()


class TestEntryFormsIntegration(TestCase):
    """Integration tests for entry forms."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization exchange rate
        from apps.organizations.models import OrganizationExchangeRate

        self.org_exchange_rate = OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today(),
            rate=Decimal("1.00"),
        )

    def test_form_clean_method_currency_validation(self):
        """Test that form clean method validates currency."""
        form_data = {
            "amount": "100.00",
            "description": "Test expense",
            "currency": "",  # Empty currency
            "occurred_at": date.today(),
        }

        form = BaseEntryForm(
            data=form_data,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert not form.is_valid()
        assert "Currency is required" in str(form.errors["__all__"])

    def test_form_clean_method_attachment_validation(self):
        """Test that form clean method validates attachments."""
        # Create an invalid file (too large - over 5MB limit, with allowed extension)
        large_file = SimpleUploadedFile(
            "large.pdf",
            b"x" * (6 * 1024 * 1024),  # 6MB file (over 5MB limit)
            content_type="application/pdf",
        )

        form_data = {
            "amount": "100.00",
            "description": "Test expense",
            "currency": self.currency.currency_id,
            "occurred_at": date.today(),
        }

        files = {"attachment_files": [large_file]}

        form = BaseEntryForm(
            data=form_data,
            files=files,
            org_member=self.org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # This should fail validation due to file size
        assert not form.is_valid()
