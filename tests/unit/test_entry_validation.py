"""
Unit tests for Entry model validation logic.

Tests the custom clean() method validation for role-based business rules.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.teams.constants import TeamMemberRole
from tests.factories import (
    TeamMemberFactory,
    EntryFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryCleanValidation:
    """Test Entry model's clean() method validation."""

    def test_valid_submitter_role_passes_validation(self):
        """Test that entries with SUBMITTER role pass validation."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        entry = EntryFactory.build(submitted_by=submitter)

        # Should not raise ValidationError
        entry.clean()

    def test_invalid_submitter_role_fails_validation(self):
        """Test that entries with non-SUBMITTER role fail validation."""
        non_submitter = TeamMemberFactory(role=TeamMemberRole.AUDITOR)
        entry = EntryFactory.build(submitted_by=non_submitter)

        with pytest.raises(ValidationError) as exc_info:
            entry.clean()

        assert "submitted_by" in exc_info.value.message_dict
        assert "Only users with Submitter role can create entries." in str(
            exc_info.value
        )

    def test_valid_reviewer_roles_pass_validation(self):
        """Test that entries with valid reviewer roles pass validation."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        valid_reviewer_roles = [
            TeamMemberRole.WORKSPACE_ADMIN,
            TeamMemberRole.OPERATIONS_REVIEWER,
            TeamMemberRole.TEAM_COORDINATOR,
        ]

        for role in valid_reviewer_roles:
            reviewer = TeamMemberFactory(role=role)
            entry = EntryFactory.build(submitted_by=submitter, reviewed_by=reviewer)

            # Should not raise ValidationError
            entry.clean()

    def test_invalid_reviewer_role_fails_validation(self):
        """Test that entries with invalid reviewer roles fail validation."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        invalid_reviewer = TeamMemberFactory(role=TeamMemberRole.AUDITOR)

        entry = EntryFactory.build(submitted_by=submitter, reviewed_by=invalid_reviewer)

        with pytest.raises(ValidationError) as exc_info:
            entry.clean()

        assert "reviewed_by" in exc_info.value.message_dict
        assert "Team Coordinator, Operations Reviewer, or Workspace Admin" in str(
            exc_info.value
        )

    def test_none_reviewer_passes_validation(self):
        """Test that entries with None reviewer pass validation."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        entry = EntryFactory.build(submitted_by=submitter, reviewed_by=None)

        # Should not raise ValidationError
        entry.clean()

    def test_reviewer_validation_checked_first(self):
        """Test that reviewer validation is checked first, stopping on first error."""
        non_submitter = TeamMemberFactory(role=TeamMemberRole.AUDITOR)
        invalid_reviewer = TeamMemberFactory(role=TeamMemberRole.AUDITOR)
        
        entry = EntryFactory.build(
            submitted_by=non_submitter, reviewed_by=invalid_reviewer
        )
        
        with pytest.raises(ValidationError) as exc_info:
            entry.clean()
        
        error_dict = exc_info.value.message_dict
        # Only reviewer error is caught since it's checked first
        assert "reviewed_by" in error_dict
        assert "submitted_by" not in error_dict  # This validation is not reached
    
    def test_submitter_validation_when_reviewer_valid(self):
        """Test that submitter validation is checked when reviewer is valid."""
        non_submitter = TeamMemberFactory(role=TeamMemberRole.AUDITOR)
        valid_reviewer = TeamMemberFactory(role=TeamMemberRole.TEAM_COORDINATOR)
        
        entry = EntryFactory.build(
            submitted_by=non_submitter, reviewed_by=valid_reviewer
        )
        
        with pytest.raises(ValidationError) as exc_info:
            entry.clean()
        
        error_dict = exc_info.value.message_dict
        assert "submitted_by" in error_dict
        assert "reviewed_by" not in error_dict

    def test_submitter_and_reviewer_can_be_different_people(self):
        """Test that submitter and reviewer must be different team members."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        coordinator = TeamMemberFactory(role=TeamMemberRole.TEAM_COORDINATOR)

        entry = EntryFactory.build(submitted_by=submitter, reviewed_by=coordinator)

        # Should not raise ValidationError
        entry.clean()
        assert entry.submitted_by != entry.reviewed_by
