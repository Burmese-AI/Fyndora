"""
Performance and system tests for the teams app.

Following the test plan: Teams App (apps.teams)
- Performance tests for team operations with large datasets
- System tests for team management workflows under load
- Load testing for team member operations
"""

import pytest
import time
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse

from apps.teams.constants import TeamMemberRole
from apps.teams.models import Team, TeamMember
from tests.factories import (
    CustomUserFactory,
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
    TeamFactory,
    TeamMemberFactory,
)


@pytest.mark.performance
class TestTeamCreationPerformance(TransactionTestCase):
    """Test team creation performance under various loads."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner

    @pytest.mark.django_db
    def test_single_team_creation_performance(self):
        """Test time to create a single team."""
        start_time = time.time()

        team = Team.objects.create(
            title="Performance Test Team",
            description="Testing team creation performance",
            organization=self.organization,
            created_by=self.org_member,
            team_coordinator=self.org_member,
        )

        end_time = time.time()
        creation_time = end_time - start_time

        # Team creation should be reasonably fast (under 1 second)
        self.assertLess(creation_time, 1.0)
        self.assertIsNotNone(team)

    @pytest.mark.django_db
    def test_bulk_team_creation_performance(self):
        """Test performance of creating multiple teams."""
        start_time = time.time()

        teams = []
        for i in range(100):
            team = Team.objects.create(
                title=f"Bulk Team {i}",
                description=f"Bulk team creation test {i}",
                organization=self.organization,
                created_by=self.org_member,
                team_coordinator=self.org_member,
            )
            teams.append(team)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_team = total_time / 100

        # Average creation time should be reasonable
        self.assertLess(avg_time_per_team, 0.1)  # Less than 100ms per team
        self.assertEqual(len(teams), 100)

    @pytest.mark.django_db
    def test_team_factory_performance(self):
        """Test performance of factory-based team creation."""
        start_time = time.time()

        teams = [TeamFactory(organization=self.organization) for _ in range(50)]

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_team = total_time / 50

        # Factory creation should be efficient
        self.assertLess(avg_time_per_team, 0.2)  # Less than 200ms per team
        self.assertEqual(len(teams), 50)


@pytest.mark.performance
class TestTeamMemberPerformance(TransactionTestCase):
    """Test team member operations performance under load."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner
        self.team = TeamFactory(organization=self.organization)

    @pytest.mark.django_db
    def test_single_team_member_creation_performance(self):
        """Test time to create a single team member."""
        member = OrganizationMemberFactory(organization=self.organization)

        start_time = time.time()

        team_member = TeamMember.objects.create(
            organization_member=member,
            team=self.team,
            role=TeamMemberRole.SUBMITTER,
        )

        end_time = time.time()
        creation_time = end_time - start_time

        # Team member creation should be fast
        self.assertLess(creation_time, 0.5)
        self.assertIsNotNone(team_member)

    @pytest.mark.django_db
    def test_bulk_team_member_creation_performance(self):
        """Test performance of creating multiple team members."""
        # Create organization members first
        members = [
            OrganizationMemberFactory(organization=self.organization) for _ in range(100)
        ]

        start_time = time.time()

        team_members = []
        for i, member in enumerate(members):
            role = TeamMemberRole.SUBMITTER if i % 2 == 0 else TeamMemberRole.AUDITOR
            team_member = TeamMember.objects.create(
                organization_member=member,
                team=self.team,
                role=role,
            )
            team_members.append(team_member)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_member = total_time / 100

        # Average creation time should be reasonable
        self.assertLess(avg_time_per_member, 0.05)  # Less than 50ms per member
        self.assertEqual(len(team_members), 100)

    @pytest.mark.django_db
    def test_team_member_factory_performance(self):
        """Test performance of factory-based team member creation."""
        start_time = time.time()

        team_members = [TeamMemberFactory(team=self.team) for _ in range(50)]

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_member = total_time / 50

        # Factory creation should be efficient
        self.assertLess(avg_time_per_member, 0.1)  # Less than 100ms per member
        self.assertEqual(len(team_members), 50)


