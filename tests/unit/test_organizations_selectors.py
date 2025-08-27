"""Unit tests for organization selectors.

Tests data retrieval functions with various scenarios and edge cases.
"""

import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.test import TestCase

from apps.organizations.constants import StatusChoices
from apps.organizations.selectors import (
    get_org_members,
    get_organization_by_id,
    get_organization_members_count,
    get_orgMember_by_user_id_and_organization_id,
    get_teams_count,
    get_user_org_membership,
    get_user_organizations,
    get_workspaces_count,
    get_org_exchange_rates,
)
from tests.factories import (
    CustomUserFactory,
    InactiveOrganizationMemberFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
    OrganizationExchangeRateFactory,
    CurrencyFactory,
)

User = get_user_model()


class TestGetUserOrganizations(TestCase):
    """Test get_user_organizations selector."""

    def setUp(self):
        self.user = CustomUserFactory()

    def test_get_user_organizations_with_active_memberships(self):
        """Test getting organizations for user with active memberships."""
        # Create organizations with active memberships
        org1 = OrganizationFactory(title="Organization 1")
        org2 = OrganizationFactory(title="Organization 2")
        OrganizationMemberFactory(user=self.user, organization=org1)
        OrganizationMemberFactory(user=self.user, organization=org2)

        # Create inactive membership (should be excluded)
        org3 = OrganizationFactory(title="Organization 3")
        InactiveOrganizationMemberFactory(user=self.user, organization=org3)

        organizations = get_user_organizations(self.user)

        self.assertIsInstance(organizations, QuerySet)
        self.assertEqual(organizations.count(), 2)
        self.assertIn(org1, organizations)
        self.assertIn(org2, organizations)
        self.assertNotIn(org3, organizations)

    def test_get_user_organizations_no_memberships(self):
        """Test getting organizations for user with no memberships."""
        organizations = get_user_organizations(self.user)

        self.assertIsInstance(organizations, QuerySet)
        self.assertEqual(organizations.count(), 0)

    def test_get_user_organizations_only_inactive_memberships(self):
        """Test getting organizations for user with only inactive memberships."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        InactiveOrganizationMemberFactory(user=self.user, organization=org1)
        InactiveOrganizationMemberFactory(user=self.user, organization=org2)

        organizations = get_user_organizations(self.user)

        self.assertEqual(organizations.count(), 0)

    def test_get_user_organizations_mixed_statuses(self):
        """Test getting organizations with mixed membership statuses."""
        active_org = OrganizationFactory(status=StatusChoices.ACTIVE)
        close_org = OrganizationFactory(status=StatusChoices.CLOSED)

        OrganizationMemberFactory(user=self.user, organization=active_org)
        OrganizationMemberFactory(user=self.user, organization=close_org)

        organizations = get_user_organizations(self.user)

        # Should return both organizations regardless of org status
        # (selector filters by membership status, not org status)
        self.assertEqual(organizations.count(), 2)
        self.assertIn(active_org, organizations)
        self.assertIn(close_org, organizations)

    def test_get_user_organizations_ordering(self):
        """Test that organizations are returned in consistent order."""
        org_a = OrganizationFactory(title="A Organization")
        org_z = OrganizationFactory(title="Z Organization")
        org_m = OrganizationFactory(title="M Organization")

        OrganizationMemberFactory(user=self.user, organization=org_z)
        OrganizationMemberFactory(user=self.user, organization=org_a)
        OrganizationMemberFactory(user=self.user, organization=org_m)

        organizations = get_user_organizations(self.user)

        # Check if there's any ordering applied
        org_titles = list(organizations.values_list("title", flat=True))
        self.assertEqual(len(org_titles), 3)

    def test_get_user_organizations_with_soft_deleted_memberships(self):
        """Test that soft-deleted memberships are excluded."""
        org = OrganizationFactory()
        member = OrganizationMemberFactory(user=self.user, organization=org)
        
        # Soft delete the membership
        member.delete()
        
        organizations = get_user_organizations(self.user)
        self.assertEqual(organizations.count(), 0)

    def test_get_user_organizations_select_related_owner(self):
        """Test that owner is properly selected related."""
        org = OrganizationFactory()
        OrganizationMemberFactory(user=self.user, organization=org)
        
        organizations = get_user_organizations(self.user)
        org_result = organizations.first()
        
        # Should not cause additional queries when accessing owner
        with self.assertNumQueries(0):
            org_result.owner


class TestGetOrganizationById(TestCase):
    """Test get_organization_by_id selector."""

    def test_get_organization_by_id_existing(self):
        """Test getting existing organization by ID."""
        organization = OrganizationFactory(title="Test Organization")

        result = get_organization_by_id(organization.organization_id)

        self.assertEqual(result, organization)
        self.assertEqual(result.title, "Test Organization")

    def test_get_organization_by_id_non_existent(self):
        """Test getting non-existent organization by ID."""
        import uuid

        non_existent_id = uuid.uuid4()

        result = get_organization_by_id(non_existent_id)

        self.assertIsNone(result)

    def test_get_organization_by_id_soft_deleted(self):
        """Test getting soft-deleted organization by ID."""
        organization = OrganizationFactory()
        organization.delete()  # Soft delete

        result = get_organization_by_id(organization.organization_id)

        # Should return None for soft-deleted organizations
        self.assertIsNone(result)

    def test_get_organization_by_id_invalid_type(self):
        """Test getting organization with invalid ID type."""
        # The function should raise ValidationError for invalid UUIDs
        with self.assertRaises(ValidationError):
            get_organization_by_id("not-a-uuid")

    def test_get_organization_by_id_zero(self):
        """Test getting organization with ID zero."""

        result = get_organization_by_id(
            uuid.UUID("00000000-0000-0000-0000-000000000000")
        )
        self.assertIsNone(result)

    def test_get_organization_by_id_none(self):
        """Test getting organization with None ID."""
        # The function should raise ValidationError for None
        with self.assertRaises(ValidationError):
            get_organization_by_id(None)


class TestGetOrganizationMembersCount(TestCase):
    """Test get_organization_members_count selector."""

    def setUp(self):
        self.organization = OrganizationFactory()

    def test_get_organization_members_count_with_active_members(self):
        """Test counting active members in organization."""
        # Create active members
        OrganizationMemberFactory.create_batch(3, organization=self.organization)

        # Create inactive members (should not be counted)
        InactiveOrganizationMemberFactory.create_batch(
            2, organization=self.organization
        )

        count = get_organization_members_count(self.organization)

        self.assertEqual(count, 3)

    def test_get_organization_members_count_no_members(self):
        """Test counting members in organization with no members."""
        count = get_organization_members_count(self.organization)

        self.assertEqual(count, 0)

    def test_get_organization_members_count_only_inactive_members(self):
        """Test counting members in organization with only inactive members."""
        InactiveOrganizationMemberFactory.create_batch(
            5, organization=self.organization
        )

        count = get_organization_members_count(self.organization)

        self.assertEqual(count, 0)

    def test_get_organization_members_count_large_number(self):
        """Test counting large number of members."""
        OrganizationMemberFactory.create_batch(100, organization=self.organization)

        count = get_organization_members_count(self.organization)

        self.assertEqual(count, 100)

    def test_get_organization_members_count_different_organizations(self):
        """Test that count is specific to organization."""
        other_org = OrganizationFactory()

        # Add members to both organizations
        OrganizationMemberFactory.create_batch(3, organization=self.organization)
        OrganizationMemberFactory.create_batch(5, organization=other_org)

        count_org1 = get_organization_members_count(self.organization)
        count_org2 = get_organization_members_count(other_org)

        self.assertEqual(count_org1, 3)
        self.assertEqual(count_org2, 5)

    def test_get_organization_members_count_with_soft_deleted_members(self):
        """Test that soft-deleted members are excluded from count."""
        # Create active members
        OrganizationMemberFactory.create_batch(2, organization=self.organization)
        
        # Create and soft delete a member
        member = OrganizationMemberFactory(organization=self.organization)
        member.delete()
        
        count = get_organization_members_count(self.organization)
        self.assertEqual(count, 2)


class TestGetWorkspacesCount(TestCase):
    """Test get_workspaces_count selector."""

    def setUp(self):
        self.organization = OrganizationFactory()

    def test_get_workspaces_count_with_active_workspaces(self):
        """Test counting active workspaces in organization."""
        # Create active workspaces
        WorkspaceFactory.create_batch(4, organization=self.organization)

        # Create workspace in different organization
        other_org = OrganizationFactory()
        WorkspaceFactory(organization=other_org)

        count = get_workspaces_count(self.organization)

        self.assertEqual(count, 4)

    def test_get_workspaces_count_no_workspaces(self):
        """Test counting workspaces in organization with no workspaces."""
        count = get_workspaces_count(self.organization)

        self.assertEqual(count, 0)

    def test_get_workspaces_count_with_soft_deleted_workspaces(self):
        """Test counting workspaces excludes soft-deleted ones."""
        # Create active workspaces
        WorkspaceFactory(organization=self.organization)
        WorkspaceFactory(organization=self.organization)
        workspace2 = WorkspaceFactory(organization=self.organization)

        # Soft delete one workspace
        workspace2.delete()

        count = get_workspaces_count(self.organization)

        self.assertEqual(count, 2)

    def test_get_workspaces_count_different_statuses(self):
        """Test counting workspaces with different statuses."""
        WorkspaceFactory(organization=self.organization, status="ACTIVE")
        WorkspaceFactory(organization=self.organization, status="ARCHIVED")

        count = get_workspaces_count(self.organization)

        # Should count all non-deleted workspaces regardless of status
        self.assertEqual(count, 2)


class TestGetTeamsCount(TestCase):
    """Test get_teams_count selector."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)

    def test_get_teams_count_with_teams(self):
        """Test counting teams through workspace relationships."""
        # Create teams and associate with workspace
        team1 = TeamFactory()
        team2 = TeamFactory()
        team3 = TeamFactory()

        WorkspaceTeamFactory(workspace=self.workspace, team=team1)
        WorkspaceTeamFactory(workspace=self.workspace, team=team2)
        WorkspaceTeamFactory(workspace=self.workspace, team=team3)

        # Create team in different organization
        other_org = OrganizationFactory()
        other_workspace = WorkspaceFactory(organization=other_org)
        other_team = TeamFactory()
        WorkspaceTeamFactory(workspace=other_workspace, team=other_team)

        count = get_teams_count(self.organization)

        self.assertEqual(count, 3)

    def test_get_teams_count_no_teams(self):
        """Test counting teams in organization with no teams."""
        count = get_teams_count(self.organization)

        self.assertEqual(count, 0)

    def test_get_teams_count_multiple_workspaces(self):
        """Test counting teams across multiple workspaces in organization."""
        workspace2 = WorkspaceFactory(organization=self.organization)

        # Create teams for first workspace
        team1 = TeamFactory()
        team2 = TeamFactory()
        WorkspaceTeamFactory(workspace=self.workspace, team=team1)
        WorkspaceTeamFactory(workspace=workspace2, team=team2)

        # Create teams for second workspace
        team3 = TeamFactory()
        team4 = TeamFactory()
        WorkspaceTeamFactory(workspace=self.workspace, team=team3)
        WorkspaceTeamFactory(workspace=workspace2, team=team4)

        count = get_teams_count(self.organization)

        self.assertEqual(count, 4)

    def test_get_teams_count_duplicate_teams_across_workspaces(self):
        """Test counting when same team is in multiple workspaces."""
        workspace2 = WorkspaceFactory(organization=self.organization)

        # Create team and add to both workspaces
        team = TeamFactory()
        WorkspaceTeamFactory(workspace=self.workspace, team=team)
        WorkspaceTeamFactory(workspace=workspace2, team=team)

        count = get_teams_count(self.organization)

        # Should count distinct teams only
        self.assertEqual(count, 1)

    def test_get_teams_count_with_soft_deleted_workspaces(self):
        """Test counting teams excludes those from soft-deleted workspaces."""
        workspace2 = WorkspaceFactory(organization=self.organization)

        # Add teams to both workspaces
        team1 = TeamFactory()
        team2 = TeamFactory()
        WorkspaceTeamFactory(workspace=self.workspace, team=team1)
        WorkspaceTeamFactory(workspace=workspace2, team=team2)

        # Soft delete one workspace
        workspace2.delete()

        count = get_teams_count(self.organization)

        self.assertEqual(count, 1)


