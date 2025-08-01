"""
Unit tests for workspace services.

Tests the business logic functions in apps.workspaces.services module.
Focuses on real database operations with minimal mocking.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.currencies.models import Currency
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.workspaces.models import WorkspaceTeam, WorkspaceExchangeRate
from apps.workspaces.services import (
    create_workspace_from_form,
    update_workspace_from_form,
    remove_team_from_workspace,
    add_team_to_workspace,
    update_workspace_team_remittance_rate_from_form,
    create_workspace_exchange_rate,
    update_workspace_exchange_rate,
    delete_workspace_exchange_rate,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceExchangeRateFactory,
)


@pytest.mark.unit
class TestWorkspaceServices(TestCase):
    """Test workspace service functions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    @pytest.mark.django_db
    def test_create_workspace_from_form_success(self):
        """Test successful workspace creation from form."""
        # Mock form
        mock_form = Mock()
        mock_workspace = WorkspaceFactory.build(organization=self.organization)
        mock_form.save.return_value = mock_workspace

        with patch(
            "apps.workspaces.services.assign_workspace_permissions"
        ) as mock_assign:
            result = create_workspace_from_form(
                form=mock_form,
                orgMember=self.org_member,
                organization=self.organization,
            )

            # Verify form.save was called with commit=False
            mock_form.save.assert_called_once_with(commit=False)

            # Verify workspace attributes were set
            self.assertEqual(result.organization, self.organization)
            self.assertEqual(result.created_by, self.org_member)

            # Verify permissions were assigned
            mock_assign.assert_called_once_with(result)

    @pytest.mark.django_db
    def test_create_workspace_from_form_failure(self):
        """Test workspace creation failure."""
        mock_form = Mock()
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(WorkspaceCreationError) as context:
            create_workspace_from_form(
                form=mock_form,
                orgMember=self.org_member,
                organization=self.organization,
            )

        self.assertIn("Failed to create workspace", str(context.exception))

    @pytest.mark.django_db
    def test_update_workspace_from_form_success(self):
        """Test successful workspace update from form."""
        workspace = WorkspaceFactory(organization=self.organization)
        previous_admin = OrganizationMemberFactory(organization=self.organization)
        previous_reviewer = OrganizationMemberFactory(organization=self.organization)
        new_admin = OrganizationMemberFactory(organization=self.organization)
        new_reviewer = OrganizationMemberFactory(organization=self.organization)

        mock_form = Mock()
        mock_form.cleaned_data = {
            "title": "Updated Title",
            "workspace_admin": new_admin,
            "operations_reviewer": new_reviewer,
        }

        with (
            patch("apps.workspaces.services.model_update") as mock_update,
            patch(
                "apps.workspaces.services.update_workspace_admin_group"
            ) as mock_update_group,
        ):
            mock_update.return_value = workspace

            result = update_workspace_from_form(
                form=mock_form,
                workspace=workspace,
                previous_workspace_admin=previous_admin,
                previous_operations_reviewer=previous_reviewer,
            )

            mock_update.assert_called_once_with(workspace, mock_form.cleaned_data)
            mock_update_group.assert_called_once_with(
                workspace, previous_admin, new_admin, previous_reviewer, new_reviewer
            )
            self.assertEqual(result, workspace)

    @pytest.mark.django_db
    def test_update_workspace_from_form_failure(self):
        """Test workspace update failure."""
        workspace = WorkspaceFactory()
        mock_form = Mock()
        mock_form.cleaned_data = {}

        with patch("apps.workspaces.services.model_update") as mock_update:
            mock_update.side_effect = Exception("Update error")

            with self.assertRaises(WorkspaceUpdateError) as context:
                update_workspace_from_form(
                    form=mock_form,
                    workspace=workspace,
                    previous_workspace_admin=None,
                    previous_operations_reviewer=None,
                )

            self.assertIn("Failed to update workspace", str(context.exception))

    @pytest.mark.django_db
    def test_remove_team_from_workspace_success(self):
        """Test successful team removal from workspace."""
        workspace_team = WorkspaceTeamFactory()
        workspace_id = workspace_team.workspace.workspace_id
        team_id = workspace_team.team.team_id

        result = remove_team_from_workspace(workspace_id, team_id)

        # Verify the returned object has the same attributes as the original
        self.assertEqual(result.workspace_id, workspace_team.workspace_id)
        self.assertEqual(result.team_id, workspace_team.team_id)
        self.assertIsInstance(result, WorkspaceTeam)
        self.assertFalse(
            WorkspaceTeam.objects.filter(
                workspace_id=workspace_id, team_id=team_id
            ).exists()
        )

    @pytest.mark.django_db
    def test_remove_team_from_workspace_not_found(self):
        """Test team removal when workspace team doesn't exist."""
        workspace = WorkspaceFactory()
        team = TeamFactory()

        with self.assertRaises(WorkspaceTeam.DoesNotExist):
            remove_team_from_workspace(workspace.workspace_id, team.team_id)

    @pytest.mark.django_db
    def test_add_team_to_workspace_success(self):
        """Test successful team addition to workspace."""
        workspace = WorkspaceFactory()
        team = TeamFactory(organization=workspace.organization)
        custom_rate = Decimal("85.00")

        result = add_team_to_workspace(
            workspace.workspace_id, team.team_id, custom_rate
        )

        self.assertIsInstance(result, WorkspaceTeam)
        self.assertEqual(result.workspace, workspace)
        self.assertEqual(result.team, team)
        self.assertEqual(result.custom_remittance_rate, custom_rate)

    @pytest.mark.django_db
    def test_add_team_to_workspace_duplicate(self):
        """Test adding team that already exists in workspace."""
        workspace_team = WorkspaceTeamFactory()

        with self.assertRaises(IntegrityError):
            add_team_to_workspace(
                workspace_team.workspace.workspace_id, workspace_team.team.team_id, None
            )

    @pytest.mark.django_db
    def test_update_workspace_team_remittance_rate_success(self):
        """Test successful workspace team remittance rate update."""
        workspace = WorkspaceFactory(remittance_rate=Decimal("90.00"))
        workspace_team = WorkspaceTeamFactory(workspace=workspace)

        mock_form = Mock()
        mock_form.cleaned_data = {"custom_remittance_rate": Decimal("85.00")}

        with patch("apps.workspaces.services.model_update") as mock_update:
            mock_update.return_value = workspace_team
            workspace_team.custom_remittance_rate = Decimal("85.00")

            result = update_workspace_team_remittance_rate_from_form(
                form=mock_form, workspace_team=workspace_team, workspace=workspace
            )

            mock_update.assert_called_once_with(workspace_team, mock_form.cleaned_data)
            self.assertEqual(result.custom_remittance_rate, Decimal("85.00"))

    @pytest.mark.django_db
    def test_update_workspace_team_remittance_rate_same_as_workspace(self):
        """Test workspace team remittance rate update when same as workspace default."""
        workspace = WorkspaceFactory(remittance_rate=Decimal("90.00"))
        workspace_team = WorkspaceTeamFactory(workspace=workspace)

        mock_form = Mock()
        mock_form.cleaned_data = {"custom_remittance_rate": Decimal("90.00")}

        with patch("apps.workspaces.services.model_update") as mock_update:
            mock_update.return_value = workspace_team
            workspace_team.custom_remittance_rate = Decimal("90.00")

            result = update_workspace_team_remittance_rate_from_form(
                form=mock_form, workspace_team=workspace_team, workspace=workspace
            )

            # Should be set to None when same as workspace default
            self.assertIsNone(result.custom_remittance_rate)