@pytest.mark.performance
class TestTeamViewsPerformance(TestCase):
    """Test team views performance with large datasets."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner
        self.client.force_login(self.user)

    @pytest.mark.django_db
    def test_large_team_member_list_performance(self):
        """Test performance with large number of team members."""
        team = TeamFactory(organization=self.organization)
        
        # Create multiple team members
        members = []
        for i in range(100):  # Large dataset for performance testing
            org_member = OrganizationMemberFactory(organization=self.organization)
            team_member = TeamMemberFactory(
                organization_member=org_member,
                team=team,
                role=TeamMemberRole.SUBMITTER if i % 2 == 0 else TeamMemberRole.AUDITOR
            )
            members.append(team_member)

        url = reverse(
            "team_members",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        # Measure response time
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        response_time = end_time - start_time

        # Response should be fast even with large dataset
        self.assertLess(response_time, 2.0)  # Less than 2 seconds
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["team_members"].count(), 100)

    @pytest.mark.django_db
    def test_multiple_teams_listing_performance(self):
        """Test performance when listing multiple teams."""
        # Create multiple teams
        teams = []
        for i in range(200):  # Large dataset for performance testing
            team = TeamFactory(
                organization=self.organization,
                title=f"Performance Test Team {i}",
                created_by=self.org_member,
            )
            teams.append(team)

        url = reverse(
            "teams", kwargs={"organization_id": self.organization.organization_id}
        )

        # Measure response time
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        response_time = end_time - start_time

        # Response should be fast even with large dataset
        self.assertLess(response_time, 3.0)  # Less than 3 seconds
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["teams"]), 200)

    @pytest.mark.django_db
    def test_team_creation_form_performance(self):
        """Test performance of team creation form rendering."""
        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        # Measure form rendering time
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        response_time = end_time - start_time

        # Form rendering should be fast
        self.assertLess(response_time, 1.0)  # Less than 1 second
        self.assertEqual(response.status_code, 200)

    @pytest.mark.django_db
    def test_team_member_addition_performance(self):
        """Test performance of adding team members via form."""
        team = TeamFactory(organization=self.organization)
        members = [
            OrganizationMemberFactory(organization=self.organization) for _ in range(10)
        ]

        url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        # Measure time to add multiple members
        start_time = time.time()

        for member in members:
            form_data = {
                "organization_member": member.pk,
                "role": TeamMemberRole.SUBMITTER,
            }
            response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_addition = total_time / 10

        # Average addition time should be reasonable
        self.assertLess(avg_time_per_addition, 0.5)  # Less than 500ms per addition
        self.assertEqual(TeamMember.objects.filter(team=team).count(), 10)


@pytest.mark.system
class TestTeamSystemWorkflows(TransactionTestCase):
    """System tests for complete team management workflows under load."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner
        self.client.force_login(self.user)

    @pytest.mark.django_db
    def test_high_volume_team_operations_system_test(self):
        """Test system behavior under high volume team operations."""
        # Create multiple teams with members
        teams_count = 20
        members_per_team = 10

        start_time = time.time()

        created_teams = []
        for i in range(teams_count):
            # Create team
            create_url = reverse(
                "create_team", kwargs={"organization_id": self.organization.organization_id}
            )

            team_data = {
                "title": f"High Volume Team {i}",
                "description": f"System test team {i}",
                "team_coordinator": self.org_member.pk,
            }

            response = self.client.post(create_url, data=team_data)
            self.assertEqual(response.status_code, 302)

            team = Team.objects.get(title=f"High Volume Team {i}")
            created_teams.append(team)

            # Add members to team
            add_member_url = reverse(
                "add_team_member",
                kwargs={
                    "organization_id": self.organization.organization_id,
                    "team_id": team.team_id,
                },
            )

            for j in range(members_per_team):
                member = OrganizationMemberFactory(organization=self.organization)
                member_data = {
                    "organization_member": member.pk,
                    "role": TeamMemberRole.SUBMITTER if j % 2 == 0 else TeamMemberRole.AUDITOR,
                }

                response = self.client.post(
                    add_member_url, data=member_data, HTTP_HX_REQUEST="true"
                )
                self.assertEqual(response.status_code, 200)

        end_time = time.time()
        total_time = end_time - start_time

        # System should handle high volume operations efficiently
        self.assertLess(total_time, 30.0)  # Less than 30 seconds for all operations
        self.assertEqual(len(created_teams), teams_count)

        # Verify all team members were created
        total_members = TeamMember.objects.filter(team__in=created_teams).count()
        self.assertEqual(total_members, teams_count * members_per_team)

    @pytest.mark.django_db
    def test_concurrent_team_member_operations_system_test(self):
        """Test system behavior with concurrent team member operations."""
        team = TeamFactory(organization=self.organization)
        members = [
            OrganizationMemberFactory(organization=self.organization) for _ in range(20)
        ]

        add_url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        start_time = time.time()

        # Simulate concurrent additions
        for member in members:
            member_data = {
                "organization_member": member.pk,
                "role": TeamMemberRole.SUBMITTER,
            }

            response = self.client.post(add_url, data=member_data, HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)

        end_time = time.time()
        total_time = end_time - start_time

        # Operations should complete efficiently
        self.assertLess(total_time, 10.0)  # Less than 10 seconds
        self.assertEqual(TeamMember.objects.filter(team=team).count(), 20)

    @pytest.mark.django_db
    def test_team_deletion_with_large_membership_system_test(self):
        """Test system behavior when deleting teams with large membership."""
        team = TeamFactory(organization=self.organization)

        # Create large membership
        members = []
        for i in range(50):
            org_member = OrganizationMemberFactory(organization=self.organization)
            team_member = TeamMemberFactory(
                organization_member=org_member,
                team=team,
                role=TeamMemberRole.SUBMITTER if i % 2 == 0 else TeamMemberRole.AUDITOR
            )
            members.append(team_member)

        # Verify setup
        self.assertEqual(TeamMember.objects.filter(team=team).count(), 50)

        delete_url = reverse(
            "delete_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        start_time = time.time()

        # Delete team (should cascade delete all members)
        response = self.client.post(delete_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        end_time = time.time()
        deletion_time = end_time - start_time

        # Deletion should be efficient even with large membership
        self.assertLess(deletion_time, 5.0)  # Less than 5 seconds

        # Verify team and all members were deleted
        with self.assertRaises(Team.DoesNotExist):
            Team.objects.get(team_id=team.team_id)

        self.assertEqual(TeamMember.objects.filter(team=team).count(), 0)

    @pytest.mark.django_db
    def test_organization_with_many_teams_system_test(self):
        """Test system behavior with organization containing many teams."""
        # Create many teams
        teams = [
            TeamFactory(organization=self.organization) for _ in range(100)
        ]

        # Add members to some teams
        for i, team in enumerate(teams[:20]):  # Add members to first 20 teams
            for j in range(5):
                org_member = OrganizationMemberFactory(organization=self.organization)
                TeamMemberFactory(
                    organization_member=org_member,
                    team=team,
                    role=TeamMemberRole.SUBMITTER if j % 2 == 0 else TeamMemberRole.AUDITOR
                )

        # Test teams listing performance
        url = reverse(
            "teams", kwargs={"organization_id": self.organization.organization_id}
        )

        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        response_time = end_time - start_time

        # Should handle large number of teams efficiently
        self.assertLess(response_time, 5.0)  # Less than 5 seconds
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["teams"]), 100)

        # Verify database integrity
        self.assertEqual(Team.objects.filter(organization=self.organization).count(), 100)
        self.assertEqual(
            TeamMember.objects.filter(team__organization=self.organization).count(), 100
        )  # 20 teams * 5 members each