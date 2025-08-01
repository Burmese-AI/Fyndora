"""
Unit tests for Workspace models.

Tests cover:
- Workspace model creation, validation, constraints, string representation
- WorkspaceTeam model creation, unique constraints, string representation
- WorkspaceExchangeRate model creation, unique constraints, soft delete behavior
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.currencies.models import Currency
from apps.workspaces.constants import StatusChoices
from apps.workspaces.models import Workspace, WorkspaceTeam, WorkspaceExchangeRate
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceExchangeRateFactory,
    WorkspaceWithAdminFactory,
)


@pytest.mark.unit
class TestWorkspaceModel(TestCase):
    """Test the Workspace model - essential functionality only."""

    @pytest.mark.django_db
    def test_workspace_creation_with_defaults(self):
        """Test creating workspace with required fields."""
        organization = OrganizationFactory()
        workspace = Workspace.objects.create(
            organization=organization,
            title="Test Workspace",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )

        self.assertEqual(workspace.title, "Test Workspace")
        self.assertEqual(workspace.organization, organization)
        self.assertEqual(workspace.status, StatusChoices.ACTIVE)
        self.assertEqual(workspace.remittance_rate, Decimal("90.00"))
        self.assertEqual(workspace.expense, Decimal("0.00"))
        self.assertIsNotNone(workspace.workspace_id)

    @pytest.mark.django_db
    def test_workspace_string_representation(self):
        """Test workspace string representation."""
        workspace = WorkspaceFactory(title="My Workspace")
        expected = f"My Workspace ({workspace.organization.title})"
        self.assertEqual(str(workspace), expected)

    @pytest.mark.django_db
    def test_workspace_unique_title_per_organization(self):
        """Test that workspace titles must be unique within an organization."""
        organization = OrganizationFactory()
        WorkspaceFactory(organization=organization, title="Duplicate Title")

        with self.assertRaises(IntegrityError):
            WorkspaceFactory(organization=organization, title="Duplicate Title")

    @pytest.mark.django_db
    def test_workspace_same_title_different_organizations(self):
        """Test that same title is allowed in different organizations."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()

        workspace1 = WorkspaceFactory(organization=org1, title="Same Title")
        workspace2 = WorkspaceFactory(organization=org2, title="Same Title")

        self.assertEqual(workspace1.title, workspace2.title)
        self.assertNotEqual(workspace1.organization, workspace2.organization)

    @pytest.mark.django_db
    def test_workspace_clean_method_valid_dates(self):
        """Test workspace clean method with valid dates."""
        workspace = WorkspaceFactory.build(
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        # Should not raise any exception
        workspace.clean()

    @pytest.mark.django_db
    def test_workspace_clean_method_invalid_dates(self):
        """Test workspace clean method with invalid dates."""
        workspace = WorkspaceFactory.build(
            start_date=date.today(),
            end_date=date.today() - timedelta(days=30),
        )
        with self.assertRaises(ValidationError):
            workspace.clean()

    @pytest.mark.django_db
    def test_workspace_remittance_rate_validation(self):
        """Test workspace remittance rate validation."""
        organization = OrganizationFactory()

        # Valid rate
        workspace = Workspace(
            organization=organization,
            title="Valid Rate",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            remittance_rate=Decimal("50.00"),
            created_by=OrganizationMemberFactory(organization=organization),
        )
        workspace.full_clean()  # Should not raise

        # Invalid rate - too high
        workspace.remittance_rate = Decimal("150.00")
        with self.assertRaises(ValidationError):
            workspace.full_clean()

        # Invalid rate - negative
        workspace.remittance_rate = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            workspace.full_clean()

    @pytest.mark.django_db
    def test_workspace_status_choices(self):
        """Test workspace status choices."""
        workspace = WorkspaceWithAdminFactory()

        # Test all valid status choices
        for status, _ in StatusChoices.choices:
            workspace.status = status
            workspace.full_clean()  # Should not raise

        # Test invalid status
        workspace.status = "invalid_status"
        with self.assertRaises(ValidationError):
            workspace.full_clean()

    @pytest.mark.django_db
    def test_workspace_with_admin_and_reviewer(self):
        """Test workspace with admin and operations reviewer."""
        organization = OrganizationFactory()
        admin = OrganizationMemberFactory(organization=organization)
        reviewer = OrganizationMemberFactory(organization=organization)

        workspace = WorkspaceFactory(
            organization=organization,
            workspace_admin=admin,
            operations_reviewer=reviewer,
            created_by=admin,
        )

        self.assertEqual(workspace.workspace_admin, admin)
        self.assertEqual(workspace.operations_reviewer, reviewer)
        self.assertEqual(workspace.created_by, admin)


@pytest.mark.unit
class TestWorkspaceTeamModel(TestCase):
    """Test the WorkspaceTeam model."""

    @pytest.mark.django_db
    def test_workspace_team_creation(self):
        """Test creating workspace team."""
        workspace = WorkspaceFactory()
        team = TeamFactory(organization=workspace.organization)

        workspace_team = WorkspaceTeam.objects.create(
            workspace=workspace,
            team=team,
        )

        self.assertEqual(workspace_team.workspace, workspace)
        self.assertEqual(workspace_team.team, team)
        self.assertIsNone(workspace_team.custom_remittance_rate)
        self.assertIsNotNone(workspace_team.workspace_team_id)

    @pytest.mark.django_db
    def test_workspace_team_string_representation(self):
        """Test workspace team string representation."""
        workspace_team = WorkspaceTeamFactory()
        expected = f"{workspace_team.team.title} in {workspace_team.workspace.title}"
        self.assertEqual(str(workspace_team), expected)

    @pytest.mark.django_db
    def test_workspace_team_unique_constraint(self):
        """Test that team can only be added once to a workspace."""
        workspace = WorkspaceFactory()
        team = TeamFactory(organization=workspace.organization)

        WorkspaceTeamFactory(workspace=workspace, team=team)

        with self.assertRaises(IntegrityError):
            WorkspaceTeamFactory(workspace=workspace, team=team)

    @pytest.mark.django_db
    def test_workspace_team_custom_remittance_rate_validation(self):
        """Test workspace team custom remittance rate validation."""
        workspace_team = WorkspaceTeamFactory()

        # Valid rate
        workspace_team.custom_remittance_rate = Decimal("75.00")
        workspace_team.full_clean()  # Should not raise

        # Invalid rate - too high
        workspace_team.custom_remittance_rate = Decimal("150.00")
        with self.assertRaises(ValidationError):
            workspace_team.full_clean()

        # Invalid rate - negative
        workspace_team.custom_remittance_rate = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            workspace_team.full_clean()

    @pytest.mark.django_db
    def test_workspace_team_same_team_different_workspaces(self):
        """Test that same team can be in different workspaces."""
        organization = OrganizationFactory()
        team = TeamFactory(organization=organization)
        workspace1 = WorkspaceFactory(organization=organization)
        workspace2 = WorkspaceFactory(organization=organization)

        workspace_team1 = WorkspaceTeamFactory(workspace=workspace1, team=team)
        workspace_team2 = WorkspaceTeamFactory(workspace=workspace2, team=team)

        self.assertEqual(workspace_team1.team, workspace_team2.team)
        self.assertNotEqual(workspace_team1.workspace, workspace_team2.workspace)


@pytest.mark.unit
class TestWorkspaceExchangeRateModel(TestCase):
    """Test the WorkspaceExchangeRate model."""

    @pytest.mark.django_db
    def test_workspace_exchange_rate_creation(self):
        """Test creating workspace exchange rate."""
        workspace = WorkspaceFactory()
        member = OrganizationMemberFactory(organization=workspace.organization)
        currency = Currency.objects.create(code="EUR", name="Euro")

        exchange_rate = WorkspaceExchangeRate.objects.create(
            workspace=workspace,
            currency=currency,
            rate=Decimal("1.20"),
            effective_date=date.today(),
            added_by=member,
            note="Test rate",
        )

        self.assertEqual(exchange_rate.workspace, workspace)
        self.assertEqual(exchange_rate.currency, currency)
        self.assertEqual(exchange_rate.rate, Decimal("1.20"))
        self.assertEqual(exchange_rate.added_by, member)
        self.assertFalse(exchange_rate.is_approved)
        self.assertIsNone(exchange_rate.approved_by)
        self.assertIsNotNone(exchange_rate.workspace_exchange_rate_id)

    @pytest.mark.django_db
    def test_workspace_exchange_rate_approval(self):
        """Test workspace exchange rate approval."""
        exchange_rate = WorkspaceExchangeRateFactory()
        approver = OrganizationMemberFactory(
            organization=exchange_rate.workspace.organization
        )

        exchange_rate.is_approved = True
        exchange_rate.approved_by = approver
        exchange_rate.save()

        self.assertTrue(exchange_rate.is_approved)
        self.assertEqual(exchange_rate.approved_by, approver)

    @pytest.mark.django_db
    def test_workspace_exchange_rate_unique_constraint(self):
        """Test unique constraint for workspace, currency, and effective date."""
        workspace = WorkspaceFactory()
        currency = Currency.objects.create(code="GBP", name="British Pound")
        effective_date = date.today()

        WorkspaceExchangeRateFactory(
            workspace=workspace,
            currency=currency,
            effective_date=effective_date,
        )

        with self.assertRaises(IntegrityError):
            WorkspaceExchangeRateFactory(
                workspace=workspace,
                currency=currency,
                effective_date=effective_date,
            )

    @pytest.mark.django_db
    def test_workspace_exchange_rate_different_dates_allowed(self):
        """Test that same workspace and currency allowed for different dates."""
        workspace = WorkspaceFactory()
        currency = Currency.objects.create(code="JPY", name="Japanese Yen")

        rate1 = WorkspaceExchangeRateFactory(
            workspace=workspace,
            currency=currency,
            effective_date=date.today(),
        )
        rate2 = WorkspaceExchangeRateFactory(
            workspace=workspace,
            currency=currency,
            effective_date=date.today() + timedelta(days=1),
        )

        self.assertEqual(rate1.workspace, rate2.workspace)
        self.assertEqual(rate1.currency, rate2.currency)
        self.assertNotEqual(rate1.effective_date, rate2.effective_date)

    @pytest.mark.django_db
    def test_workspace_exchange_rate_different_workspaces_allowed(self):
        """Test that same currency and date allowed for different workspaces."""
        organization = OrganizationFactory()
        workspace1 = WorkspaceFactory(organization=organization)
        workspace2 = WorkspaceFactory(organization=organization)
        currency = Currency.objects.create(code="CAD", name="Canadian Dollar")
        effective_date = date.today()

        rate1 = WorkspaceExchangeRateFactory(
            workspace=workspace1,
            currency=currency,
            effective_date=effective_date,
        )
        rate2 = WorkspaceExchangeRateFactory(
            workspace=workspace2,
            currency=currency,
            effective_date=effective_date,
        )

        self.assertNotEqual(rate1.workspace, rate2.workspace)
        self.assertEqual(rate1.currency, rate2.currency)
        self.assertEqual(rate1.effective_date, rate2.effective_date)

    @pytest.mark.django_db
    def test_workspace_exchange_rate_soft_delete(self):
        """Test soft delete behavior of workspace exchange rate."""
        exchange_rate = WorkspaceExchangeRateFactory()
        exchange_rate_id = exchange_rate.workspace_exchange_rate_id

        # Soft delete
        exchange_rate.delete()

        # Should not exist in normal queryset
        self.assertFalse(
            WorkspaceExchangeRate.objects.filter(
                workspace_exchange_rate_id=exchange_rate_id
            ).exists()
        )

        # Should exist in all_objects queryset
        self.assertTrue(
            WorkspaceExchangeRate.all_objects.filter(
                workspace_exchange_rate_id=exchange_rate_id
            ).exists()
        )

    @pytest.mark.django_db
    def test_workspace_exchange_rate_unique_constraint_with_soft_delete(self):
        """Test unique constraint respects soft delete."""
        workspace = WorkspaceFactory()
        currency = Currency.objects.create(code="AUD", name="Australian Dollar")
        effective_date = date.today()

        # Create and soft delete first rate
        rate1 = WorkspaceExchangeRateFactory(
            workspace=workspace,
            currency=currency,
            effective_date=effective_date,
        )
        rate1.delete()

        # Should be able to create another with same values after soft delete
        rate2 = WorkspaceExchangeRateFactory(
            workspace=workspace,
            currency=currency,
            effective_date=effective_date,
        )

        self.assertIsNotNone(rate2)
        self.assertNotEqual(
            rate1.workspace_exchange_rate_id, rate2.workspace_exchange_rate_id
        )
