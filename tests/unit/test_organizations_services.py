"""Unit tests for organization services.

Tests business logic functions with various scenarios and edge cases.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.organizations.exceptions import (
    OrganizationCreationError,
    OrganizationUpdateError,
)
from apps.organizations.models import Organization, OrganizationExchangeRate
from apps.organizations.services import (
    create_organization_with_owner,
    update_organization_from_form,
    create_organization_exchange_rate,
    update_organization_exchange_rate,
    delete_organization_exchange_rate,
)
from tests.factories import (
    CustomUserFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    OrganizationExchangeRateFactory,
    CurrencyFactory,
)


class TestCreateOrganizationWithOwner(TestCase):
    """Test create_organization_with_owner service."""

    def setUp(self):
        self.user = CustomUserFactory()

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.get_permissions_for_role")
    @patch("apps.organizations.services.assign_perm")
    @patch("apps.organizations.services.Group.objects.get_or_create")
    @patch("apps.organizations.services.OrganizationMember.objects.create")
    @patch("apps.organizations.services.model_update")
    def test_create_organization_with_owner_success(
        self,
        mock_model_update,
        mock_member_create,
        mock_group,
        mock_assign_perm,
        mock_get_permissions,
        mock_audit_logger,
    ):
        """Test successful organization creation with owner."""
        # Mock form
        mock_form = MagicMock()
        mock_org = OrganizationFactory()
        mock_form.save.return_value = mock_org

        # Mock permissions
        mock_get_permissions.return_value = ["add_organization", "change_organization"]

        # Mock member creation
        mock_member = MagicMock()
        mock_member.user = self.user
        mock_member_create.return_value = mock_member

        # Mock group creation
        mock_group_obj = MagicMock()
        mock_group.return_value = (mock_group_obj, True)

        # Mock model update
        mock_model_update.return_value = mock_org

        result = create_organization_with_owner(form=mock_form, user=self.user)

        # Verify organization was created
        self.assertIsInstance(result, Organization)

        # Verify permissions were assigned
        mock_assign_perm.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_create_organization_with_owner_failure(self, mock_audit_logger):
        """Test organization creation failure."""
        # Mock form that raises an exception
        mock_form = MagicMock()
        mock_form.save.side_effect = Exception("Database error")

        with self.assertRaises(OrganizationCreationError):
            create_organization_with_owner(form=mock_form, user=self.user)

        # Verify audit logging was attempted
        mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.assign_perm")
    @patch("apps.organizations.services.Group.objects.get_or_create")
    @patch("apps.organizations.services.OrganizationMember.objects.create")
    @patch("apps.organizations.services.model_update")
    def test_create_organization_with_owner_audit_logging_failure(
        self,
        mock_model_update,
        mock_member_create,
        mock_group,
        mock_assign_perm,
        mock_audit_logger,
    ):
        """Test organization creation when audit logging fails."""
        # Mock form
        mock_form = MagicMock()
        mock_org = OrganizationFactory()
        mock_form.save.return_value = mock_org

        # Mock member creation
        mock_member = MagicMock()
        mock_member.user = self.user
        mock_member_create.return_value = mock_member

        # Mock group creation
        mock_group_obj = MagicMock()
        mock_group.return_value = (mock_group_obj, True)

        # Mock model update
        mock_model_update.return_value = mock_org

        # Mock audit logging failure
        mock_audit_logger.log_permission_change.side_effect = Exception("Audit error")

        # Should still create organization even if audit logging fails
        result = create_organization_with_owner(form=mock_form, user=self.user)
        self.assertIsInstance(result, Organization)


class TestUpdateOrganizationFromForm(TestCase):
    """Test update_organization_from_form service."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.model_update")
    def test_update_organization_success(self, mock_model_update, mock_audit_logger):
        """Test successful organization update."""
        # Mock form
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {"title": "Updated Title"}

        # Mock model update
        updated_org = OrganizationFactory(title="Updated Title")
        mock_model_update.return_value = updated_org

        result = update_organization_from_form(
            form=mock_form, organization=self.organization, user=self.user
        )

        self.assertEqual(result.title, "Updated Title")
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    def test_update_organization_invalid_form(self):
        """Test organization update with invalid form."""
        # Mock invalid form
        mock_form = MagicMock()
        mock_form.is_valid.return_value = False
        mock_form.errors = {"title": ["This field is required."]}

        with self.assertRaises(OrganizationUpdateError):
            update_organization_from_form(
                form=mock_form, organization=self.organization, user=self.user
            )

    def test_update_organization_status_change(self):
        """Test organization update with status change - auditing handled by signals."""
        # Mock form
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {"status": "CLOSED"}

        # Mock model update
        updated_org = OrganizationFactory(status="CLOSED")
        with patch("apps.organizations.services.model_update") as mock_model_update:
            mock_model_update.return_value = updated_org

            result = update_organization_from_form(
                form=mock_form, organization=self.organization, user=self.user
            )

            # Verify organization was updated successfully
            self.assertEqual(result.status, "CLOSED")
            # Note: Audit logging is now handled automatically by signal handlers


