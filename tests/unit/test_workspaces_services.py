"""
Unit tests for workspace services.

Tests cover:
- Workspace creation, update, and management
- Team addition/removal from workspaces
- Remittance rate updates
- Exchange rate creation, update, and deletion
- Error handling and audit logging
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

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
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.workspaces.models import Workspace, WorkspaceTeam, WorkspaceExchangeRate
from apps.currencies.models import Currency
from tests.factories.organization_factories import (
    OrganizationMemberFactory,
    OrganizationWithOwnerFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory
from tests.factories.user_factories import CustomUserFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceExchangeRateFactory,
)


@pytest.mark.unit
class TestCreateWorkspaceFromForm(TestCase):
    """Test workspace creation from form."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.user = self.org_member.user

    @pytest.mark.django_db
    def test_create_workspace_success(self):
        """Test successful workspace creation."""
        # Mock form
        mock_form = Mock()
        mock_form.save.return_value = WorkspaceFactory.build(
            organization=self.organization
        )
        mock_form.cleaned_data = {"title": "Test Workspace"}

        with patch(
            "apps.workspaces.services.assign_workspace_permissions"
        ) as mock_assign:
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_action"
            ) as mock_log:
                result = create_workspace_from_form(
                    form=mock_form,
                    orgMember=self.org_member,
                    organization=self.organization,
                )

                self.assertIsInstance(result, Workspace)
                mock_assign.assert_called_once()
                mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_create_workspace_without_org_member(self):
        """Test workspace creation without organization member."""
        # Mock form
        mock_form = Mock()
        mock_form.save.return_value = WorkspaceFactory.build(
            organization=self.organization
        )
        mock_form.cleaned_data = {"title": "Test Workspace"}

        with patch(
            "apps.workspaces.services.assign_workspace_permissions"
        ) as mock_assign:
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_action"
            ) as mock_log:
                result = create_workspace_from_form(
                    form=mock_form,
                    orgMember=None,
                    organization=self.organization,
                )

                self.assertIsInstance(result, Workspace)
                mock_assign.assert_called_once()
                # Should not log when no org member
                mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_create_workspace_form_save_error(self):
        """Test workspace creation when form save fails."""
        # Mock form that raises an error
        mock_form = Mock()
        mock_form.save.side_effect = Exception("Form save error")
        mock_form.cleaned_data = {"title": "Test Workspace"}

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            with self.assertRaises(WorkspaceCreationError):
                create_workspace_from_form(
                    form=mock_form,
                    orgMember=self.org_member,
                    organization=self.organization,
                )

                mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_create_workspace_audit_logging_failure(self):
        """Test workspace creation when audit logging fails."""
        # Mock form
        mock_form = Mock()
        mock_form.save.return_value = WorkspaceFactory.build(
            organization=self.organization
        )
        mock_form.cleaned_data = {"title": "Test Workspace"}

        with patch(
            "apps.workspaces.services.assign_workspace_permissions"
        ) as mock_assign:
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_action"
            ) as mock_log:
                mock_log.side_effect = Exception("Logging error")

                # Should still create workspace even if logging fails
                result = create_workspace_from_form(
                    form=mock_form,
                    orgMember=self.org_member,
                    organization=self.organization,
                )

                self.assertIsInstance(result, Workspace)
                mock_assign.assert_called_once()