@pytest.mark.unit
class TestWorkspaceExchangeRateServices(TestCase):
    """Test workspace exchange rate service functions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    @pytest.mark.django_db
    def test_create_workspace_exchange_rate_success(self):
        """Test successful workspace exchange rate creation."""
        currency_code = "EUR"
        rate = Decimal("1.20")
        note = "Test exchange rate"
        effective_date = date.today()

        create_workspace_exchange_rate(
            workspace=self.workspace,
            organization_member=self.org_member,
            currency_code=currency_code,
            rate=rate,
            note=note,
            effective_date=effective_date,
        )

        # Verify exchange rate was created
        exchange_rate = WorkspaceExchangeRate.objects.get(
            workspace=self.workspace, currency__code=currency_code
        )
        self.assertEqual(exchange_rate.rate, rate)
        self.assertEqual(exchange_rate.note, note)
        self.assertEqual(exchange_rate.effective_date, effective_date)
        self.assertEqual(exchange_rate.added_by, self.org_member)

        # Verify currency was created
        currency = Currency.objects.get(code=currency_code)
        self.assertEqual(currency.code, currency_code)

    @pytest.mark.django_db
    def test_create_workspace_exchange_rate_existing_currency(self):
        """Test workspace exchange rate creation with existing currency."""
        currency = Currency.objects.create(code="GBP", name="British Pound")
        rate = Decimal("1.30")

        create_workspace_exchange_rate(
            workspace=self.workspace,
            organization_member=self.org_member,
            currency_code=currency.code,
            rate=rate,
            note="Test rate",
            effective_date=date.today(),
        )

        # Should use existing currency
        exchange_rate = WorkspaceExchangeRate.objects.get(
            workspace=self.workspace, currency=currency
        )
        self.assertEqual(exchange_rate.currency, currency)

    @pytest.mark.django_db
    def test_create_workspace_exchange_rate_duplicate(self):
        """Test workspace exchange rate creation with duplicate constraint."""
        currency_code = "USD"
        effective_date = date.today()

        # Create first exchange rate
        create_workspace_exchange_rate(
            workspace=self.workspace,
            organization_member=self.org_member,
            currency_code=currency_code,
            rate=Decimal("1.00"),
            note="First rate",
            effective_date=effective_date,
        )

        # Try to create duplicate
        with self.assertRaises(ValidationError) as context:
            create_workspace_exchange_rate(
                workspace=self.workspace,
                organization_member=self.org_member,
                currency_code=currency_code,
                rate=Decimal("1.10"),
                note="Duplicate rate",
                effective_date=effective_date,
            )

        self.assertIn(
            "Failed to create workspace exchange rate", str(context.exception)
        )

    @pytest.mark.django_db
    def test_update_workspace_exchange_rate_success(self):
        """Test successful workspace exchange rate update."""
        exchange_rate = WorkspaceExchangeRateFactory(workspace=self.workspace)
        approver = OrganizationMemberFactory(organization=self.organization)
        new_note = "Updated note"

        with patch("apps.workspaces.services.model_update") as mock_update:
            mock_update.return_value = exchange_rate

            result = update_workspace_exchange_rate(
                workspace_exchange_rate=exchange_rate,
                note=new_note,
                is_approved=True,
                org_member=approver,
            )

            expected_data = {
                "note": new_note,
                "is_approved": True,
                "approved_by": approver,
            }
            mock_update.assert_called_once_with(exchange_rate, expected_data)
            self.assertEqual(result, exchange_rate)

    @pytest.mark.django_db
    def test_update_workspace_exchange_rate_not_approved(self):
        """Test workspace exchange rate update when not approved."""
        exchange_rate = WorkspaceExchangeRateFactory(workspace=self.workspace)
        new_note = "Updated note"

        with patch("apps.workspaces.services.model_update") as mock_update:
            mock_update.return_value = exchange_rate

            update_workspace_exchange_rate(
                workspace_exchange_rate=exchange_rate,
                note=new_note,
                is_approved=False,
                org_member=self.org_member,
            )

            expected_data = {
                "note": new_note,
                "is_approved": False,
                "approved_by": None,
            }
            mock_update.assert_called_once_with(exchange_rate, expected_data)

    @pytest.mark.django_db
    def test_update_workspace_exchange_rate_failure(self):
        """Test workspace exchange rate update failure."""
        exchange_rate = WorkspaceExchangeRateFactory()

        with patch("apps.workspaces.services.model_update") as mock_update:
            mock_update.side_effect = Exception("Update error")

            with self.assertRaises(ValidationError) as context:
                update_workspace_exchange_rate(
                    workspace_exchange_rate=exchange_rate,
                    note="New note",
                    is_approved=True,
                    org_member=self.org_member,
                )

            self.assertIn(
                "Failed to update workspace exchange rate", str(context.exception)
            )

    @pytest.mark.django_db
    def test_delete_workspace_exchange_rate_success(self):
        """Test successful workspace exchange rate deletion."""
        exchange_rate = WorkspaceExchangeRateFactory()
        exchange_rate_id = exchange_rate.workspace_exchange_rate_id

        delete_workspace_exchange_rate(workspace_exchange_rate=exchange_rate)

        # Should be soft deleted
        self.assertFalse(
            WorkspaceExchangeRate.objects.filter(
                workspace_exchange_rate_id=exchange_rate_id
            ).exists()
        )

    @pytest.mark.django_db
    def test_delete_workspace_exchange_rate_failure(self):
        """Test workspace exchange rate deletion failure."""
        exchange_rate = WorkspaceExchangeRateFactory()

        with patch.object(exchange_rate, "delete") as mock_delete:
            mock_delete.side_effect = Exception("Delete error")

            with self.assertRaises(ValidationError) as context:
                delete_workspace_exchange_rate(workspace_exchange_rate=exchange_rate)

            self.assertIn(
                "Failed to delete workspace exchange rate", str(context.exception)
            )