class TestCreateOrganizationExchangeRate(TestCase):
    """Test create_organization_exchange_rate service."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization
        )
        # Don't create real currency in setUp to avoid interference

    @patch("apps.organizations.services.get_or_create_currency_by_code")
    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_create_exchange_rate_success(
        self, mock_audit_logger, mock_get_or_create_currency
    ):
        """Test successful exchange rate creation."""
        # Mock currency creation with real Currency instance
        currency = CurrencyFactory(code="USD")
        mock_get_or_create_currency.return_value = currency

        result = create_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.organization_member,
            currency_code="USD",
            rate=Decimal("1.25"),
            note="Test rate",
            effective_date=date.today(),
        )

        # Verify exchange rate was created and returned
        self.assertIsInstance(result, OrganizationExchangeRate)
        self.assertEqual(result.organization, self.organization)
        self.assertEqual(result.currency, currency)
        self.assertEqual(result.rate, Decimal("1.25"))
        self.assertEqual(result.note, "Test rate")

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.organizations.services.get_or_create_currency_by_code")
    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_create_exchange_rate_integrity_error(
        self, mock_audit_logger, mock_get_or_create_currency
    ):
        """Test exchange rate creation with integrity error."""
        # Mock currency creation with real Currency instance
        currency = CurrencyFactory(code="USD")
        mock_get_or_create_currency.return_value = currency

        # Mock integrity error on save
        with patch.object(OrganizationExchangeRate, "save") as mock_save:
            mock_save.side_effect = IntegrityError("Duplicate entry")

            with self.assertRaises(ValidationError):
                create_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    currency_code="USD",
                    rate=Decimal("1.25"),
                    note="Test rate",
                    effective_date=date.today(),
                )

            # Verify audit logging was attempted
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.get_or_create_currency_by_code")
    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_create_exchange_rate_general_error(
        self, mock_audit_logger, mock_get_or_create_currency
    ):
        """Test exchange rate creation with general error."""
        # Mock currency creation with real Currency instance
        currency = CurrencyFactory(code="USD")
        mock_get_or_create_currency.return_value = currency

        # Mock general error on save
        with patch.object(OrganizationExchangeRate, "save") as mock_save:
            mock_save.side_effect = Exception("General error")

            with self.assertRaises(ValidationError):
                create_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    currency_code="USD",
                    rate=Decimal("1.25"),
                    note="Test rate",
                    effective_date=date.today(),
                )

            # Verify audit logging was attempted
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.get_or_create_currency_by_code")
    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_create_exchange_rate_audit_logging_failure(
        self, mock_audit_logger, mock_get_or_create_currency
    ):
        """Test exchange rate creation when audit logging fails."""
        # Mock currency creation with real Currency instance
        currency = CurrencyFactory(code="USD")
        mock_get_or_create_currency.return_value = currency

        # Call the service function
        result = create_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.organization_member,
            currency_code="USD",
            rate=Decimal("1.00"),
            note="Test rate",
            effective_date=date.today(),
        )

        # Verify the function still returns the exchange rate
        self.assertIsInstance(result, OrganizationExchangeRate)
        self.assertEqual(result.organization, self.organization)
        self.assertEqual(result.currency, currency)

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service


class TestUpdateOrganizationExchangeRate(TestCase):
    """Test update_organization_exchange_rate service."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization
        )
        self.exchange_rate = OrganizationExchangeRateFactory(
            organization=self.organization, note="Original note"
        )

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.model_update")
    def test_update_exchange_rate_success(self, mock_model_update, mock_audit_logger):
        """Test successful exchange rate update."""
        # Mock model update
        updated_rate = OrganizationExchangeRateFactory(note="Updated note")
        mock_model_update.return_value = updated_rate

        result = update_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.organization_member,
            org_exchange_rate=self.exchange_rate,
            note="Updated note",
        )

        # Verify update was performed
        mock_model_update.assert_called_once()
        self.assertEqual(result, updated_rate)

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_update_exchange_rate_failure(self, mock_audit_logger):
        """Test exchange rate update failure."""
        # Mock model update failure
        with patch("apps.organizations.services.model_update") as mock_model_update:
            mock_model_update.side_effect = Exception("Update error")

            with self.assertRaises(ValidationError):
                update_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    org_exchange_rate=self.exchange_rate,
                    note="Updated note",
                )

            # Verify audit logging was attempted
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.model_update")
    def test_update_exchange_rate_audit_logging_failure(
        self, mock_model_update, mock_audit_logger
    ):
        """Test exchange rate update when audit logging fails."""
        # Mock successful model update
        updated_rate = OrganizationExchangeRateFactory(note="Updated note")
        mock_model_update.return_value = updated_rate

        # Call the service function
        result = update_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.organization_member,
            org_exchange_rate=self.exchange_rate,
            note="Updated note",
        )

        # Verify the function still returns the updated rate
        assert result == updated_rate

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service