@pytest.mark.unit
class TestUpdateWorkspaceFromForm(TestCase):
    """Test workspace update from form."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.user = CustomUserFactory()
        self.previous_admin = OrganizationMemberFactory(organization=self.organization)
        self.previous_reviewer = OrganizationMemberFactory(
            organization=self.organization
        )

    @pytest.mark.django_db
    def test_update_workspace_success(self):
        """Test successful workspace update."""
        # Mock form
        org_member = OrganizationMemberFactory(organization=self.organization)
        mock_form = Mock()
        mock_form.cleaned_data = {
            "workspace_admin": self.previous_admin,
            "operations_reviewer": self.previous_reviewer,
            "created_by": org_member,
        }

        with patch(
            "apps.workspaces.services.update_workspace_admin_group"
        ) as mock_update:
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_action"
            ) as mock_log:
                result = update_workspace_from_form(
                    form=mock_form,
                    workspace=self.workspace,
                    previous_workspace_admin=self.previous_admin,
                    previous_operations_reviewer=self.previous_reviewer,
                    user=org_member,
                )

                self.assertEqual(result, self.workspace)
                mock_update.assert_called_once()
                mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_update_workspace_without_user(self):
        """Test workspace update without user."""
        # Mock form
        org_member = OrganizationMemberFactory(organization=self.organization)
        mock_form = Mock()
        mock_form.cleaned_data = {
            "workspace_admin": self.previous_admin,
            "operations_reviewer": self.previous_reviewer,
            "created_by": org_member,
        }

        with patch(
            "apps.workspaces.services.update_workspace_admin_group"
        ) as mock_update:
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_action"
            ) as mock_log:
                result = update_workspace_from_form(
                    form=mock_form,
                    workspace=self.workspace,
                    previous_workspace_admin=self.previous_admin,
                    previous_operations_reviewer=self.previous_reviewer,
                    user=None,
                )

                self.assertEqual(result, self.workspace)
                mock_update.assert_called_once()
                # Should not log when no user
                mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_update_workspace_error(self):
        """Test workspace update when an error occurs."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "workspace_admin": self.previous_admin,
            "created_by": self.user,
        }

        with patch(
            "apps.workspaces.services.update_workspace_admin_group"
        ) as mock_update:
            mock_update.side_effect = Exception("Update error")
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
            ) as mock_log:
                with self.assertRaises(WorkspaceUpdateError):
                    update_workspace_from_form(
                        form=mock_form,
                        workspace=self.workspace,
                        previous_workspace_admin=self.previous_admin,
                        previous_operations_reviewer=self.previous_reviewer,
                        user=self.user,
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestRemoveTeamFromWorkspace(TestCase):
    """Test removing team from workspace."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_remove_team_success(self):
        """Test successful team removal."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = remove_team_from_workspace(
                workspace_team=self.workspace_team,
                user=self.user,
                team=self.team,
            )

            self.assertEqual(result, self.workspace_team)
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_remove_team_without_user(self):
        """Test team removal without user."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = remove_team_from_workspace(
                workspace_team=self.workspace_team,
                user=None,
                team=self.team,
            )

            self.assertEqual(result, self.workspace_team)
            # Should not log when no user
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_remove_team_with_team_coordinator(self):
        """Test team removal when team has coordinator."""
        # Set team coordinator
        team_member = TeamMemberFactory(team=self.team)
        self.workspace_team.team.team_coordinator = team_member.organization_member
        self.workspace_team.team.save()

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            with patch("apps.workspaces.services.remove_perm") as mock_remove_perm:
                result = remove_team_from_workspace(
                    workspace_team=self.workspace_team,
                    user=self.user,
                    team=self.team,
                )

                self.assertEqual(result, self.workspace_team)
                mock_log.assert_called_once()
                mock_remove_perm.assert_called_once()

    @pytest.mark.django_db
    def test_remove_team_error(self):
        """Test team removal when an error occurs."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the delete to raise an error
            with patch.object(self.workspace_team, "delete") as mock_delete:
                mock_delete.side_effect = Exception("Delete error")

                with self.assertRaises(ValidationError):
                    remove_team_from_workspace(
                        workspace_team=self.workspace_team,
                        user=self.user,
                        team=self.team,
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestAddTeamToWorkspace(TestCase):
    """Test adding team to workspace."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_add_team_success(self):
        """Test successful team addition."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = add_team_to_workspace(
                workspace_id=self.workspace.workspace_id,
                team_id=self.team.team_id,
                custom_remittance_rate=Decimal("85.50"),
                workspace=self.workspace,
                user=self.user,
            )

            self.assertIsInstance(result, WorkspaceTeam)
            self.assertEqual(result.workspace, self.workspace)
            self.assertEqual(result.team, self.team)
            self.assertEqual(result.custom_remittance_rate, Decimal("85.50"))
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_add_team_without_custom_rate(self):
        """Test team addition without custom remittance rate."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = add_team_to_workspace(
                workspace_id=self.workspace.workspace_id,
                team_id=self.team.team_id,
                custom_remittance_rate=None,
                workspace=self.workspace,
                user=self.user,
            )

            self.assertIsInstance(result, WorkspaceTeam)
            self.assertEqual(
                result.custom_remittance_rate, self.workspace.remittance_rate
            )
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_add_team_without_user(self):
        """Test team addition without user."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = add_team_to_workspace(
                workspace_id=self.workspace.workspace_id,
                team_id=self.team.team_id,
                custom_remittance_rate=Decimal("80.00"),
                workspace=self.workspace,
                user=None,
            )

            self.assertIsInstance(result, WorkspaceTeam)
            # Should not log when no user
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_add_team_error(self):
        """Test team addition when an error occurs."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the create to raise an error
            with patch.object(WorkspaceTeam.objects, "create") as mock_create:
                mock_create.side_effect = Exception("Create error")

                with self.assertRaises(Exception):
                    add_team_to_workspace(
                        workspace_id=self.workspace.workspace_id,
                        team_id=self.team.team_id,
                        custom_remittance_rate=Decimal("80.00"),
                        workspace=self.workspace,
                        user=self.user,
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestUpdateWorkspaceTeamRemittanceRateFromForm(TestCase):
    """Test updating workspace team remittance rate from form."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(
            organization=self.organization, remittance_rate=Decimal("90.00")
        )
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace,
            team=self.team,
            custom_remittance_rate=Decimal("85.00"),
        )
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_update_remittance_rate_success(self):
        """Test successful remittance rate update."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {"custom_remittance_rate": Decimal("80.00")}

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = update_workspace_team_remittance_rate_from_form(
                form=mock_form,
                workspace_team=self.workspace_team,
                workspace=self.workspace,
                user=self.user,
            )

            self.assertEqual(result, self.workspace_team)
            self.assertEqual(result.custom_remittance_rate, Decimal("80.00"))
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_update_remittance_rate_to_workspace_default(self):
        """Test updating remittance rate to workspace default (should set to None)."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "custom_remittance_rate": Decimal("90.00")
        }  # Same as workspace

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = update_workspace_team_remittance_rate_from_form(
                form=mock_form,
                workspace_team=self.workspace_team,
                workspace=self.workspace,
                user=self.user,
            )

            self.assertEqual(result, self.workspace_team)
            self.assertIsNone(result.custom_remittance_rate)
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_update_remittance_rate_without_user(self):
        """Test remittance rate update without user."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {"custom_remittance_rate": Decimal("80.00")}

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_team_action"
        ) as mock_log:
            result = update_workspace_team_remittance_rate_from_form(
                form=mock_form,
                workspace_team=self.workspace_team,
                workspace=self.workspace,
                user=None,
            )

            self.assertEqual(result, self.workspace_team)
            # Should not log when no user
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_update_remittance_rate_error(self):
        """Test remittance rate update when an error occurs."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {"custom_remittance_rate": Decimal("80.00")}

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the save to raise an error
            with patch.object(self.workspace_team, "save") as mock_save:
                mock_save.side_effect = Exception("Save error")

                with self.assertRaises(Exception):
                    update_workspace_team_remittance_rate_from_form(
                        form=mock_form,
                        workspace_team=self.workspace_team,
                        workspace=self.workspace,
                        user=self.user,
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestCreateWorkspaceExchangeRate(TestCase):
    """Test creating workspace exchange rate."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    @pytest.mark.django_db
    def test_create_exchange_rate_success(self):
        """Test successful exchange rate creation."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            result = create_workspace_exchange_rate(
                workspace=self.workspace,
                organization_member=self.org_member,
                currency_code="EUR",
                rate=Decimal("1.25"),
                note="Test rate",
                effective_date=date.today(),
            )

            self.assertIsInstance(result, WorkspaceExchangeRate)
            self.assertEqual(result.workspace, self.workspace)
            self.assertEqual(result.currency.code, "EUR")
            self.assertEqual(result.rate, Decimal("1.25"))
            self.assertEqual(result.note, "Test rate")
            self.assertEqual(result.added_by, self.org_member)
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_create_exchange_rate_without_org_member(self):
        """Test exchange rate creation without organization member."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            result = create_workspace_exchange_rate(
                workspace=self.workspace,
                organization_member=None,
                currency_code="USD",
                rate=Decimal("1.00"),
                note="Test rate",
                effective_date=date.today(),
            )

            self.assertIsInstance(result, WorkspaceExchangeRate)
            # Should not log when no org member
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_create_exchange_rate_integrity_error(self):
        """Test exchange rate creation with integrity error."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the create to raise an integrity error
            with patch.object(WorkspaceExchangeRate.objects, "create") as mock_create:
                mock_create.side_effect = IntegrityError("Duplicate key")

                with self.assertRaises(ValidationError):
                    create_workspace_exchange_rate(
                        workspace=self.workspace,
                        organization_member=self.org_member,
                        currency_code="EUR",
                        rate=Decimal("1.25"),
                        note="Test rate",
                        effective_date=date.today(),
                    )

                    mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_create_exchange_rate_general_error(self):
        """Test exchange rate creation with general error."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the create to raise a general error
            with patch.object(WorkspaceExchangeRate.objects, "create") as mock_create:
                mock_create.side_effect = Exception("General error")

                with self.assertRaises(ValidationError):
                    create_workspace_exchange_rate(
                        workspace=self.workspace,
                        organization_member=self.org_member,
                        currency_code="EUR",
                        rate=Decimal("1.25"),
                        note="Test rate",
                        effective_date=date.today(),
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestUpdateWorkspaceExchangeRate(TestCase):
    """Test updating workspace exchange rate."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.exchange_rate = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            note="Original note",
            is_approved=False,
            approved_by=None,
        )

    @pytest.mark.django_db
    def test_update_exchange_rate_success(self):
        """Test successful exchange rate update."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            result = update_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
                note="Updated note",
                is_approved=True,
                org_member=self.org_member,
            )

            self.assertEqual(result, self.exchange_rate)
            self.assertEqual(result.note, "Updated note")
            self.assertTrue(result.is_approved)
            self.assertEqual(result.approved_by, self.org_member)
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_update_exchange_rate_unapprove(self):
        """Test unapproving an exchange rate."""
        # First approve it
        self.exchange_rate.is_approved = True
        self.exchange_rate.approved_by = self.org_member
        self.exchange_rate.save()

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            result = update_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
                note="Updated note",
                is_approved=False,
                org_member=self.org_member,
            )

            self.assertEqual(result, self.exchange_rate)
            self.assertFalse(result.is_approved)
            self.assertIsNone(result.approved_by)
            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_update_exchange_rate_without_org_member(self):
        """Test exchange rate update without organization member."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            result = update_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
                note="Updated note",
                is_approved=True,
                org_member=None,
            )

            self.assertEqual(result, self.exchange_rate)
            # Should not log when no org member
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_update_exchange_rate_error(self):
        """Test exchange rate update when an error occurs."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the model_update to raise an error
            with patch("apps.workspaces.services.model_update") as mock_update:
                mock_update.side_effect = Exception("Update error")

                with self.assertRaises(ValidationError):
                    update_workspace_exchange_rate(
                        workspace_exchange_rate=self.exchange_rate,
                        note="Updated note",
                        is_approved=True,
                        org_member=self.org_member,
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestDeleteWorkspaceExchangeRate(TestCase):
    """Test deleting workspace exchange rate."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.user = CustomUserFactory()
        self.exchange_rate = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency__code="EUR",
            rate=Decimal("1.25"),
        )

    @pytest.mark.django_db
    def test_delete_exchange_rate_success(self):
        """Test successful exchange rate deletion."""
        exchange_rate_id = self.exchange_rate.pk

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            delete_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
                user=self.user,
            )

            # Verify it was deleted
            with self.assertRaises(WorkspaceExchangeRate.DoesNotExist):
                WorkspaceExchangeRate.objects.get(pk=exchange_rate_id)

            mock_log.assert_called_once()

    @pytest.mark.django_db
    def test_delete_exchange_rate_without_user(self):
        """Test exchange rate deletion without user."""
        exchange_rate_id = self.exchange_rate.pk

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ) as mock_log:
            delete_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
                user=None,
            )

            # Verify it was deleted
            with self.assertRaises(WorkspaceExchangeRate.DoesNotExist):
                WorkspaceExchangeRate.objects.get(pk=exchange_rate_id)

            # Should not log when no user
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_delete_exchange_rate_error(self):
        """Test exchange rate deletion when an error occurs."""
        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_operation_failure"
        ) as mock_log:
            # Mock the delete to raise an error
            with patch.object(self.exchange_rate, "delete") as mock_delete:
                mock_delete.side_effect = Exception("Delete error")

                with self.assertRaises(ValidationError):
                    delete_workspace_exchange_rate(
                        workspace_exchange_rate=self.exchange_rate,
                        user=self.user,
                    )

                    mock_log.assert_called_once()


