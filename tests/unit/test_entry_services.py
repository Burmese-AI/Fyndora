"""
Fresh pytest unit tests for EntryService static methods.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import BaseServiceError, BulkOperationError
from apps.currencies.models import Currency
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.entries.services import EntryService, EntryServiceError

# Import related models for setup (if needed for object creation in fixtures)
from apps.organizations.models import Organization, OrganizationExchangeRate
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam
from django.contrib.auth import get_user_model
from tests.factories.organization_factories import OrganizationExchangeRateFactory
from tests.factories.workspace_factories import WorkspaceExchangeRateFactory

# Import factories for quick data creation
from tests.factories import (
    EntryFactory,
    OrganizationMemberFactory,
    OrganizationWithOwnerFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


User = get_user_model()


# --- Pytest Fixtures for common setup ---

@pytest.fixture
@pytest.mark.django_db
def setup_common_models():
    """Fixture to create common model instances for tests, including currencies and exchange rates."""
    organization = OrganizationWithOwnerFactory()
    workspace = WorkspaceFactory(organization=organization)
    workspace_team = WorkspaceTeamFactory(workspace=workspace)
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    org_member = OrganizationMemberFactory(organization=organization, user=user)
    team_member = TeamMemberFactory(organization_member=org_member, team=workspace_team.team)

    # Create or get currencies
    currency_usd, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar"})
    currency_eur, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})

    # Create Organization Exchange Rates for these currencies
    org_exchange_rate_usd = OrganizationExchangeRateFactory(
        organization=organization,
        currency=currency_usd,
        rate=Decimal("1.00"),
        effective_date=date.today(),
        added_by=org_member,
    )

    org_exchange_rate_eur = OrganizationExchangeRateFactory(
        organization=organization,
        currency=currency_eur,
        rate=Decimal("0.85"),
        effective_date=date.today(),
        added_by=org_member,
    )

    # Optional: Create a Workspace Exchange Rate (if your logic ever uses it)
    workspace_exchange_rate_usd = WorkspaceExchangeRateFactory(
        workspace=workspace,
        currency=currency_usd,
        rate=Decimal("1.02"),
        effective_date=date.today(),
        added_by=org_member,
    )

    

    return {
        "organization": organization,
        "workspace": workspace,
        "workspace_team": workspace_team,
        "currency_usd": currency_usd,
        "currency_eur": currency_eur,
        "org_exchange_rate_usd": org_exchange_rate_usd,  # 👈 Added
        "org_exchange_rate_eur": org_exchange_rate_eur,  # 👈 Added
        "workspace_exchange_rate_usd": workspace_exchange_rate_usd,  # Optional
        "user": user,
        "org_member": org_member,
        "team_member": team_member,
    }

@pytest.fixture
def mock_external_dependencies():
    """
    Fixture to patch external service dependencies globally for the test function.
    Returns a dictionary of mock objects for easy access.
    """
    with patch("apps.entries.services.get_currency_by_code", autospec=True) as mock_get_currency, \
         patch("apps.entries.services.get_closest_exchanged_rate", autospec=True) as mock_get_exchange_rate, \
         patch("apps.entries.services.create_attachments", autospec=True) as mock_create_attachments, \
         patch("apps.entries.services.replace_or_append_attachments", autospec=True) as mock_replace_or_append_attachments, \
         patch("apps.entries.services.BusinessAuditLogger", autospec=True) as mock_audit_logger, \
         patch("django.db.transaction.atomic", autospec=True) as mock_transaction_atomic:

        # Configure mock_transaction_atomic to behave like a context manager
        mock_transaction_atomic.return_value.__enter__.return_value = None
        mock_transaction_atomic.return_value.__exit__.return_value = None

        yield {
            "get_currency_by_code": mock_get_currency,
            "get_closest_exchanged_rate": mock_get_exchange_rate,
            "create_attachments": mock_create_attachments,
            "replace_or_append_attachments": mock_replace_or_append_attachments,
            "audit_logger": mock_audit_logger,
            "transaction_atomic": mock_transaction_atomic,
        }

@pytest.mark.django_db
def test_build_entry_success(setup_common_models, mock_external_dependencies):
    """Test that build_entry creates an Entry object correctly with valid inputs."""
    models = setup_common_models
    mocks = mock_external_dependencies

    # --- ARRANGE ---
    # Configure mocks to return real model instances from the fixture
    mocks["get_currency_by_code"].return_value = models["currency_usd"]
    mocks["get_closest_exchanged_rate"].return_value = models["org_exchange_rate_usd"]

    # Define explicit input parameters
    test_amount = Decimal("100.00")
    test_occurred_at = date.today()
    test_description = "Test Entry Description"
    test_entry_type = EntryType.INCOME

    # --- ACT ---
    entry = EntryService.build_entry(
        currency_code="USD",
        amount=test_amount,
        occurred_at=test_occurred_at,
        description=test_description,
        entry_type=test_entry_type,
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        submitted_by_org_member=models["org_member"],
        submitted_by_team_member=models["team_member"],
    )

    # --- ASSERT ---
    # 1. Verify an Entry object is returned
    assert isinstance(entry, Entry)

    # 2. Verify input fields
    assert entry.amount == test_amount
    assert entry.entry_type == test_entry_type
    assert entry.organization == models["organization"]
    assert entry.workspace == models["workspace"]
    assert entry.workspace_team == models["workspace_team"]
    assert entry.description == test_description
    assert entry.occurred_at == test_occurred_at
    assert entry.submitted_by_org_member == models["org_member"]
    assert entry.submitted_by_team_member == models["team_member"]

    # 3. Verify derived fields from service logic
    assert entry.currency == models["currency_usd"]  # From get_currency_by_code
    assert entry.exchange_rate_used == models["org_exchange_rate_usd"].rate  # From get_closest_exchanged_rate
    assert entry.org_exchange_rate_ref == models["org_exchange_rate_usd"]  # Correct reference set
    assert entry.workspace_exchange_rate_ref is None  # Because it's an OrgExchangeRate
    assert entry.is_flagged is True  # Default for new entries
    assert entry.status == EntryStatus.PENDING  # Default status

    # 4. Verify external dependencies were called correctly
    mocks["get_currency_by_code"].assert_called_once_with("USD")
    mocks["get_closest_exchanged_rate"].assert_called_once_with(
        currency=models["currency_usd"],
        occurred_at=test_occurred_at,
        organization=models["organization"],
        workspace=models["workspace"],
    )
    
@pytest.mark.django_db
def test_bulk_create_entry_success(setup_common_models):
    """Test that bulk_create_entry successfully saves multiple Entry objects to the database."""
    models = setup_common_models

    # --- ARRANGE ---
    # Create unsaved Entry instances using build_entry (or manually)
    entry1 = Entry(
        entry_type=EntryType.INCOME,
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        description="First test entry",
        amount=Decimal("100.00"),
        occurred_at=date.today(),
        currency=models["currency_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
        is_flagged=True,
    )

    entry2 = Entry(
        entry_type=EntryType.ORG_EXP,
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        description="Second test entry",
        amount=Decimal("50.00"),
        occurred_at=date.today(),
        currency=models["currency_eur"],
        exchange_rate_used=models["org_exchange_rate_eur"].rate,
        org_exchange_rate_ref=models["org_exchange_rate_eur"],
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
        is_flagged=True,
    )

    # --- ACT ---
    created_entries = EntryService.bulk_create_entry(entries=[entry1, entry2])

    # --- ASSERT ---
    assert len(created_entries) == 2
    assert Entry.objects.count() == 2

    # Verify first entry
    db_entry1 = Entry.objects.get(description="First test entry")
    assert db_entry1.amount == Decimal("100.00")
    assert db_entry1.currency == models["currency_usd"]
    assert db_entry1.org_exchange_rate_ref == models["org_exchange_rate_usd"]

    # Verify second entry
    db_entry2 = Entry.objects.get(description="Second test entry")
    assert db_entry2.amount == Decimal("50.00")
    assert db_entry2.currency == models["currency_eur"]
    assert db_entry2.org_exchange_rate_ref == models["org_exchange_rate_eur"]
    
@pytest.mark.django_db
def test_bulk_create_entry_raises_entry_service_error_on_db_exception(setup_common_models):
    """Test that bulk_create_entry raises EntryServiceError if database integrity is violated."""
    models = setup_common_models

    # --- ARRANGE ---
    # Create an Entry with a required field missing (e.g., no organization)
    bad_entry = Entry(
        entry_type=EntryType.INCOME,
        # organization=models["organization"],  # ← Intentionally omitted to trigger error
        workspace=models["workspace"],
        description="Invalid entry",
        amount=Decimal("100.00"),
        occurred_at=date.today(),
        currency=models["currency_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
        is_flagged=True,
    )

    # --- ACT & ASSERT ---
    with pytest.raises(BulkOperationError):
        with transaction.atomic():
            EntryService.bulk_create_entry(entries=[bad_entry])

    assert Entry.objects.count() == 0
    
@pytest.mark.django_db
def test_create_entry_without_attachments_success(setup_common_models, mock_external_dependencies):
    """Test that create_entry_with_attachments creates an Entry and calls attachments + audit logger."""
    models = setup_common_models
    mocks = mock_external_dependencies

    # --- ARRANGE ---
    test_amount = Decimal("123.45")
    test_occurred_at = date.today()
    test_description = "Entry with attachments"

    # Mock exchange rate return
    mocks["get_closest_exchanged_rate"].return_value = models["org_exchange_rate_usd"]

    # --- ACT ---
    entry = EntryService.create_entry_with_attachments(
        amount=test_amount,
        occurred_at=test_occurred_at,
        description=test_description,
        attachments=[],
        entry_type=EntryType.INCOME,
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        submitted_by_org_member=models["org_member"],
        submitted_by_team_member=models["team_member"],
        user=models["user"],
        request=Mock(),
    )

    # --- ASSERT ---
    # Entry persisted
    assert Entry.objects.count() == 1
    db_entry = Entry.objects.first()
    assert db_entry == entry
    assert db_entry.amount == test_amount
    assert db_entry.currency == models["currency_usd"]
    assert db_entry.org_exchange_rate_ref == models["org_exchange_rate_usd"]
    assert db_entry.is_flagged is True


    # Audit log called
    mocks["audit_logger"].log_entry_action.assert_called_once()
    call_kwargs = mocks["audit_logger"].log_entry_action.call_args.kwargs
    assert call_kwargs["user"] == models["user"]
    assert call_kwargs["entry"] == entry
    assert call_kwargs["action"] == "submit"
    assert call_kwargs["currency_code"] == "USD"
    assert call_kwargs["attachment_count"] == 0


@pytest.mark.django_db
def test_create_entry_without_attachments_no_exchange_rate(setup_common_models, mock_external_dependencies):
    """Test that ValueError is raised if no exchange rate is found."""
    models = setup_common_models
    mocks = mock_external_dependencies

    # Mock to return None
    mocks["get_closest_exchanged_rate"].return_value = None

    with pytest.raises(BaseServiceError) as exc_info:
        EntryService.create_entry_with_attachments(
            amount=Decimal("50.00"),
            occurred_at=date.today(),
            description="No exchange rate",
            attachments=[],
            entry_type=EntryType.INCOME,
            organization=models["organization"],
            workspace=models["workspace"],
            workspace_team=models["workspace_team"],
            submitted_by_org_member=models["org_member"],
            submitted_by_team_member=models["team_member"],
            user=models["user"],
            request=Mock(),
            currency=models["currency_usd"],
        )

@pytest.mark.django_db
def test_update_entry_user_inputs_success(setup_common_models, mock_external_dependencies):
    """Test that update_entry_user_inputs updates fields, attachments, and logs properly."""
    models = setup_common_models
    mocks = mock_external_dependencies
    request_mock = Mock()

    # --- ARRANGE ---
    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
        is_flagged=True,
    )

    new_amount = Decimal("250.00")
    new_description = "Updated entry"
    new_occurred_at = date.today() - timedelta(days=1)
    new_currency = models["currency_eur"]

    # Make exchange rate lookup return the EUR rate
    mocks["get_closest_exchanged_rate"].return_value = models["org_exchange_rate_eur"]

    fake_attachments = [{"name": "new_file.pdf"}]

    # --- ACT ---
    EntryService.update_entry_user_inputs(
        entry=entry,
        organization=models["organization"],
        workspace=models["workspace"],
        amount=new_amount,
        occurred_at=new_occurred_at,
        description=new_description,
        currency=new_currency,
        attachments=fake_attachments,
        replace_attachments=True,
        user=models["user"],
        request=request_mock,
    )

    # --- REFRESH & ASSERT ---
    entry.refresh_from_db()
    assert entry.amount == new_amount
    assert entry.description == new_description
    assert entry.currency == new_currency
    assert entry.exchange_rate_used == models["org_exchange_rate_eur"].rate
    assert entry.org_exchange_rate_ref == models["org_exchange_rate_eur"]
    assert entry.is_flagged is False  # was cleared since attachments added

    mocks["replace_or_append_attachments"].assert_called_once_with(
        entry=entry,
        attachments=fake_attachments,
        replace_attachments=True,
        user=models["user"],
        request=request_mock,
    )

    mocks["audit_logger"].log_entry_action.assert_called_once()
    log_kwargs = mocks["audit_logger"].log_entry_action.call_args.kwargs
    assert log_kwargs["action"] == "update"
    assert log_kwargs["currency_changed"] is True
    assert log_kwargs["occurred_at_changed"] is True
    assert log_kwargs["exchange_rate_updated"] is True
    assert log_kwargs["attachments_updated"] is True


@pytest.mark.django_db
def test_update_entry_user_inputs_raises_if_not_pending(setup_common_models, mock_external_dependencies):
    """Test that update_entry_user_inputs raises ValidationError if entry is not pending."""
    models = setup_common_models

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.APPROVED,  # ❌ Not pending
    )

    with pytest.raises(BaseServiceError):
        EntryService.update_entry_user_inputs(
            entry=entry,
            organization=models["organization"],
            workspace=models["workspace"],
            amount=Decimal("123.00"),
            occurred_at=entry.occurred_at,
            description="Should fail",
            currency=models["currency_usd"],
            attachments=[],
            replace_attachments=False,
            user=models["user"],
            request=Mock(),
        )


@pytest.mark.django_db
def test_bulk_update_entry_status_success(setup_common_models):
    """Test that bulk_update_entry_status successfully updates multiple Entry objects."""
    models = setup_common_models

    # --- ARRANGE ---
    entry1 = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    entry2 = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    # Change values in memory (not saved yet)
    entry1.status = EntryStatus.APPROVED
    entry1.status_note = "Approved in bulk"
    entry2.status = EntryStatus.REJECTED
    entry2.status_note = "Rejected in bulk"

    # --- ACT ---
    updated_entries = EntryService.bulk_update_entry_status(
        entries=[entry1, entry2],
        request=Mock(),
    )

    # --- ASSERT ---
    assert len(updated_entries) == 2

    # Reload from DB to confirm persistence
    entry1.refresh_from_db()
    entry2.refresh_from_db()

    assert entry1.status == EntryStatus.APPROVED
    assert entry1.status_note == "Approved in bulk"
    assert entry2.status == EntryStatus.REJECTED
    assert entry2.status_note == "Rejected in bulk"


@pytest.mark.django_db
def test_bulk_update_entry_status_raises_error(monkeypatch, setup_common_models):
    """Test that bulk_update_entry_status raises EntryServiceError if bulk_update fails."""
    models = setup_common_models

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    # Monkeypatch bulk_update to raise an Exception
    def fake_bulk_update(*args, **kwargs):
        raise Exception("DB error")

    monkeypatch.setattr(Entry.objects, "bulk_update", fake_bulk_update)

    with pytest.raises(EntryServiceError):
        EntryService.bulk_update_entry_status(entries=[entry])


@pytest.mark.django_db
def test_bulk_update_entry_status_success(setup_common_models):
    """Test that bulk_update_entry_status successfully updates multiple Entry objects."""
    models = setup_common_models

    # --- ARRANGE ---
    entry1 = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    entry2 = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    # Update fields in memory
    entry1.status = EntryStatus.APPROVED
    entry1.status_note = "Bulk approved"
    entry2.status = EntryStatus.REJECTED
    entry2.status_note = "Bulk rejected"

    # --- ACT ---
    updated_entries = EntryService.bulk_update_entry_status(
        entries=[entry1, entry2],
        request=Mock(),
    )

    # --- ASSERT ---
    assert len(updated_entries) == 2

    entry1.refresh_from_db()
    entry2.refresh_from_db()

    assert entry1.status == EntryStatus.APPROVED
    assert entry1.status_note == "Bulk approved"
    assert entry2.status == EntryStatus.REJECTED
    assert entry2.status_note == "Bulk rejected"


@pytest.mark.django_db
def test_bulk_update_entry_status_raises_service_error(monkeypatch, setup_common_models):
    """Test that bulk_update_entry_status raises EntryServiceError when bulk_update fails."""
    models = setup_common_models

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    # Monkeypatch to force failure
    def fake_bulk_update(*args, **kwargs):
        raise Exception("DB error")

    monkeypatch.setattr(Entry.objects, "bulk_update", fake_bulk_update)

    with pytest.raises(EntryServiceError):
        EntryService.bulk_update_entry_status(entries=[entry])

@pytest.mark.django_db
def test_delete_entry_success_with_user(setup_common_models, mock_external_dependencies):
    """Test that delete_entry deletes the entry and logs the deletion if user is provided."""
    models = setup_common_models
    mocks = mock_external_dependencies

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    # --- ACT ---
    deleted_entry = EntryService.delete_entry(
        entry=entry,
        user=models["user"],
        request=Mock(),
    )

    # --- ASSERT ---
    assert deleted_entry == entry
    assert Entry.objects.filter(pk=entry.pk).count() == 0

    mocks["audit_logger"].log_entry_action.assert_called_once()
    log_kwargs = mocks["audit_logger"].log_entry_action.call_args.kwargs
    assert log_kwargs["action"] == "delete"
    assert log_kwargs["entry"] == entry
    assert log_kwargs["entry_status"] == EntryStatus.PENDING
    assert log_kwargs["deletion_reason"] == "user_initiated"


@pytest.mark.django_db
def test_delete_entry_success_without_user(setup_common_models, mock_external_dependencies):
    """Test that delete_entry deletes the entry without logging if user is None."""
    models = setup_common_models
    mocks = mock_external_dependencies

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
    )

    EntryService.delete_entry(entry=entry, user=None, request=Mock())

    assert Entry.objects.filter(pk=entry.pk).count() == 0
    mocks["audit_logger"].log_entry_action.assert_not_called()


@pytest.mark.django_db
def test_delete_entry_raises_if_status_modified(setup_common_models):
    """Test that delete_entry raises error if entry.last_status_modified_by is set."""
    models = setup_common_models

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.PENDING,
        last_status_modified_by=models["org_member"],  # ❌ should block deletion
    )

    with pytest.raises(EntryServiceError, match="already modified the status"):
        EntryService.delete_entry(entry=entry, user=models["user"], request=Mock())

    assert Entry.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
def test_delete_entry_raises_if_not_pending(setup_common_models):
    """Test that delete_entry raises error if entry.status is not pending."""
    models = setup_common_models

    entry = EntryFactory(
        organization=models["organization"],
        workspace=models["workspace"],
        workspace_team=models["workspace_team"],
        currency=models["currency_usd"],
        org_exchange_rate_ref=models["org_exchange_rate_usd"],
        exchange_rate_used=models["org_exchange_rate_usd"].rate,
        submitted_by_org_member=models["org_member"],
        status=EntryStatus.APPROVED,  # ❌ should block deletion
    )

    with pytest.raises(EntryServiceError, match="not pending review"):
        EntryService.delete_entry(entry=entry, user=models["user"], request=Mock())

    assert Entry.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
def test_bulk_delete_entries_success_with_user(setup_common_models, mock_external_dependencies):
    """Test that bulk_delete_entries deletes all entries and logs when user is provided."""
    models = setup_common_models
    mocks = mock_external_dependencies

    entries = [
        EntryFactory(
            organization=models["organization"],
            workspace=models["workspace"],
            workspace_team=models["workspace_team"],
            currency=models["currency_usd"],
            org_exchange_rate_ref=models["org_exchange_rate_usd"],
            exchange_rate_used=models["org_exchange_rate_usd"].rate,
            submitted_by_org_member=models["org_member"],
            status=EntryStatus.PENDING,
        )
        for _ in range(2)
    ]

    EntryService.bulk_delete_entries(entries=Entry.objects.filter(pk__in=[e.pk for e in entries]),
                                     user=models["user"],
                                     request=Mock())

    # All deleted
    assert Entry.objects.count() == 0


@pytest.mark.django_db
def test_bulk_delete_entries_success_without_user(setup_common_models, mock_external_dependencies):
    """Test that bulk_delete_entries deletes entries without logging when user is None."""
    models = setup_common_models
    mocks = mock_external_dependencies

    entries = [
        EntryFactory(
            organization=models["organization"],
            workspace=models["workspace"],
            workspace_team=models["workspace_team"],
            currency=models["currency_usd"],
            org_exchange_rate_ref=models["org_exchange_rate_usd"],
            exchange_rate_used=models["org_exchange_rate_usd"].rate,
            submitted_by_org_member=models["org_member"],
            status=EntryStatus.PENDING,
        )
        for _ in range(2)
    ]

    EntryService.bulk_delete_entries(entries=Entry.objects.filter(pk__in=[e.pk for e in entries]),
                                     user=None,
                                     request=Mock())

    assert Entry.objects.count() == 0