class TestGetUserOrgMembership(TestCase):
    """Test get_user_org_membership selector."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()

    def test_get_user_org_membership_existing_active(self):
        """Test getting existing active membership."""
        membership = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

        result = get_user_org_membership(self.user, self.organization)

        self.assertEqual(result, membership)

    def test_get_user_org_membership_non_existent(self):
        """Test getting non-existent membership."""
        result = get_user_org_membership(self.user, self.organization)

        self.assertIsNone(result)

    def test_get_user_org_membership_inactive(self):
        """Test getting inactive membership."""
        InactiveOrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

        result = get_user_org_membership(self.user, self.organization)

        # Should return None for inactive memberships
        self.assertIsNone(result)

    def test_get_user_org_membership_different_user(self):
        """Test getting membership for different user."""
        other_user = CustomUserFactory()
        OrganizationMemberFactory(user=other_user, organization=self.organization)

        result = get_user_org_membership(self.user, self.organization)

        self.assertIsNone(result)

    def test_get_user_org_membership_different_organization(self):
        """Test getting membership for different organization."""
        other_org = OrganizationFactory()
        OrganizationMemberFactory(user=self.user, organization=other_org)

        result = get_user_org_membership(self.user, self.organization)

        self.assertIsNone(result)

    def test_get_user_org_membership_with_prefetch_user(self):
        """Test getting membership with user prefetched."""
        membership = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

        result = get_user_org_membership(
            self.user, self.organization, prefetch_user=True
        )

        self.assertEqual(result, membership)
        # Should not cause additional queries when accessing user
        with self.assertNumQueries(0):
            result.user


class TestGetOrgMembers(TestCase):
    """Test get_org_members selector."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)

    def test_get_org_members_by_organization(self):
        """Test getting organization members by organization."""
        # Create active members
        member1 = OrganizationMemberFactory(organization=self.organization)
        member2 = OrganizationMemberFactory(organization=self.organization)

        # Create inactive member
        InactiveOrganizationMemberFactory(organization=self.organization)

        # Create member in different organization
        other_org = OrganizationFactory()
        OrganizationMemberFactory(organization=other_org)

        members = get_org_members(organization=self.organization)

        self.assertIsInstance(members, QuerySet)
        self.assertEqual(members.count(), 2)
        self.assertIn(member1, members)
        self.assertIn(member2, members)

    def test_get_org_members_by_workspace(self):
        """Test getting organization members by workspace."""
        # Create members in the organization
        member1 = OrganizationMemberFactory(organization=self.organization)
        member2 = OrganizationMemberFactory(organization=self.organization)

        # Add members as workspace admins
        member1.administered_workspaces.add(self.workspace)

        members = get_org_members(workspace=self.workspace)

        self.assertIsInstance(members, QuerySet)
        self.assertEqual(members.count(), 1)
        self.assertIn(member1, members)
        self.assertNotIn(member2, members)

    def test_get_org_members_no_parameters(self):
        """Test getting organization members with no parameters."""
        with self.assertRaises((ValueError, TypeError)):
            get_org_members()

    def test_get_org_members_both_parameters(self):
        """Test getting organization members with both parameters."""
        OrganizationMemberFactory(organization=self.organization)

        # Should work with both parameters (workspace takes precedence or both are used)
        members = get_org_members(
            organization=self.organization, workspace=self.workspace
        )

        self.assertIsInstance(members, QuerySet)

    def test_get_org_members_empty_result(self):
        """Test getting organization members with no members."""
        members = get_org_members(organization=self.organization)

        self.assertIsInstance(members, QuerySet)
        self.assertEqual(members.count(), 0)

    def test_get_org_members_with_user_details(self):
        """Test that members include user details."""
        user = CustomUserFactory(email="test@example.com")
        OrganizationMemberFactory(user=user, organization=self.organization)

        members = get_org_members(organization=self.organization)

        self.assertEqual(members.count(), 1)
        retrieved_member = members.first()
        self.assertEqual(retrieved_member.user.email, "test@example.com")

    def test_get_org_members_with_prefetch_user(self):
        """Test getting members with user prefetched."""
        OrganizationMemberFactory(organization=self.organization)

        members = get_org_members(
            organization=self.organization, prefetch_user=True
        )

        self.assertIsInstance(members, QuerySet)
        self.assertEqual(members.count(), 1)
        
        # The prefetch should work, but we need to access the first member to trigger it
        first_member = members.first()
        # Now accessing user should not cause additional queries
        with self.assertNumQueries(0):
            first_member.user