@pytest.mark.unit
class TestServiceEdgeCases(TestCase):
    """Test edge cases and error scenarios for services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_create_workspace_transaction_rollback(self):
        """Test that workspace creation rolls back on error."""
        # Mock form that fails during save
        mock_form = Mock()
        mock_form.save.side_effect = Exception("Save error")
        mock_form.cleaned_data = {"title": "Test Workspace"}

        with self.assertRaises(WorkspaceCreationError):
            create_workspace_from_form(
                form=mock_form,
                orgMember=None,
                organization=self.organization,
            )

        # Verify no workspace was created
        self.assertEqual(Workspace.objects.count(), 1)  # Only the one from setUp

    @pytest.mark.django_db
    def test_update_workspace_transaction_rollback(self):
        """Test that workspace update rolls back on error."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {"title": "Updated Workspace"}

        with patch(
            "apps.workspaces.services.update_workspace_admin_group"
        ) as mock_update:
            mock_update.side_effect = Exception("Update error")

            with self.assertRaises(WorkspaceUpdateError):
                update_workspace_from_form(
                    form=mock_form,
                    workspace=self.workspace,
                    previous_workspace_admin=None,
                    previous_operations_reviewer=None,
                    user=self.user,
                )

            # Verify workspace title wasn't changed
            self.workspace.refresh_from_db()
            self.assertNotEqual(self.workspace.title, "Updated Workspace")

    @pytest.mark.django_db
    def test_audit_logging_failure_doesnt_break_operation(self):
        """Test that audit logging failures don't break the main operation."""
        # Mock form
        mock_form = Mock()
        mock_form.save.return_value = WorkspaceFactory.build(
            organization=self.organization
        )
        mock_form.cleaned_data = {"title": "Test Workspace"}

        with patch(
            "apps.workspaces.services.assign_workspace_permissions"
        ) as mock_assign:
            with patch(
                "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_action"
            ) as mock_log:
                mock_log.side_effect = Exception("Logging error")

                # Should still create workspace even if logging fails
                result = create_workspace_from_form(
                    form=mock_form,
                    orgMember=None,
                    organization=self.organization,
                )

                self.assertIsInstance(result, Workspace)
                mock_assign.assert_called_once()

    @pytest.mark.django_db
    def test_remove_team_permission_cleanup(self):
        """Test that team removal properly cleans up permissions."""
        team = TeamFactory(organization=self.organization)
        workspace_team = WorkspaceTeamFactory(workspace=self.workspace, team=team)

        # Set team coordinator
        team_member = TeamMemberFactory(team=team)
        team.team_coordinator = team_member.organization_member
        team.save()

        # Mock the remove_perm function to verify it's called
        with patch("apps.workspaces.services.remove_perm") as mock_remove_perm:
            remove_team_from_workspace(
                workspace_team=workspace_team,
                user=self.user,
                team=team,
            )

            # Verify permission was removed
            mock_remove_perm.assert_called_once()

    @pytest.mark.django_db
    def test_exchange_rate_currency_creation(self):
        """Test that new currencies are created when needed."""
        # Test with a currency code that doesn't exist
        org_member = OrganizationMemberFactory(organization=self.organization)

        with patch(
            "apps.auditlog.business_logger.BusinessAuditLogger.log_workspace_exchange_rate_action"
        ):
            result = create_workspace_exchange_rate(
                workspace=self.workspace,
                organization_member=org_member,
                currency_code="JPY",  # Valid currency code that might not exist in test DB
                rate=Decimal("2.00"),
                note="Test rate",
                effective_date=date.today(),
            )

            self.assertIsInstance(result, WorkspaceExchangeRate)
            self.assertEqual(result.currency.code, "JPY")

            # Verify currency was created
            currency = Currency.objects.get(code="JPY")
            self.assertIsNotNone(currency)
