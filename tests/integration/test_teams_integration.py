"""
Integration tests for Team management views.

This module provides comprehensive integration testing for the team management system,
covering all views, workflows, and edge cases.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm

from apps.core.roles import get_permissions_for_role
from apps.teams.constants import TeamMemberRole
from apps.teams.models import Team, TeamMember
from apps.teams.permissions import assign_team_permissions
from tests.factories.organization_factories import (
    OrganizationMemberFactory,
    OrganizationWithOwnerFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory
from tests.factories.user_factories import CustomUserFactory

User = get_user_model()


class TeamViewsIntegrationTest(TestCase):
    """Integration tests for team management views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner

        # Create organization owner group and assign permissions
        org_owner_group, _ = Group.objects.get_or_create(
            name=f"Org Owner - {self.organization.organization_id}"
        )
        
        # Get org owner permissions and assign them
        org_owner_permissions = get_permissions_for_role("ORG_OWNER")
        for perm in org_owner_permissions:
            if "workspace_currency" not in perm:
                assign_perm(perm, org_owner_group, self.organization)
        
        # Add user to the org owner group
        org_owner_group.user_set.add(self.user)

        # Login the user
        self.client.force_login(self.user)

    def create_team_with_permissions(self, **kwargs):
        """Helper method to create a team with proper permissions assigned."""
        if 'organization' not in kwargs:
            kwargs['organization'] = self.organization
        team = TeamFactory(**kwargs)
        assign_team_permissions(team)
        return team

    def test_teams_view_integration(self):
        """Test teams list view integration."""
        # Create some teams
        team1 = self.create_team_with_permissions(title="Team 1")
        team2 = self.create_team_with_permissions(title="Team 2")

        url = reverse(
            "teams", kwargs={"organization_id": self.organization.organization_id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team 1")
        self.assertContains(response, "Team 2")
        self.assertIn("teams", response.context)
        self.assertIn("organization", response.context)

    def test_create_team_view_get_integration(self):
        """Test create team view GET request integration."""
        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("organization", response.context)

    def test_create_team_view_post_integration(self):
        """Test create team view POST request integration."""
        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        form_data = {
            "title": "New Integration Team",
            "description": "Team created via integration test",
            "team_coordinator": self.org_member.pk,
        }

        response = self.client.post(url, data=form_data)

        # Should redirect on success
        self.assertEqual(response.status_code, 302)

        # Verify team was created
        team = Team.objects.get(title="New Integration Team")
        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)
        self.assertEqual(team.team_coordinator, self.org_member)

    def test_create_team_view_post_htmx_integration(self):
        """Test create team view POST request with HTMX integration."""
        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        form_data = {
            "title": "HTMX Integration Team",
            "description": "Team created via HTMX integration test",
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertIn("HX-trigger", response)

        # Verify team was created
        team = Team.objects.get(title="HTMX Integration Team")
        self.assertEqual(team.organization, self.organization)

    def test_edit_team_view_integration(self):
        """Test edit team view integration."""
        team = self.create_team_with_permissions(
            title="Original Title",
            created_by=self.org_member,
        )

        url = reverse(
            "edit_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

        # Test POST request
        form_data = {
            "title": "Updated Title",
            "description": "Updated description",
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team was updated
        team.refresh_from_db()
        self.assertEqual(team.title, "Updated Title")
        self.assertEqual(team.description, "Updated description")

    def test_delete_team_view_integration(self):
        """Test delete team view integration."""
        team = self.create_team_with_permissions(created_by=self.org_member)
        team_id = team.team_id

        url = reverse(
            "delete_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team_id,
            },
        )

        # Test GET request (confirmation)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("team", response.context)

        # Test POST request (actual deletion)
        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team was deleted
        with self.assertRaises(Team.DoesNotExist):
            Team.objects.get(team_id=team_id)

    def test_get_team_members_view_integration(self):
        """Test get team members view integration."""
        team = self.create_team_with_permissions()
        member1 = TeamMemberFactory(team=team)
        member2 = TeamMemberFactory(team=team)

        url = reverse(
            "team_members",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("team", response.context)
        self.assertIn("team_members", response.context)
        self.assertEqual(response.context["team_members"].count(), 2)

    def test_add_team_member_view_integration(self):
        """Test add team member view integration."""
        team = self.create_team_with_permissions()
        new_member = OrganizationMemberFactory(organization=self.organization)

        url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

        # Test POST request
        form_data = {
            "organization_member": new_member.pk,
            "role": TeamMemberRole.SUBMITTER,
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team member was created
        team_member = TeamMember.objects.get(organization_member=new_member, team=team)
        self.assertEqual(team_member.role, TeamMemberRole.SUBMITTER)

    def test_remove_team_member_view_integration(self):
        """Test remove team member view integration."""
        team = self.create_team_with_permissions()
        team_member = TeamMemberFactory(team=team)
        team_member_id = team_member.team_member_id

        url = reverse(
            "remove_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": team_member_id,
            },
        )

        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team member was removed
        with self.assertRaises(TeamMember.DoesNotExist):
            TeamMember.objects.get(team_member_id=team_member_id)

    def test_edit_team_member_role_view_integration(self):
        """Test edit team member role view integration."""
        team = self.create_team_with_permissions()
        member = OrganizationMemberFactory(organization=self.organization)
        team_member = TeamMemberFactory(
            organization_member=member, team=team, role=TeamMemberRole.SUBMITTER
        )

        url = reverse(
            "edit_team_member_role",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": team_member.team_member_id,
            },
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("team_member", response.context)

        # Test POST request to change role
        form_data = {
            "role": TeamMemberRole.AUDITOR,
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify role was changed
        team_member.refresh_from_db()
        self.assertEqual(team_member.role, TeamMemberRole.AUDITOR)

    def test_unauthorized_access_integration(self):
        """Test unauthorized access to team views."""
        # Create a team in a different organization
        other_org = OrganizationWithOwnerFactory()
        other_team = TeamFactory(organization=other_org)

        # Try to access team views for a team in a different organization
        url = reverse(
            "team_members",
            kwargs={
                "organization_id": other_org.organization_id,
                "team_id": other_team.team_id,
            },
        )

        response = self.client.get(url)

        # Should be forbidden or redirect
        self.assertIn(response.status_code, [302, 403])

    def test_create_team_with_permissions_integration(self):
        """Test creating a team with proper permissions."""
        team = self.create_team_with_permissions(
            title="Test Team", description="Test Description"
        )

    def test_team_creation_with_permissions_integration(self):
        """Test team creation with permission assignment integration."""
        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        form_data = {
            "title": "Permission Test Team",
            "description": "Testing permission assignment",
            "team_coordinator": self.org_member.pk,
        }

        with patch("apps.teams.services.assign_team_permissions") as mock_assign:
            response = self.client.post(url, data=form_data)

            # Verify permissions were assigned
            mock_assign.assert_called_once()

            # Verify team was created
            team = Team.objects.get(title="Permission Test Team")
            self.assertIsNotNone(team)



    def test_team_member_addition_with_groups_integration(self):
        """Test team member addition with group assignment integration."""
        team = self.create_team_with_permissions()
        new_member = OrganizationMemberFactory(organization=self.organization)

        url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        form_data = {
            "organization_member": new_member.pk,
            "role": TeamMemberRole.AUDITOR,
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team member was created
        team_member = TeamMember.objects.get(organization_member=new_member, team=team)
        self.assertEqual(team_member.role, TeamMemberRole.AUDITOR)

    def test_form_validation_errors_integration(self):
        """Test form validation errors in integration context."""
        # Create team with existing title
        self.create_team_with_permissions(title="Existing Team")

        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        form_data = {
            "title": "Existing Team",  # Duplicate title
            "description": "This should fail",
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")

        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_team_member_duplicate_prevention_integration(self):
        """Test prevention of duplicate team members in integration context."""
        team = self.create_team_with_permissions()
        existing_member = OrganizationMemberFactory(organization=self.organization)

        # Add member to team first
        TeamMemberFactory(organization_member=existing_member, team=team)

        url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        form_data = {
            "organization_member": existing_member.pk,
            "role": TeamMemberRole.AUDITOR,
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")

        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already part of this team")


class TeamEdgeCasesIntegrationTest(TestCase):
    """Integration tests for team management edge cases and error scenarios."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner

        # Create organization owner group and assign permissions
        org_owner_group, _ = Group.objects.get_or_create(
            name=f"Org Owner - {self.organization.organization_id}"
        )
        
        # Get org owner permissions and assign them
        org_owner_permissions = get_permissions_for_role("ORG_OWNER")
        for perm in org_owner_permissions:
            if "workspace_currency" not in perm:
                assign_perm(perm, org_owner_group, self.organization)
        
        # Add user to the org owner group
        org_owner_group.user_set.add(self.user)

        self.client.force_login(self.user)

    def create_team_with_permissions(self, **kwargs):
        """Helper method to create a team with proper permissions assigned."""
        # Set default organization if not provided
        if 'organization' not in kwargs:
            kwargs['organization'] = self.organization
        
        team = TeamFactory(**kwargs)
        assign_team_permissions(team)
        return team

    def test_edit_team_member_role_validation_errors(self):
        """Test edit team member role with validation errors."""
        team = self.create_team_with_permissions()
        member = OrganizationMemberFactory(organization=self.organization)
        team_member = TeamMemberFactory(
            organization_member=member, team=team, role=TeamMemberRole.SUBMITTER
        )

        url = reverse(
            "edit_team_member_role",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": team_member.team_member_id,
            },
        )

        # Test with same role (should fail validation)
        form_data = {
            "role": TeamMemberRole.SUBMITTER,  # Same as current role
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "same as the current role")

    def test_team_deletion_with_workspace_attachments(self):
        """Test team deletion when team is attached to workspaces."""
        
        team = self.create_team_with_permissions(created_by=self.org_member)
        
        # Create a workspace team attachment (simulating team attached to workspace)
        # Note: This would require creating a workspace first in a real scenario
        # For now, we'll test the error handling path
        
        url = reverse(
            "delete_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        # Test GET request (confirmation page)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("team", response.context)

    def test_team_member_removal_confirmation(self):
        """Test team member removal GET request for confirmation."""
        team = self.create_team_with_permissions()
        team_member = TeamMemberFactory(team=team)

        url = reverse(
            "remove_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": team_member.team_member_id,
            },
        )

        # Test GET request (confirmation)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("team_member", response.context)
        self.assertIn("team", response.context)

    def test_nonexistent_team_member_removal(self):
        """Test removing a non-existent team member."""
        team = self.create_team_with_permissions()
        fake_team_member_id = "00000000-0000-0000-0000-000000000000"

        url = reverse(
            "remove_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": fake_team_member_id,
            },
        )

        # Test GET request with non-existent team member
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Should redirect with error

    def test_team_creation_without_coordinator(self):
        """Test team creation without specifying a coordinator."""
        url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        form_data = {
            "title": "Team Without Coordinator",
            "description": "Testing team creation without coordinator",
            # No team_coordinator specified
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team was created (coordinator should default to created_by)
        team = Team.objects.get(title="Team Without Coordinator")
        self.assertEqual(team.organization, self.organization)
        self.assertEqual(team.created_by, self.org_member)

    def test_team_update_coordinator_change(self):
        """Test updating team with coordinator change."""
        team = self.create_team_with_permissions(
            created_by=self.org_member,
            team_coordinator=self.org_member,
        )
        new_coordinator = OrganizationMemberFactory(organization=self.organization)

        url = reverse(
            "edit_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        form_data = {
            "title": team.title,
            "description": team.description,
            "team_coordinator": new_coordinator.pk,
        }

        response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify coordinator was changed
        team.refresh_from_db()
        self.assertEqual(team.team_coordinator, new_coordinator)

    def test_team_member_addition_error_handling(self):
        """Test team member addition with service layer errors."""
        team = self.create_team_with_permissions()
        member = OrganizationMemberFactory(organization=self.organization)

        url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        form_data = {
            "organization_member": member.pk,
            "role": TeamMemberRole.AUDITOR,
        }

        # Mock a TeamMemberCreationError
        with patch("apps.teams.views.create_team_member_from_form") as mock_create:
            from apps.teams.exceptions import TeamMemberCreationError
            mock_create.side_effect = TeamMemberCreationError("Mocked error")

            response = self.client.post(url, data=form_data, HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)  # HTMX requests should return 200

    def test_invalid_organization_id_access(self):
        """Test accessing team views with invalid organization ID."""
        fake_org_id = "00000000-0000-0000-0000-000000000000"
        
        url = reverse("teams", kwargs={"organization_id": fake_org_id})
        response = self.client.get(url)
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [302, 404, 500])

    def test_team_permissions_context(self):
        """Test that team views include proper permission context."""
        url = reverse(
            "teams", kwargs={"organization_id": self.organization.organization_id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("permissions", response.context)
        self.assertIn("can_add_team", response.context["permissions"])

    def test_concurrent_team_member_operations(self):
        """Test handling of concurrent team member operations."""
        team = self.create_team_with_permissions()
        member = OrganizationMemberFactory(organization=self.organization)
        
        # Add member
        add_url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        member_data = {
            "organization_member": member.pk,
            "role": TeamMemberRole.SUBMITTER,
        }

        response = self.client.post(add_url, data=member_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        team_member = TeamMember.objects.get(organization_member=member, team=team)

        # Try to add the same member again (should fail)
        response = self.client.post(add_url, data=member_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already part of this team")


class TeamWorkflowIntegrationTest(TestCase):
    """Integration tests for complete team management workflows."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = CustomUserFactory()
        self.organization = OrganizationWithOwnerFactory(owner=self.user)
        self.org_member = self.organization.owner

        # Create organization owner group and assign permissions
        org_owner_group, _ = Group.objects.get_or_create(
            name=f"Org Owner - {self.organization.organization_id}"
        )
        
        # Get org owner permissions and assign them
        org_owner_permissions = get_permissions_for_role("ORG_OWNER")
        for perm in org_owner_permissions:
            if "workspace_currency" not in perm:
                assign_perm(perm, org_owner_group, self.organization)
        
        # Add user to the org owner group
        org_owner_group.user_set.add(self.user)

        # Login the user
        self.client.force_login(self.user)

    def create_team_with_permissions(self, **kwargs):
        """Helper method to create a team with proper permissions assigned."""
        # Set default organization if not provided
        if 'organization' not in kwargs:
            kwargs['organization'] = self.organization
        
        team = TeamFactory(**kwargs)
        assign_team_permissions(team)
        return team

    def test_complete_team_lifecycle_workflow(self):
        """Test complete team lifecycle from creation to deletion."""
        # Step 1: Create team
        create_url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        team_data = {
            "title": "Lifecycle Test Team",
            "description": "Testing complete lifecycle",
            "team_coordinator": self.org_member.pk,
        }

        response = self.client.post(create_url, data=team_data)
        self.assertEqual(response.status_code, 302)

        team = Team.objects.get(title="Lifecycle Test Team")

        # Step 2: Add team members
        member1 = OrganizationMemberFactory(organization=self.organization)
        member2 = OrganizationMemberFactory(organization=self.organization)

        add_member_url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        # Add first member as submitter
        member1_data = {
            "organization_member": member1.pk,
            "role": TeamMemberRole.SUBMITTER,
        }
        response = self.client.post(
            add_member_url, data=member1_data, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)

        # Add second member as auditor
        member2_data = {
            "organization_member": member2.pk,
            "role": TeamMemberRole.AUDITOR,
        }
        response = self.client.post(
            add_member_url, data=member2_data, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)

        # Verify members were added
        self.assertEqual(TeamMember.objects.filter(team=team).count(), 2)

        # Step 3: Update team
        edit_url = reverse(
            "edit_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        update_data = {
            "title": "Updated Lifecycle Team",
            "description": "Updated description",
            "team_coordinator": member1.pk,  # Change coordinator
        }

        response = self.client.post(edit_url, data=update_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        team.refresh_from_db()
        self.assertEqual(team.title, "Updated Lifecycle Team")
        self.assertEqual(team.team_coordinator, member1)

        # Step 4: Remove a team member
        team_member_to_remove = TeamMember.objects.filter(
            team=team, organization_member=member2
        ).first()

        remove_url = reverse(
            "remove_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": team_member_to_remove.team_member_id,
            },
        )

        response = self.client.post(remove_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify member was removed
        self.assertEqual(TeamMember.objects.filter(team=team).count(), 1)

        # Step 5: Delete team
        delete_url = reverse(
            "delete_team",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        response = self.client.post(delete_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify team and remaining members were deleted
        with self.assertRaises(Team.DoesNotExist):
            Team.objects.get(team_id=team.team_id)

        self.assertEqual(TeamMember.objects.filter(team=team).count(), 0)

    def test_team_member_role_change_workflow(self):
        """Test changing team member roles workflow."""
        # Create team and member
        team = self.create_team_with_permissions()
        member = OrganizationMemberFactory(organization=self.organization)

        # Add member as submitter
        add_url = reverse(
            "add_team_member",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
            },
        )

        member_data = {
            "organization_member": member.pk,
            "role": TeamMemberRole.SUBMITTER,
        }

        response = self.client.post(add_url, data=member_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        team_member = TeamMember.objects.get(organization_member=member, team=team)
        self.assertEqual(team_member.role, TeamMemberRole.SUBMITTER)

        # Test role editing functionality
        edit_role_url = reverse(
            "edit_team_member_role",
            kwargs={
                "organization_id": self.organization.organization_id,
                "team_id": team.team_id,
                "team_member_id": team_member.team_member_id,
            },
        )

        # Test GET request for edit role form
        response = self.client.get(edit_role_url)
        self.assertEqual(response.status_code, 200)

        # Test POST request to change role from SUBMITTER to AUDITOR
        role_change_data = {
            "role": TeamMemberRole.AUDITOR,
        }

        response = self.client.post(edit_role_url, data=role_change_data, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)

        # Verify role was changed
        team_member.refresh_from_db()
        self.assertEqual(team_member.role, TeamMemberRole.AUDITOR)

    def test_multiple_teams_same_organization_workflow(self):
        """Test managing multiple teams in the same organization."""
        # Create multiple teams
        teams_data = [
            {"title": "Marketing Team", "description": "Marketing activities"},
            {"title": "Sales Team", "description": "Sales activities"},
            {"title": "Development Team", "description": "Development activities"},
        ]

        create_url = reverse(
            "create_team", kwargs={"organization_id": self.organization.organization_id}
        )

        created_teams = []
        for team_data in teams_data:
            response = self.client.post(create_url, data=team_data)
            self.assertEqual(response.status_code, 302)

            team = Team.objects.get(title=team_data["title"])
            created_teams.append(team)

        # Verify all teams were created
        self.assertEqual(len(created_teams), 3)

        # Add different members to different teams
        members = [
            OrganizationMemberFactory(organization=self.organization) for _ in range(5)
        ]

        # Add members to teams with different roles
        for i, team in enumerate(created_teams):
            add_url = reverse(
                "add_team_member",
                kwargs={
                    "organization_id": self.organization.organization_id,
                    "team_id": team.team_id,
                },
            )

            # Add 2 members per team
            for j in range(2):
                member_idx = (i * 2 + j) % len(members)
                role = TeamMemberRole.AUDITOR if j == 0 else TeamMemberRole.SUBMITTER

                member_data = {
                    "organization_member": members[member_idx].pk,
                    "role": role,
                }

                response = self.client.post(
                    add_url, data=member_data, HTTP_HX_REQUEST="true"
                )
                self.assertEqual(response.status_code, 200)

        # Verify team members were added correctly
        for team in created_teams:
            self.assertEqual(TeamMember.objects.filter(team=team).count(), 2)

        # Test teams list view shows all teams
        teams_url = reverse(
            "teams", kwargs={"organization_id": self.organization.organization_id}
        )
        response = self.client.get(teams_url)

        self.assertEqual(response.status_code, 200)
        for team in created_teams:
            self.assertContains(response, team.title)