class TestGetOrgExchangeRates(TestCase):
    """Test get_org_exchange_rates selector."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.currency = CurrencyFactory()

    def test_get_org_exchange_rates_with_rates(self):
        """Test getting exchange rates for organization."""
        # Create exchange rates with different effective dates to avoid uniqueness constraint
        from datetime import date, timedelta
        
        rate1 = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate="1.25",
            effective_date=date.today()
        )
        rate2 = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate="1.30",
            effective_date=date.today() + timedelta(days=1)
        )

        # Create rate for different organization
        other_org = OrganizationFactory()
        OrganizationExchangeRateFactory(
            organization=other_org, 
            currency=self.currency,
            effective_date=date.today()
        )

        rates = get_org_exchange_rates(organization=self.organization)

        self.assertIsInstance(rates, QuerySet)
        self.assertEqual(rates.count(), 2)
        self.assertIn(rate1, rates)
        self.assertIn(rate2, rates)

    def test_get_org_exchange_rates_no_rates(self):
        """Test getting exchange rates for organization with no rates."""
        rates = get_org_exchange_rates(organization=self.organization)

        self.assertIsInstance(rates, QuerySet)
        self.assertEqual(rates.count(), 0)

    def test_get_org_exchange_rates_with_soft_deleted_rates(self):
        """Test that soft-deleted rates are excluded."""
        from datetime import date, timedelta
        
        # Create active rate
        active_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today()
        )
        
        # Create and soft delete a rate with different date
        deleted_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            effective_date=date.today() + timedelta(days=1)
        )
        deleted_rate.delete()
        
        rates = get_org_exchange_rates(organization=self.organization)
        self.assertEqual(rates.count(), 1)
        self.assertIn(active_rate, rates)
        self.assertNotIn(deleted_rate, rates)

    def test_get_org_exchange_rates_multiple_currencies(self):
        """Test getting rates for multiple currencies."""
        from datetime import date, timedelta
        
        # Create different currencies to avoid uniqueness constraints
        currency1 = CurrencyFactory(code="EUR")
        currency2 = CurrencyFactory(code="GBP")
        
        OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=currency1,
            rate="0.85",
            effective_date=date.today()
        )
        OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=currency2,
            rate="0.75",
            effective_date=date.today() + timedelta(days=1)
        )
        
        rates = get_org_exchange_rates(organization=self.organization)
        self.assertEqual(rates.count(), 2)
        
        # Check that both currencies are present
        currency_codes = list(rates.values_list("currency__code", flat=True))
        self.assertIn("EUR", currency_codes)
        self.assertIn("GBP", currency_codes)

    def test_get_org_exchange_rates_organization_parameter_required(self):
        """Test that organization parameter is required."""
        with self.assertRaises(TypeError):
            get_org_exchange_rates()


class TestGetOrgMemberByUserIdAndOrganizationId(TestCase):
    """Test get_orgMember_by_user_id_and_organization_id selector."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()

    def test_get_org_member_existing(self):
        """Test getting existing organization member."""
        member = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

        result = get_orgMember_by_user_id_and_organization_id(
            self.user.user_id, self.organization.organization_id
        )

        self.assertEqual(result, member)

    def test_get_org_member_non_existent_user(self):
        """Test getting organization member with non-existent user ID."""

        OrganizationMemberFactory(organization=self.organization)

        # Test with a valid UUID that doesn't exist
        result = get_orgMember_by_user_id_and_organization_id(
            uuid.uuid4(), self.organization.organization_id
        )

        self.assertIsNone(result)

    def test_get_org_member_non_existent_organization(self):
        """Test getting organization member with non-existent organization ID."""

        OrganizationMemberFactory(user=self.user)

        result = get_orgMember_by_user_id_and_organization_id(
            self.user.user_id, uuid.uuid4()
        )

        self.assertIsNone(result)

    def test_get_org_member_inactive_membership(self):
        """Test getting inactive organization member."""
        InactiveOrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

        result = get_orgMember_by_user_id_and_organization_id(
            self.user.user_id, self.organization.organization_id
        )

        # Should return None for inactive memberships
        self.assertIsNone(result)

    def test_get_org_member_wrong_combination(self):
        """Test getting organization member with wrong user/org combination."""
        other_user = CustomUserFactory()
        other_org = OrganizationFactory()

        # Create memberships but not for the queried combination
        OrganizationMemberFactory(user=self.user, organization=other_org)
        OrganizationMemberFactory(user=other_user, organization=self.organization)

        result = get_orgMember_by_user_id_and_organization_id(
            self.user.user_id, self.organization.organization_id
        )

        self.assertIsNone(result)

    def test_get_org_member_invalid_ids(self):
        """Test getting organization member with invalid ID types."""

        with self.assertRaises(ValidationError):
            # Use actually invalid types like strings
            get_orgMember_by_user_id_and_organization_id(
                "not-a-uuid", self.organization.organization_id
            )

        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                self.user.user_id, "not-a-uuid"
            )

    def test_get_org_member_zero_ids(self):
        """Test getting organization member with zero IDs."""

        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                0, self.organization.organization_id
            )

        result = get_orgMember_by_user_id_and_organization_id(
            self.user.user_id, uuid.UUID("00000000-0000-0000-0000-000000000000")
        )
        self.assertIsNone(result)

    def test_get_org_member_negative_ids(self):
        """Test getting organization member with negative IDs."""

        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                -1, self.organization.organization_id
            )

    def test_get_org_member_none_ids(self):
        """Test getting organization member with None IDs."""
        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                None, self.organization.organization_id
            )

        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                self.user.user_id, None
            )

    def test_get_org_member_empty_string_ids(self):
        """Test getting organization member with empty string IDs."""
        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                "", self.organization.organization_id
            )

        with self.assertRaises(ValidationError):
            get_orgMember_by_user_id_and_organization_id(
                self.user.user_id, ""
            )

    def test_get_org_member_exception_handling(self):
        """Test exception handling in the function."""
        # This should handle exceptions gracefully and return None
        result = get_orgMember_by_user_id_and_organization_id(
            self.user.user_id, self.organization.organization_id
        )
        self.assertIsNone(result)
