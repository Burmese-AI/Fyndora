"""
Unit tests for Team forms.
"""

from django.test import TestCase

from apps.teams.constants import TeamMemberRole
from apps.teams.forms import TeamForm, TeamMemberForm, EditTeamMemberRoleForm
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory


class TeamFormTest(TestCase):
    """Test cases for TeamForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.coordinator = OrganizationMemberFactory(organization=self.organization)
        self.other_member = OrganizationMemberFactory(organization=self.organization)

    def test_team_form_valid_data(self):
        """Test team form with valid data."""
        form_data = {
            "title": "Marketing Team",
            "description": "Team responsible for marketing activities",
            "team_coordinator": self.coordinator.pk,
        }

        form = TeamForm(data=form_data, organization=self.organization)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["title"], "Marketing Team")
        self.assertEqual(form.cleaned_data["team_coordinator"], self.coordinator)

    def test_team_form_valid_without_coordinator(self):
        """Test team form without coordinator (optional field)."""
        form_data = {
            "title": "Sales Team",
            "description": "Team responsible for sales",
        }

        form = TeamForm(data=form_data, organization=self.organization)

        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["team_coordinator"])

    def test_team_form_valid_without_description(self):
        """Test team form without description (optional field)."""
        form_data = {
            "title": "Development Team",
            "team_coordinator": self.coordinator.pk,
        }

        form = TeamForm(data=form_data, organization=self.organization)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["description"], "")

    def test_team_form_missing_title(self):
        """Test team form with missing title."""
        form_data = {
            "description": "Team without title",
            "team_coordinator": self.coordinator.pk,
        }

        form = TeamForm(data=form_data, organization=self.organization)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_team_form_duplicate_title_same_organization(self):
        """Test team form with duplicate title in same organization."""
        # Create existing team
        TeamFactory(organization=self.organization, title="Existing Team")

        form_data = {
            "title": "Existing Team",
            "description": "Duplicate team",
        }

        form = TeamForm(data=form_data, organization=self.organization)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("Team with this title already exists", str(form.errors["title"]))

    def test_team_form_duplicate_title_different_organization(self):
        """Test team form with duplicate title in different organization."""
        other_organization = OrganizationFactory()
        TeamFactory(organization=other_organization, title="Same Title")

        form_data = {
            "title": "Same Title",
            "description": "Same title but different org",
        }

        form = TeamForm(data=form_data, organization=self.organization)

        self.assertTrue(form.is_valid())

    def test_team_form_edit_same_title(self):
        """Test editing team with same title (should be valid)."""
        existing_team = TeamFactory(
            organization=self.organization, title="Original Title"
        )

        form_data = {
            "title": "Original Title",
            "description": "Updated description",
        }

        form = TeamForm(
            data=form_data, instance=existing_team, organization=self.organization
        )

        self.assertTrue(form.is_valid())

    def test_team_form_edit_duplicate_title(self):
        """Test editing team with title that exists in another team."""
        existing_team1 = TeamFactory(organization=self.organization, title="Team One")
        TeamFactory(organization=self.organization, title="Team Two")

        form_data = {
            "title": "Team Two",  # Trying to change to existing title
            "description": "Updated description",
        }

        form = TeamForm(
            data=form_data, instance=existing_team1, organization=self.organization
        )

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_team_form_coordinator_queryset(self):
        """Test that coordinator queryset is filtered by organization."""
        other_organization = OrganizationFactory()
        other_coordinator = OrganizationMemberFactory(organization=other_organization)

        form = TeamForm(organization=self.organization)

        # Should include members from the organization
        self.assertIn(self.coordinator, form.fields["team_coordinator"].queryset)
        self.assertIn(self.other_member, form.fields["team_coordinator"].queryset)

        # Should not include members from other organizations
        self.assertNotIn(other_coordinator, form.fields["team_coordinator"].queryset)

    def test_team_form_no_organization_error(self):
        """Test team form validation without organization."""
        form_data = {
            "title": "Test Team",
            "description": "Test description",
        }

        # Create form without organization
        form = TeamForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("Organization is required", str(form.errors["title"]))


class TeamMemberFormTest(TestCase):
    """Test cases for TeamMemberForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team = TeamFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.other_member = OrganizationMemberFactory(organization=self.organization)

    def test_team_member_form_valid_data(self):
        """Test team member form with valid data."""
        form_data = {
            "organization_member": self.org_member.pk,
            "role": TeamMemberRole.SUBMITTER,
        }

        form = TeamMemberForm(
            data=form_data, organization=self.organization, team=self.team
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["organization_member"], self.org_member)
        self.assertEqual(form.cleaned_data["role"], TeamMemberRole.SUBMITTER)

    def test_team_member_form_auditor_role(self):
        """Test team member form with auditor role."""
        form_data = {
            "organization_member": self.org_member.pk,
            "role": TeamMemberRole.AUDITOR,
        }

        form = TeamMemberForm(
            data=form_data, organization=self.organization, team=self.team
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["role"], TeamMemberRole.AUDITOR)

    def test_team_member_form_missing_member(self):
        """Test team member form with missing organization member."""
        form_data = {
            "role": TeamMemberRole.SUBMITTER,
        }

        form = TeamMemberForm(
            data=form_data, organization=self.organization, team=self.team
        )

        self.assertFalse(form.is_valid())
        self.assertIn("organization_member", form.errors)

    def test_team_member_form_missing_role(self):
        """Test team member form with missing role."""
        form_data = {
            "organization_member": self.org_member.pk,
        }

        form = TeamMemberForm(
            data=form_data, organization=self.organization, team=self.team
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_team_member_form_duplicate_member(self):
        """Test team member form with member already in team."""
        # Add member to team first
        TeamMemberFactory(organization_member=self.org_member, team=self.team)

        form_data = {
            "organization_member": self.org_member.pk,
            "role": TeamMemberRole.AUDITOR,
        }

        form = TeamMemberForm(
            data=form_data, organization=self.organization, team=self.team
        )

        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("already part of this team", str(form.errors["__all__"]))

    def test_team_member_form_member_queryset(self):
        """Test that organization member queryset is filtered by organization."""
        other_organization = OrganizationFactory()
        other_member = OrganizationMemberFactory(organization=other_organization)

        form = TeamMemberForm(organization=self.organization, team=self.team)

        # Should include members from the organization
        self.assertIn(self.org_member, form.fields["organization_member"].queryset)
        self.assertIn(self.other_member, form.fields["organization_member"].queryset)

        # Should not include members from other organizations
        self.assertNotIn(other_member, form.fields["organization_member"].queryset)

    def test_team_member_form_role_choices(self):
        """Test that role field has correct choices."""
        form = TeamMemberForm(organization=self.organization, team=self.team)

        role_choices = form.fields["role"].choices
        self.assertIn((TeamMemberRole.SUBMITTER, "Submitter"), role_choices)
        self.assertIn((TeamMemberRole.AUDITOR, "Auditor"), role_choices)


class EditTeamMemberRoleFormTest(TestCase):
    """Test cases for EditTeamMemberRoleForm."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            team=self.team, role=TeamMemberRole.SUBMITTER
        )

    def test_edit_role_form_valid_data(self):
        """Test edit role form with valid data."""
        form_data = {
            "role": TeamMemberRole.AUDITOR,
        }

        form = EditTeamMemberRoleForm(data=form_data, instance=self.team_member)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["role"], TeamMemberRole.AUDITOR)

    def test_edit_role_form_same_role(self):
        """Test edit role form with same role (should be invalid)."""
        form_data = {
            "role": TeamMemberRole.SUBMITTER,  # Same as current role
        }

        form = EditTeamMemberRoleForm(data=form_data, instance=self.team_member)

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)
        self.assertIn(
            "cannot be the same as the current role", str(form.errors["role"])
        )

    def test_edit_role_form_missing_role(self):
        """Test edit role form with missing role."""
        form_data = {}

        form = EditTeamMemberRoleForm(data=form_data, instance=self.team_member)

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_edit_role_form_role_choices(self):
        """Test that role field has correct choices."""
        form = EditTeamMemberRoleForm(instance=self.team_member)

        role_choices = form.fields["role"].choices
        self.assertIn((TeamMemberRole.SUBMITTER, "Submitter"), role_choices)
        self.assertIn((TeamMemberRole.AUDITOR, "Auditor"), role_choices)

    def test_edit_role_form_auditor_to_submitter(self):
        """Test changing role from auditor to submitter."""
        auditor_member = TeamMemberFactory(team=self.team, role=TeamMemberRole.AUDITOR)

        form_data = {
            "role": TeamMemberRole.SUBMITTER,
        }

        form = EditTeamMemberRoleForm(data=form_data, instance=auditor_member)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["role"], TeamMemberRole.SUBMITTER)
