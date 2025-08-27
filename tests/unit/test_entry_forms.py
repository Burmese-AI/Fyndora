"""
Unit tests for Entry forms.

Tests form validation, field behavior, and business logic in entry forms.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.currencies.models import Currency
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.forms import (
    BaseEntryForm,
    BaseUpdateEntryForm,
    CreateOrganizationExpenseEntryForm,
    CreateWorkspaceTeamEntryForm,
)
from apps.organizations.models import OrganizationExchangeRate
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    ApprovedEntryFactory,
    EntryFactory,
    OrganizationMemberFactory,
    PendingEntryFactory,
    TeamFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)
from apps.entries.forms import UpdateOrganizationExpenseEntryForm


@pytest.mark.unit
@pytest.mark.django_db
class TestBaseEntryForm:
    """Test BaseEntryForm functionality."""

    def setup_method(self):
        """Set up test data."""

        self.organization = OrganizationMemberFactory().organization
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create organization member to use as added_by
        self.org_member = OrganizationMemberFactory(organization=self.organization)

        # Create OrganizationExchangeRate to associate currency with organization
        OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.00"),
            effective_date=date.today(),
            added_by=self.org_member,
        )

    def test_form_initialization_with_organization(self):
        """Test form initializes with organization currency queryset."""
        form = BaseEntryForm(organization=self.organization)

        assert self.currency in form.fields["currency"].queryset
        assert form.fields["currency"].queryset.count() == 1

    def test_form_initialization_without_organization(self):
        """Test form initializes with empty currency queryset when no organization."""
        form = BaseEntryForm()

        assert form.fields["currency"].queryset.count() == 0

    def test_valid_form_data(self):
        """Test form validation with valid data."""
        form_data = {
            "amount": "100.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert form.is_valid()

    def test_invalid_amount_negative(self):
        """Test form validation fails with negative amount."""
        form_data = {
            "amount": "-100.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert not form.is_valid()
        assert "amount" in form.errors

    def test_invalid_amount_zero(self):
        """Test form validation fails with zero amount."""
        form_data = {
            "amount": "0.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert not form.is_valid()
        assert "amount" in form.errors

    def test_invalid_description_too_long(self):
        """Test form validation fails with description too long."""
        form_data = {
            "amount": "100.00",
            "description": "x" * 256,  # Exceeds max_length=255
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert not form.is_valid()
        assert "description" in form.errors

    def test_attachment_files_validation_valid_file(self):
        """Test attachment files validation with valid file."""
        # Create a mock file
        test_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )

        form_data = {
            "amount": "100.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(
            data=form_data,
            files={"attachment_files": [test_file]},
            organization=self.organization,
        )

        # Should be valid (assuming clean_attachment_files doesn't reject PDF)
        assert form.is_valid() or "attachment_files" not in form.errors

    def test_required_fields(self):
        """Test form validation fails when required fields are missing."""
        form = BaseEntryForm(data={}, organization=self.organization)

        assert not form.is_valid()
        assert "amount" in form.errors
        assert "description" in form.errors
        assert "currency" in form.errors
        assert "occurred_at" in form.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateOrganizationExpenseEntryForm:
    """Test CreateOrganizationExpenseEntryForm functionality."""

    def setup_method(self):
        """Set up test data."""
        self.org_member = OrganizationMemberFactory()
        self.organization = self.org_member.organization
        self.currency = Currency.objects.create(code="EUR", name="Euro")

        # Create OrganizationExchangeRate to associate currency with organization
        OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.00"),
            effective_date=date.today(),
            added_by=self.org_member,
        )

    def test_form_initialization_with_authorized_user(self):
        """Test form initializes for organization admin."""
        form = CreateOrganizationExpenseEntryForm(
            organization=self.organization, is_org_admin=True
        )

        # Form should initialize successfully
        assert form.organization == self.organization

    def test_form_initialization_with_unauthorized_user(self):
        """Test form raises error for non-admin user."""
        form_data = {
            "amount": "500.00",
            "description": "Office supplies",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = CreateOrganizationExpenseEntryForm(
            data=form_data, organization=self.organization, is_org_admin=False
        )

        assert not form.is_valid()
        assert "You are not authorized to create organization expenses" in str(
            form.errors
        )

    def test_valid_form_submission(self):
        """Test valid form submission for organization expense."""
        form_data = {
            "amount": "500.00",
            "description": "Office supplies",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = CreateOrganizationExpenseEntryForm(
            data=form_data, organization=self.organization, is_org_admin=True
        )

        assert form.is_valid()


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateWorkspaceTeamEntryForm:
    """Test CreateWorkspaceTeamEntryForm functionality."""

    def setup_method(self):
        """Set up test data."""

        self.submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        self.organization = self.submitter.organization_member.organization
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )
        self.currency = Currency.objects.create(code="GBP", name="British Pound")

        # Create organization member to use as added_by
        self.org_member = OrganizationMemberFactory(organization=self.organization)

        # Create OrganizationExchangeRate to associate currency with organization
        OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.00"),
            effective_date=date.today(),
            added_by=self.org_member,
        )

    def test_form_initialization_sets_allowed_entry_types(self):
        """Test form sets allowed entry types based on user role."""
        form = CreateWorkspaceTeamEntryForm(
            org_member=self.submitter.organization_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            workspace_team_member=self.submitter,
        )

        # Submitter should be able to create income, disbursement
        expected_choices = [
            (EntryType.INCOME, "Income"),
            (EntryType.DISBURSEMENT, "Disbursement"),
        ]

        assert form.fields["entry_type"].choices == expected_choices

    def test_form_initialization_with_workspace_admin(self):
        """Test form initialization with workspace admin (team coordinator)."""
        # Create team and set up coordinator properly
        team = TeamFactory(organization=self.organization)
        coordinator_org_member = OrganizationMemberFactory(
            organization=self.organization
        )

        # Set the coordinator on the team
        team.team_coordinator = coordinator_org_member
        team.save()

        # Create workspace team member for the coordinator
        coordinator_team_member = TeamMemberFactory(
            team=team,
            organization_member=coordinator_org_member,
            role=TeamMemberRole.SUBMITTER,  # Role doesn't matter, coordinator status comes from team.team_coordinator
        )

        # Update workspace team to use this team
        self.workspace_team.team = team
        self.workspace_team.save()

        form = CreateWorkspaceTeamEntryForm(
            org_member=coordinator_org_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            workspace_team_member=coordinator_team_member,
            is_team_coordinator=True,  # Explicitly set coordinator status
        )

        # Check that entry type choices include coordinator-specific types
        entry_type_choices = form.fields["entry_type"].choices
        entry_type_values = [choice[0] for choice in entry_type_choices]

        # Coordinator should have access to all entry types including REMITTANCE
        assert EntryType.INCOME in entry_type_values
        assert EntryType.DISBURSEMENT in entry_type_values
        assert EntryType.REMITTANCE in entry_type_values

    def test_clean_entry_type_valid_choice(self):
        """Test clean_entry_type with valid choice."""
        form_data = {
            "entry_type": EntryType.INCOME,
            "amount": "100.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = CreateWorkspaceTeamEntryForm(
            data=form_data,
            org_member=self.submitter.organization_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            workspace_team_member=self.submitter,
        )

        assert form.is_valid()

    def test_clean_entry_type_invalid_choice(self):
        """Test clean_entry_type with invalid choice for user role."""
        # For a submitter, we'll test with INCOME which is valid for the field choices
        # but we'll test the business logic validation by making the workspace expired
        # so that INCOME entries are not allowed

        # Set workspace end date to yesterday to trigger validation error

        self.workspace.end_date = date.today() - timedelta(days=1)
        self.workspace.save()

        form_data = {
            "entry_type": EntryType.INCOME,  # Valid choice but should be rejected due to expired workspace
            "amount": "100.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = CreateWorkspaceTeamEntryForm(
            data=form_data,
            org_member=self.submitter.organization_member,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            workspace_team_role=TeamMemberRole.SUBMITTER,
            workspace_team_member=self.submitter,
        )

        assert not form.is_valid()
        # Should get a validation error about workspace being expired
        assert "No more entries can be created for this workspace" in str(form.errors)

    # Note: User authorization validation is currently commented out in the form
    # def test_clean_validates_user_authorization(self):
    #     """Test clean method validates user authorization."""
    #     # This test is disabled because the authorization check is commented out in the form


@pytest.mark.unit
@pytest.mark.django_db
class TestBaseUpdateEntryForm:
    """Test BaseUpdateEntryForm functionality."""

    def setup_method(self):
        """Set up test data."""
        from datetime import date
        from decimal import Decimal

        from apps.organizations.models import OrganizationExchangeRate

        self.entry = PendingEntryFactory()
        self.organization = self.entry.organization

        # Create organization member to use as added_by
        self.org_member = OrganizationMemberFactory(organization=self.organization)

        # Associate the entry's currency with the organization
        OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.entry.currency,  # Use the entry's currency instead of creating a new one
            rate=Decimal("1.00"),
            effective_date=date.today(),
            added_by=self.org_member,
        )

    def test_form_initialization_with_pending_entry(self):
        """Test form initialization with pending entry allows editing."""
        form = BaseUpdateEntryForm(instance=self.entry, organization=self.organization)

        # Fields should be enabled for pending entries
        assert not form.fields["amount"].disabled
        assert not form.fields["description"].disabled
        assert not form.fields["currency"].disabled
        assert not form.fields["occurred_at"].disabled

    def test_form_initialization_with_approved_entry(self):
        """Test form initialization with approved entry disables fields."""
        approved_entry = ApprovedEntryFactory()

        form = BaseUpdateEntryForm(
            instance=approved_entry, organization=approved_entry.organization
        )

        # Fields should be disabled for non-pending entries
        assert form.fields["amount"].disabled
        assert form.fields["description"].disabled
        assert form.fields["currency"].disabled
        assert form.fields["occurred_at"].disabled

    def test_replace_attachments_field(self):
        """Test replace_attachments field is present."""
        form = BaseUpdateEntryForm(instance=self.entry, organization=self.organization)

        assert "replace_attachments" in form.fields
        assert form.fields["replace_attachments"].required is False

    def test_valid_status_transition_pending_to_reviewed(self):
        """Test valid status transition from pending to reviewed."""
        form_data = {
            "status": EntryStatus.REVIEWED,  # Valid transition from PENDING
            "amount": str(self.entry.amount),
            "description": self.entry.description,
            "currency": self.entry.currency.currency_id,
            "occurred_at": self.entry.occurred_at,
            "replace_attachments": False,
        }

        form = BaseUpdateEntryForm(
            data=form_data, instance=self.entry, organization=self.organization
        )

        assert form.is_valid()

    def test_invalid_status_transition(self):
        """Test invalid status transition is rejected."""
        # Create an approved entry and try to transition to pending (not allowed)
        approved_entry = ApprovedEntryFactory()

        form_data = {
            "status": EntryStatus.PENDING,  # Not allowed from APPROVED status
            "amount": str(approved_entry.amount),
            "description": approved_entry.description,
            "currency": approved_entry.currency.currency_id,
            "occurred_at": approved_entry.occurred_at,
            "replace_attachments": False,
        }

        form = BaseUpdateEntryForm(
            data=form_data,
            instance=approved_entry,
            organization=approved_entry.organization,
        )

        assert not form.is_valid()
        assert "status" in form.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestUpdateOrganizationExpenseEntryForm:
    """Test UpdateOrganizationExpenseEntryForm functionality."""

    def setup_method(self):
        """Set up test data."""

        self.org_member = OrganizationMemberFactory()
        self.organization = self.org_member.organization

        # Create currency and associate it with organization
        self.currency = Currency.objects.create(code="USD", name="US Dollar")
        OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.00"),
            effective_date=date.today(),
            added_by=self.org_member,
        )

        # Create entry with the organization's currency
        self.entry = EntryFactory(
            organization=self.organization,
            entry_type=EntryType.ORG_EXP,
            currency=self.currency,
        )

    def test_form_initialization_with_authorized_user(self):
        """Test form initializes for organization admin."""
        form = UpdateOrganizationExpenseEntryForm(
            instance=self.entry, organization=self.organization, is_org_admin=True
        )

        # Form should initialize successfully
        assert form.instance == self.entry

    def test_form_initialization_with_unauthorized_user(self):
        """Test form raises error for non-admin user."""
        form_data = {
            "status": EntryStatus.PENDING,
            "amount": str(self.entry.amount),
            "description": self.entry.description,
            "currency": self.entry.currency.currency_id,
            "occurred_at": self.entry.occurred_at,
            "replace_attachments": False,
        }

        form = UpdateOrganizationExpenseEntryForm(
            data=form_data,
            instance=self.entry,
            organization=self.organization,
            is_org_admin=False,
        )

        assert not form.is_valid()
        # Check non-field errors where authorization errors appear
        assert "You are not authorized to update organization expenses" in str(
            form.non_field_errors()
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestFormFieldValidation:
    """Test specific field validation across forms."""

    def setup_method(self):
        """Set up test data."""

        self.organization = OrganizationMemberFactory().organization
        self.currency = Currency.objects.create(code="JPY", name="Japanese Yen")

        # Create organization member to use as added_by
        self.org_member = OrganizationMemberFactory(organization=self.organization)

        # Create OrganizationExchangeRate to associate currency with organization
        OrganizationExchangeRate.objects.create(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.00"),
            effective_date=date.today(),
            added_by=self.org_member,
        )

    def test_amount_field_decimal_places(self):
        """Test amount field accepts proper decimal places."""
        form_data = {
            "amount": "100.99",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert form.is_valid()

    def test_amount_field_too_many_decimal_places(self):
        """Test amount field rejects too many decimal places."""
        form_data = {
            "amount": "100.999",  # 3 decimal places
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)

        # Django DecimalField with decimal_places=2 rejects values with more than 2 decimal places
        assert not form.is_valid()
        assert "amount" in form.errors
        assert "Ensure that there are no more than 2 decimal places" in str(
            form.errors["amount"]
        )

    def test_amount_field_max_digits_validation(self):
        """Test amount field rejects values exceeding max_digits=10."""
        form_data = {
            "amount": "12345678901.00",  # 11 digits before decimal + 2 after = 13 total (exceeds max_digits=10)
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert not form.is_valid()
        assert "amount" in form.errors

    def test_amount_field_max_valid_amount(self):
        """Test amount field accepts maximum valid amount."""
        form_data = {
            "amount": "99999999.99",  # 8 digits before decimal + 2 after = 10 total (max allowed)
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert form.is_valid()

    def test_amount_field_single_decimal_place(self):
        """Test amount field accepts single decimal place."""
        form_data = {
            "amount": "100.5",  # 1 decimal place
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert form.is_valid()
        if form.is_valid():
            from decimal import Decimal

            assert form.cleaned_data["amount"] == Decimal("100.50")

    def test_amount_field_no_decimal_places(self):
        """Test amount field accepts whole numbers."""
        form_data = {
            "amount": "100",  # No decimal places
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert form.is_valid()
        if form.is_valid():
            from decimal import Decimal

            assert form.cleaned_data["amount"] == Decimal("100.00")

    def test_occurred_at_field_date_format(self):
        """Test occurred_at field accepts valid date formats."""
        valid_dates = ["2023-01-01", "2023-12-31", "2022-02-28"]

        for date_str in valid_dates:
            form_data = {
                "amount": "100.00",
                "description": "Test entry",
                "currency": self.currency.currency_id,
                "occurred_at": date_str,
            }

            form = BaseEntryForm(data=form_data, organization=self.organization)
            assert form.is_valid(), f"Date {date_str} should be valid"

    def test_occurred_at_field_invalid_date(self):
        """Test occurred_at field rejects invalid dates."""
        invalid_dates = ["invalid-date", "2023-13-01", "2023-02-30"]

        for date_str in invalid_dates:
            form_data = {
                "amount": "100.00",
                "description": "Test entry",
                "currency": self.currency.currency_id,
                "occurred_at": date_str,
            }

            form = BaseEntryForm(data=form_data, organization=self.organization)
            assert not form.is_valid(), f"Date {date_str} should be invalid"
            assert "occurred_at" in form.errors

    def test_currency_field_valid_choice(self):
        """Test currency field accepts valid currency from organization."""
        form_data = {
            "amount": "100.00",
            "description": "Test entry",
            "currency": self.currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert form.is_valid()

    def test_currency_field_invalid_choice(self):
        """Test currency field rejects currency not in organization."""
        other_currency = Currency.objects.create(
            code="EUR", name="Euro"
        )  # Not added to organization

        form_data = {
            "amount": "100.00",
            "description": "Test entry",
            "currency": other_currency.currency_id,
            "occurred_at": "2023-01-01",
        }

        form = BaseEntryForm(data=form_data, organization=self.organization)
        assert not form.is_valid()
        assert "currency" in form.errors