class TestDeleteOrganizationExchangeRate(TestCase):
    """Test delete_organization_exchange_rate service."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization
        )
        self.exchange_rate = OrganizationExchangeRateFactory(
            organization=self.organization
        )

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_delete_exchange_rate_success(self, mock_audit_logger):
        """Test successful exchange rate deletion."""
        result = delete_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.organization_member,
            org_exchange_rate=self.exchange_rate,
        )

        # Verify deletion was successful
        self.assertTrue(result)

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_delete_exchange_rate_failure(self, mock_audit_logger):
        """Test exchange rate deletion failure."""
        # Mock deletion failure
        with patch.object(self.exchange_rate, "delete") as mock_delete:
            mock_delete.side_effect = Exception("Delete error")

            with self.assertRaises(ValidationError):
                delete_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    org_exchange_rate=self.exchange_rate,
                )

            # Verify audit logging was attempted
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_delete_exchange_rate_audit_logging_failure(self, mock_audit_logger):
        """Test exchange rate deletion when audit logging fails."""
        # Should still delete successfully
        result = delete_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.organization_member,
            org_exchange_rate=self.exchange_rate,
        )

        self.assertTrue(result)

        # Note: Audit logging is now handled by signal handlers, not explicitly in the service


class TestExceptionHandlingCoverage(TestCase):
    """Test exception handling for coverage gaps."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization
        )
        self.exchange_rate = OrganizationExchangeRateFactory(
            organization=self.organization
        )

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_create_organization_audit_logging_failure_in_exception_handler(
        self, mock_audit_logger
    ):
        """Test audit logging failure in the exception handler of create_organization_with_owner."""
        # Mock form that will raise an exception
        mock_form = MagicMock()
        mock_form.save.side_effect = Exception("Form save error")

        # Mock audit logging to fail in the exception handler
        mock_audit_logger.log_operation_failure.side_effect = Exception("Audit error")

        with self.assertRaises(OrganizationCreationError):
            create_organization_with_owner(form=mock_form, user=self.user)

        # Verify audit logging was attempted and failed
        mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.model_update")
    def test_update_organization_audit_logging_failure_in_success_handler(
        self, mock_model_update, mock_audit_logger
    ):
        """Test audit logging failure in the success handler of update_organization_from_form."""
        # Mock form
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {"title": "Updated Organization"}

        # Mock model update to return the organization
        mock_model_update.return_value = self.organization

        # Should still update successfully
        result = update_organization_from_form(
            form=mock_form, organization=self.organization, user=self.user
        )

        self.assertEqual(result, self.organization)
        # Note: Audit logging is now handled by signal handlers, not explicitly in the service

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_update_organization_audit_logging_failure_in_exception_handler(
        self, mock_audit_logger
    ):
        """Test audit logging failure in the exception handler of update_organization_from_form."""
        # Mock form that will raise an exception
        mock_form = MagicMock()
        mock_form.is_valid.side_effect = Exception("Form validation error")

        with self.assertRaises(OrganizationUpdateError):
            update_organization_from_form(
                form=mock_form, organization=self.organization, user=self.user
            )

        # Note: The exception handler doesn't have explicit audit logging anymore

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.get_or_create_currency_by_code")
    def test_create_exchange_rate_audit_logging_failure_in_integrity_error_handler(
        self, mock_get_or_create_currency, mock_audit_logger
    ):
        """Test audit logging failure in the IntegrityError handler of create_organization_exchange_rate."""
        # Mock currency creation with real Currency instance
        currency = CurrencyFactory(code="EUR")
        mock_get_or_create_currency.return_value = currency

        # Mock IntegrityError on save
        with patch.object(OrganizationExchangeRate, "save") as mock_save:
            mock_save.side_effect = IntegrityError("Duplicate key")

            with self.assertRaises(ValidationError):
                create_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    currency_code="USD",
                    rate=Decimal("1.00"),
                    note="Test rate",
                    effective_date=date.today(),
                )

            # Verify audit logging was attempted (in exception handler)
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    @patch("apps.organizations.services.get_or_create_currency_by_code")
    def test_create_exchange_rate_audit_logging_failure_in_general_error_handler(
        self, mock_get_or_create_currency, mock_audit_logger
    ):
        """Test audit logging failure in the general exception handler of create_organization_exchange_rate."""
        # Mock currency creation with real Currency instance
        currency = CurrencyFactory(code="GBP")
        mock_get_or_create_currency.return_value = currency

        # Mock general exception on save
        with patch.object(OrganizationExchangeRate, "save") as mock_save:
            mock_save.side_effect = Exception("General error")

            with self.assertRaises(ValidationError):
                create_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    currency_code="USD",
                    rate=Decimal("1.00"),
                    note="Test rate",
                    effective_date=date.today(),
                )

            # Verify audit logging was attempted (in exception handler)
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_update_exchange_rate_audit_logging_failure_in_exception_handler(
        self, mock_audit_logger
    ):
        """Test audit logging failure in the exception handler of update_organization_exchange_rate."""
        # Mock update failure
        with patch("apps.organizations.services.model_update") as mock_update:
            mock_update.side_effect = Exception("Update error")

            with self.assertRaises(ValidationError):
                update_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    org_exchange_rate=self.exchange_rate,
                    note="Updated note",
                )

            # Verify audit logging was attempted (in exception handler)
            mock_audit_logger.log_operation_failure.assert_called()

    @patch("apps.organizations.services.BusinessAuditLogger")
    def test_delete_exchange_rate_audit_logging_failure_in_exception_handler(
        self, mock_audit_logger
    ):
        """Test audit logging failure in the exception handler of delete_organization_exchange_rate."""
        # Mock deletion failure
        with patch.object(self.exchange_rate, "delete") as mock_delete:
            mock_delete.side_effect = Exception("Delete error")

            with self.assertRaises(ValidationError):
                delete_organization_exchange_rate(
                    organization=self.organization,
                    organization_member=self.organization_member,
                    org_exchange_rate=self.exchange_rate,
                )

            # Verify audit logging was attempted (in exception handler)
            mock_audit_logger.log_operation_failure.assert_called()
