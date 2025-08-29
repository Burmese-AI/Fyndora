"""
Unit tests for Team constants.
"""

from django.test import TestCase
from apps.teams.constants import TeamMemberRole


class TeamMemberRoleTest(TestCase):
    """Test cases for TeamMemberRole constants."""

    def test_team_member_role_choices_exist(self):
        """Test that all expected team member role choices exist."""
        expected_roles = [
            "team_coordinator",
            "submitter", 
            "auditor"
        ]
        
        for role in expected_roles:
            self.assertTrue(hasattr(TeamMemberRole, role.upper()))

    def test_team_member_role_values(self):
        """Test that team member role values are correct."""
        self.assertEqual(TeamMemberRole.TEAM_COORDINATOR.value, "team_coordinator")
        self.assertEqual(TeamMemberRole.SUBMITTER.value, "submitter")
        self.assertEqual(TeamMemberRole.AUDITOR.value, "auditor")

    def test_team_member_role_labels(self):
        """Test that team member role labels are correct."""
        self.assertEqual(TeamMemberRole.TEAM_COORDINATOR.label, "Team Coordinator")
        self.assertEqual(TeamMemberRole.SUBMITTER.label, "Submitter")
        self.assertEqual(TeamMemberRole.AUDITOR.label, "Auditor")

    def test_team_member_role_choices_structure(self):
        """Test that choices have the correct structure."""
        choices = TeamMemberRole.choices
        
        # Check that choices is a list of tuples
        self.assertIsInstance(choices, list)
        
        # Check that each choice is a tuple with 2 elements
        for choice in choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            
        # Check that first element is the value, second is the label
        for value, label in choices:
            self.assertIsInstance(value, str)
            self.assertIsInstance(label, str)

    def test_team_member_role_names(self):
        """Test that team member role names are correct."""
        self.assertEqual(TeamMemberRole.TEAM_COORDINATOR.name, "TEAM_COORDINATOR")
        self.assertEqual(TeamMemberRole.SUBMITTER.name, "SUBMITTER")
        self.assertEqual(TeamMemberRole.AUDITOR.name, "AUDITOR")

    def test_team_member_role_choices_contains_all_roles(self):
        """Test that choices contains all defined roles."""
        expected_choices = [
            ("team_coordinator", "Team Coordinator"),
            ("submitter", "Submitter"),
            ("auditor", "Auditor")
        ]
        
        for expected_choice in expected_choices:
            self.assertIn(expected_choice, TeamMemberRole.choices)

    def test_team_member_role_choices_length(self):
        """Test that there are exactly 3 role choices."""
        self.assertEqual(len(TeamMemberRole.choices), 3)

    def test_team_member_role_values_are_strings(self):
        """Test that all role values are strings."""
        for role in TeamMemberRole:
            self.assertIsInstance(role.value, str)

    def test_team_member_role_labels_are_strings(self):
        """Test that all role labels are strings."""
        for role in TeamMemberRole:
            self.assertIsInstance(role.label, str)

    def test_team_member_role_names_are_strings(self):
        """Test that all role names are strings."""
        for role in TeamMemberRole:
            self.assertIsInstance(role.name, str)

    def test_team_member_role_immutability(self):
        """Test that role values cannot be modified."""
        with self.assertRaises(AttributeError):
            TeamMemberRole.TEAM_COORDINATOR.value = "new_value"

    def test_team_member_role_enumeration(self):
        """Test that roles can be enumerated."""
        roles = list(TeamMemberRole)
        self.assertEqual(len(roles), 3)
        
        # Check that all expected roles are present
        role_values = [role.value for role in roles]
        expected_values = ["team_coordinator", "submitter", "auditor"]
        
        for expected_value in expected_values:
            self.assertIn(expected_value, role_values)

    def test_team_member_role_choice_validation(self):
        """Test that role choices can be used for validation."""
        # Valid choices should work
        valid_choices = ["team_coordinator", "submitter", "auditor"]
        
        for choice in valid_choices:
            self.assertIn(choice, [role.value for role in TeamMemberRole])
        
        # Invalid choices should not be in choices
        invalid_choices = ["invalid_role", "admin", "user"]
        
        for choice in invalid_choices:
            self.assertNotIn(choice, [role.value for role in TeamMemberRole])

    def test_team_member_role_display_values(self):
        """Test that role display values are human-readable."""
        # Check that labels are human-readable and not just the raw values
        self.assertNotEqual(TeamMemberRole.TEAM_COORDINATOR.label, TeamMemberRole.TEAM_COORDINATOR.value)
        self.assertNotEqual(TeamMemberRole.SUBMITTER.label, TeamMemberRole.SUBMITTER.value)
        self.assertNotEqual(TeamMemberRole.AUDITOR.label, TeamMemberRole.AUDITOR.value)
        
        # Check that labels have proper capitalization
        self.assertTrue(TeamMemberRole.TEAM_COORDINATOR.label[0].isupper())
        self.assertTrue(TeamMemberRole.SUBMITTER.label[0].isupper())
        self.assertTrue(TeamMemberRole.AUDITOR.label[0].isupper())

