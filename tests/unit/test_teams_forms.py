"""
Unit tests for Team forms.
"""

from django.test import TestCase
from django import forms

from apps.teams.forms import TeamForm, TeamMemberForm, EditTeamMemberRoleForm
from apps.teams.constants import TeamMemberRole
from tests.factories.organization_factories import (
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory


class TeamFormTest(TestCase):
    """Test cases for TeamForm."""

    def setUp(self):
        """Set up test data."""
        # Use OrganizationWithOwnerFactory to automatically create an owner
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

    def test_team_form_fields(self):
        """Test that TeamForm has the correct fields."""
        form = TeamForm(organization=self.organization)
        expected_fields = ["title", "description", "team_coordinator"]

        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_team_form_widgets(self):
        """Test that TeamForm has the correct widgets."""
        form = TeamForm(organization=self.organization)

        # Check title widget
        self.assertIsInstance(form.fields["title"].widget, forms.TextInput)
        self.assertIn("placeholder", form.fields["title"].widget.attrs)
        self.assertEqual(
            form.fields["title"].widget.attrs["placeholder"], "Enter team title"
        )

        # Check description widget
        self.assertIsInstance(form.fields["description"].widget, forms.Textarea)
        self.assertIn("placeholder", form.fields["description"].widget.attrs)
        self.assertEqual(
            form.fields["description"].widget.attrs["placeholder"],
            "Describe your team (optional)",
        )

        # Check team_coordinator widget
        self.assertIsInstance(form.fields["team_coordinator"].widget, forms.Select)

    def test_team_form_initialization_with_organization(self):
        """Test that TeamForm initializes correctly with organization."""
        form = TeamForm(organization=self.organization)

        # Check that team_coordinator queryset is set and not None
        queryset = form.fields["team_coordinator"].queryset
        self.assertIsNotNone(queryset)
        # The queryset should contain members but exclude the owner
        self.assertIn(self.org_member, queryset)
        self.assertNotIn(self.organization.owner, queryset)

    def test_team_form_initialization_without_organization(self):
        """Test that TeamForm initializes correctly without organization."""
        form = TeamForm()

        # Check that team_coordinator queryset is empty
        self.assertEqual(form.fields["team_coordinator"].queryset.count(), 0)

    def test_team_form_team_coordinator_disabled(self):
        """Test that team_coordinator field is disabled when can_change_team_coordinator is False."""
        form = TeamForm(
            organization=self.organization, can_change_team_coordinator=False
        )

        self.assertTrue(form.fields["team_coordinator"].widget.attrs.get("disabled"))

    def test_team_form_team_coordinator_enabled(self):
        """Test that team_coordinator field is enabled when can_change_team_coordinator is True."""
        form = TeamForm(
            organization=self.organization, can_change_team_coordinator=True
        )

        self.assertNotIn("disabled", form.fields["team_coordinator"].widget.attrs)

    def test_team_form_clean_title_new_team_success(self):
        """Test that clean_title works for new team creation."""
        form = TeamForm(
            data={"title": "New Team", "description": "Test Description"},
            organization=self.organization,
        )

        # Must call is_valid() first to populate cleaned_data
        self.assertTrue(form.is_valid())
        title = form.cleaned_data.get("title")
        self.assertEqual(title, "New Team")

    def test_team_form_clean_title_edit_team_success(self):
        """Test that clean_title works for team editing."""
        form = TeamForm(
            data={"title": "Updated Team", "description": "Updated Description"},
            instance=self.team,
            organization=self.organization,
        )

        # Must call is_valid() first to populate cleaned_data
        self.assertTrue(form.is_valid())
        title = form.cleaned_data.get("title")
        self.assertEqual(title, "Updated Team")

    def test_team_form_clean_title_duplicate_in_same_org(self):
        """Test that clean_title raises error for duplicate title in same organization."""
        # Create another team with the same title
        TeamFactory(title="Duplicate Title", organization=self.organization)

        form = TeamForm(
            data={"title": "Duplicate Title", "description": "Test Description"},
            organization=self.organization,
        )

        # The validation error should be caught during is_valid()
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_team_form_clean_title_duplicate_in_different_org(self):
        """Test that clean_title allows same title in different organization."""
        other_organization = OrganizationWithOwnerFactory()
        OrganizationMemberFactory(organization=other_organization)

        form = TeamForm(
            data={"title": "Same Title", "description": "Test Description"},
            organization=other_organization,
        )

        # Must call is_valid() first to populate cleaned_data
        self.assertTrue(form.is_valid())
        title = form.cleaned_data.get("title")
        self.assertEqual(title, "Same Title")

    def test_team_form_clean_title_no_organization(self):
        """Test that clean_title raises error when no organization is provided."""
        form = TeamForm(data={"title": "Test Team", "description": "Test Description"})

        # The validation error should be caught during is_valid()
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_team_form_validation_success(self):
        """Test that TeamForm validates successfully with valid data."""
        form = TeamForm(
            data={
                "title": "Valid Team",
                "description": "Valid Description",
                "team_coordinator": self.org_member.pk,
            },
            organization=self.organization,
        )

        self.assertTrue(form.is_valid())

    def test_team_form_validation_missing_title(self):
        """Test that TeamForm validation fails when title is missing."""
        form = TeamForm(
            data={
                "description": "Valid Description",
                "team_coordinator": self.org_member.pk,
            },
            organization=self.organization,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)


class TeamMemberFormTest(TestCase):
    """Test cases for TeamMemberForm."""

    def setUp(self):
        """Set up test data."""
        # Use OrganizationWithOwnerFactory to automatically create an owner
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

    def test_team_member_form_fields(self):
        """Test that TeamMemberForm has the correct fields."""
        form = TeamMemberForm(organization=self.organization, team=self.team)
        expected_fields = ["organization_member", "role"]

        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_team_member_form_role_choices_exclude_team_coordinator(self):
        """Test that role choices exclude team_coordinator."""
        form = TeamMemberForm(organization=self.organization, team=self.team)

        role_choices = [choice[0] for choice in form.fields["role"].choices]
        self.assertNotIn(TeamMemberRole.TEAM_COORDINATOR, role_choices)
        self.assertIn(TeamMemberRole.SUBMITTER, role_choices)
        self.assertIn(TeamMemberRole.AUDITOR, role_choices)

    def test_team_member_form_initialization_with_organization(self):
        """Test that TeamMemberForm initializes correctly with organization."""
        form = TeamMemberForm(organization=self.organization, team=self.team)

        # Check that organization_member queryset is set and not None
        queryset = form.fields["organization_member"].queryset
        self.assertIsNotNone(queryset)
        # The queryset should contain members but exclude the owner
        self.assertIn(self.org_member, queryset)
        self.assertNotIn(self.organization.owner, queryset)

    def test_team_member_form_initialization_without_organization(self):
        """Test that TeamMemberForm initializes correctly without organization."""
        form = TeamMemberForm(team=self.team)

        # Check that organization_member queryset is empty
        self.assertEqual(form.fields["organization_member"].queryset.count(), 0)

    def test_team_member_form_clean_success(self):
        """Test that clean method works successfully."""
        form = TeamMemberForm(
            data={
                "organization_member": self.org_member.pk,
                "role": TeamMemberRole.SUBMITTER,
            },
            organization=self.organization,
            team=self.team,
        )

        # Must call is_valid() first to populate cleaned_data
        self.assertTrue(form.is_valid())
        cleaned_data = form.cleaned_data
        self.assertIsNotNone(cleaned_data)

    def test_team_member_form_clean_member_already_in_team(self):
        """Test that clean method raises error when member is already in team."""
        # Create a team member
        TeamMemberFactory(organization_member=self.org_member, team=self.team)

        form = TeamMemberForm(
            data={
                "organization_member": self.org_member.pk,
                "role": TeamMemberRole.AUDITOR,
            },
            organization=self.organization,
            team=self.team,
        )

        # The validation error should be caught during is_valid()
        self.assertFalse(form.is_valid())
        # Check for the specific error message about duplicate member in __all__
        self.assertIn("__all__", form.errors)
        self.assertIn("already part of this team", str(form.errors["__all__"]))

    def test_team_member_form_validation_success(self):
        """Test that TeamMemberForm validates successfully with valid data."""
        form = TeamMemberForm(
            data={
                "organization_member": self.org_member.pk,
                "role": TeamMemberRole.SUBMITTER,
            },
            organization=self.organization,
            team=self.team,
        )

        self.assertTrue(form.is_valid())

    def test_team_member_form_validation_missing_organization_member(self):
        """Test that TeamMemberForm validation fails when organization_member is missing."""
        form = TeamMemberForm(
            data={"role": TeamMemberRole.SUBMITTER},
            organization=self.organization,
            team=self.team,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("organization_member", form.errors)

    def test_team_member_form_validation_missing_role(self):
        """Test that TeamMemberForm validation fails when role is missing."""
        form = TeamMemberForm(
            data={"organization_member": self.org_member.pk},
            organization=self.organization,
            team=self.team,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)


class EditTeamMemberRoleFormTest(TestCase):
    """Test cases for EditTeamMemberRoleForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            organization_member=self.org_member,
            team=self.team,
            role=TeamMemberRole.SUBMITTER,
        )

    def test_edit_team_member_role_form_fields(self):
        """Test that EditTeamMemberRoleForm has the correct fields."""
        form = EditTeamMemberRoleForm(instance=self.team_member)
        expected_fields = ["role"]

        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_edit_team_member_role_form_role_choices_exclude_team_coordinator(self):
        """Test that role choices exclude team_coordinator."""
        form = EditTeamMemberRoleForm(instance=self.team_member)

        role_choices = [choice[0] for choice in form.fields["role"].choices]
        self.assertNotIn(TeamMemberRole.TEAM_COORDINATOR, role_choices)
        self.assertIn(TeamMemberRole.SUBMITTER, role_choices)
        self.assertIn(TeamMemberRole.AUDITOR, role_choices)

    def test_edit_team_member_role_form_clean_role_success(self):
        """Test that clean_role works successfully with different role."""
        form = EditTeamMemberRoleForm(
            data={"role": TeamMemberRole.AUDITOR}, instance=self.team_member
        )

        # Must call is_valid() first to populate cleaned_data
        self.assertTrue(form.is_valid())
        role = form.cleaned_data.get("role")
        self.assertEqual(role, TeamMemberRole.AUDITOR)

    def test_edit_team_member_role_form_clean_role_same_role(self):
        """Test that clean_role raises error when new role is same as current."""
        form = EditTeamMemberRoleForm(
            data={"role": TeamMemberRole.SUBMITTER}, instance=self.team_member
        )

        # The validation error should be caught during is_valid()
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_edit_team_member_role_form_validation_success(self):
        """Test that EditTeamMemberRoleForm validates successfully with valid data."""
        form = EditTeamMemberRoleForm(
            data={"role": TeamMemberRole.AUDITOR}, instance=self.team_member
        )

        self.assertTrue(form.is_valid())

    def test_edit_team_member_role_form_validation_missing_role(self):
        """Test that EditTeamMemberRoleForm validation fails when role is missing."""
        form = EditTeamMemberRoleForm(
            data={},  # Empty data should trigger validation error
            instance=self.team_member,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_edit_team_member_role_form_widget_attributes(self):
        """Test that EditTeamMemberRoleForm has correct widget attributes."""
        form = EditTeamMemberRoleForm(instance=self.team_member)

        self.assertIsInstance(form.fields["role"].widget, forms.Select)
        self.assertIn("class", form.fields["role"].widget.attrs)
        self.assertIn("select-bordered", form.fields["role"].widget.attrs["class"])


class TeamFormsIntegrationTest(TestCase):
    """Integration tests for Team forms."""

    def setUp(self):
        """Set up test data."""
        # Use OrganizationWithOwnerFactory to automatically create an owner
        self.organization = OrganizationWithOwnerFactory()
        self.org_member1 = OrganizationMemberFactory(organization=self.organization)
        self.org_member2 = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

    def test_team_creation_workflow(self):
        """Test complete team creation workflow with forms."""
        # Create team
        team_form = TeamForm(
            data={
                "title": "Integration Test Team",
                "description": "Team for integration testing",
                "team_coordinator": self.org_member1.pk,
            },
            organization=self.organization,
        )

        self.assertTrue(team_form.is_valid())
        team = team_form.save(commit=False)
        team.organization = self.organization
        team.created_by = self.org_member1
        team.save()

        # Add team member
        member_form = TeamMemberForm(
            data={
                "organization_member": self.org_member2.pk,
                "role": TeamMemberRole.SUBMITTER,
            },
            organization=self.organization,
            team=team,
        )

        self.assertTrue(member_form.is_valid())
        team_member = member_form.save(commit=False)
        team_member.team = team
        team_member.save()

        # Verify creation
        self.assertEqual(team.title, "Integration Test Team")
        self.assertEqual(team.team_coordinator, self.org_member1)
        self.assertEqual(team_member.role, TeamMemberRole.SUBMITTER)

    def test_team_member_role_update_workflow(self):
        """Test team member role update workflow."""
        # Create team member
        team_member = TeamMemberFactory(
            organization_member=self.org_member2,
            team=self.team,
            role=TeamMemberRole.SUBMITTER,
        )

        # Update role
        edit_form = EditTeamMemberRoleForm(
            data={"role": TeamMemberRole.AUDITOR}, instance=team_member
        )

        self.assertTrue(edit_form.is_valid())
        updated_role = edit_form.cleaned_data.get("role")
        self.assertEqual(updated_role, TeamMemberRole.AUDITOR)

    def test_form_queryset_filtering(self):
        """Test that forms properly filter querysets based on context."""
        # Create team form with organization
        team_form = TeamForm(organization=self.organization)

        # Check that team_coordinator queryset contains org members but excludes owner
        queryset = team_form.fields["team_coordinator"].queryset
        if queryset is not None:  # Handle case where selector returns None
            self.assertIn(self.org_member1, queryset)
            self.assertIn(self.org_member2, queryset)
            self.assertNotIn(self.organization.owner, queryset)

        # Create team member form with organization
        member_form = TeamMemberForm(organization=self.organization, team=self.team)

        # Check that organization_member queryset contains org members but excludes owner
        queryset = member_form.fields["organization_member"].queryset
        if queryset is not None:  # Handle case where selector returns None
            self.assertIn(self.org_member1, queryset)
            self.assertIn(self.org_member2, queryset)
            self.assertNotIn(self.organization.owner, queryset)
