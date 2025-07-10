"""
Unit tests for Entry model validation logic.

Tests the custom clean() method validation for role-based business rules.
"""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from apps.entries.models import Entry
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    OrganizationMemberFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)
from tests.factories.team_factories import TeamFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryCleanValidation:
    """Test Entry model's clean() method validation."""

    def setup_method(self, method):
        """Set up test data."""
        # Create submitter
        self.submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Create workspace and workspace_team
        self.organization = self.submitter.organization_member.organization
        # Coordinator (set on Team)
        self.coordinator = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(
            team_coordinator=self.coordinator, organization=self.organization
        )
        # Reviewer and admin (set on Workspace)
        self.reviewer = OrganizationMemberFactory(organization=self.organization)
        self.admin = OrganizationMemberFactory(organization=self.organization)
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            operation_reviewer=self.reviewer,
            workspace_admin=self.admin,
        )
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )
        # Create non-submitter for invalid tests
        self.non_submitter = TeamMemberFactory(role=TeamMemberRole.AUDITOR)

    def test_valid_submitter_role_passes_validation(self):
        """Test that entries with SUBMITTER role pass validation."""
        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(self.submitter),
            submitter_object_id=self.submitter.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Should not raise ValidationError
        entry.clean()

    def test_invalid_submitter_role_fails_validation(self):
        """Test that entries with non-SUBMITTER role fail validation."""
        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(
                self.non_submitter
            ),
            submitter_object_id=self.non_submitter.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.clean()

        assert "auditors are not allowed to submit entries" in str(exc_info.value).lower()

    def test_valid_reviewer_roles_pass_validation(self):
        """Test that entries with valid reviewer roles pass validation."""
        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(self.submitter),
            submitter_object_id=self.submitter.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            reviewed_by=self.coordinator,
            status="approved",
            review_notes="Approved entry",
        )

        # Should not raise ValidationError
        entry.clean()

    def test_invalid_reviewer_role_fails_validation(self):
        """Test that entries with invalid reviewer roles fail validation."""
        invalid_reviewer = TeamMemberFactory(role=TeamMemberRole.AUDITOR)

        # Create an organization member from the team member for the reviewer
        invalid_org_member = invalid_reviewer.organization_member

        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(self.submitter),
            submitter_object_id=self.submitter.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            reviewed_by=invalid_org_member,
            status="approved",
            review_notes="Approved entry",
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.clean()

        assert "Reviewer must belong to the same organization as the entry." in str(
            exc_info.value
        )

    def test_none_reviewer_passes_validation(self):
        """Test that entries with None reviewer pass validation."""
        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(self.submitter),
            submitter_object_id=self.submitter.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            reviewed_by=None,
        )

        # Should not raise ValidationError
        entry.clean()

    def test_reviewer_validation_checked_first(self):
        """Test that validation order in the model's clean method."""
        # Create an entry with both submitter and workspace_team issues
        # The submitter belongs to a different team than the workspace_team
        different_team = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(different_team),
            submitter_object_id=different_team.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,  # This workspace_team is linked to self.submitter's team
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.clean()

        # The error should be about the team mismatch
        assert "Submitter must belong to the team linked to this Workspace Team" in str(
            exc_info.value
        )

    def test_submitter_validation_when_reviewer_valid(self):
        """Test that submitter validation works with valid reviewer."""
        # Create an entry with valid reviewer but invalid submitter (wrong team)
        different_team = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(different_team),
            submitter_object_id=different_team.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            reviewed_by=self.coordinator,  # Valid reviewer
            status="approved",
            review_notes="Approved entry",
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.clean()

        # Even with a valid reviewer, the submitter validation should still fail
        assert "Submitter must belong to the team linked to this Workspace Team" in str(
            exc_info.value
        )

    def test_submitter_and_reviewer_can_be_different_people(self):
        """Test that submitter and reviewer must be different team members."""
        entry = Entry(
            entry_type="income",
            amount=100.00,
            description="Test entry",
            submitter_content_type=ContentType.objects.get_for_model(self.submitter),
            submitter_object_id=self.submitter.pk,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            reviewed_by=self.coordinator,
            status="approved",
            review_notes="Approved entry",
        )

        # Should not raise ValidationError
        entry.clean()
        assert entry.submitter != entry.reviewed_by
