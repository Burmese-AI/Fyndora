from django.test import TestCase
from apps.entries.constants import (
    CONTEXT_OBJECT_NAME,
    DETAIL_CONTEXT_OBJECT_NAME,
    EntryType,
    EntryStatus,
)


class TestEntryConstants(TestCase):
    """Test cases for entry constants."""

    def test_context_object_names(self):
        """Test that context object names are correctly defined."""
        assert CONTEXT_OBJECT_NAME == "entries"
        assert DETAIL_CONTEXT_OBJECT_NAME == "entry"


class TestEntryType(TestCase):
    """Test cases for EntryType choices."""

    def test_entry_type_choices_exist(self):
        """Test that all expected entry type choices exist."""
        expected_choices = [
            ("income", "Income"),
            ("disbursement", "Disbursement"),
            ("remittance", "Remittance"),
            ("workspace_exp", "Workspace Expense"),
            ("org_exp", "Organization Expense"),
        ]
        
        assert len(EntryType.choices) == len(expected_choices)
        
        for choice in expected_choices:
            assert choice in EntryType.choices

    def test_entry_type_values(self):
        """Test that entry type values are correctly defined."""
        assert EntryType.INCOME == "income"
        assert EntryType.DISBURSEMENT == "disbursement"
        assert EntryType.REMITTANCE == "remittance"
        assert EntryType.WORKSPACE_EXP == "workspace_exp"
        assert EntryType.ORG_EXP == "org_exp"

    def test_entry_type_labels(self):
        """Test that entry type labels are correctly defined."""
        assert EntryType.INCOME.label == "Income"
        assert EntryType.DISBURSEMENT.label == "Disbursement"
        assert EntryType.REMITTANCE.label == "Remittance"
        assert EntryType.WORKSPACE_EXP.label == "Workspace Expense"
        assert EntryType.ORG_EXP.label == "Organization Expense"

    def test_entry_type_names(self):
        """Test that entry type names are correctly defined."""
        assert EntryType.INCOME.name == "INCOME"
        assert EntryType.DISBURSEMENT.name == "DISBURSEMENT"
        assert EntryType.REMITTANCE.name == "REMITTANCE"
        assert EntryType.WORKSPACE_EXP.name == "WORKSPACE_EXP"
        assert EntryType.ORG_EXP.name == "ORG_EXP"


class TestEntryStatus(TestCase):
    """Test cases for EntryStatus choices."""

    def test_entry_status_choices_exist(self):
        """Test that all expected entry status choices exist."""
        expected_choices = [
            ("pending", "Pending"),
            ("reviewed", "Reviewed"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ]
        
        assert len(EntryStatus.choices) == len(expected_choices)
        
        for choice in expected_choices:
            assert choice in EntryStatus.choices

    def test_entry_status_values(self):
        """Test that entry status values are correctly defined."""
        assert EntryStatus.PENDING == "pending"
        assert EntryStatus.REVIEWED == "reviewed"
        assert EntryStatus.APPROVED == "approved"
        assert EntryStatus.REJECTED == "rejected"

    def test_entry_status_labels(self):
        """Test that entry status labels are correctly defined."""
        assert EntryStatus.PENDING.label == "Pending"
        assert EntryStatus.REVIEWED.label == "Reviewed"
        assert EntryStatus.APPROVED.label == "Approved"
        assert EntryStatus.REJECTED.label == "Rejected"

    def test_entry_status_names(self):
        """Test that entry status names are correctly defined."""
        assert EntryStatus.PENDING.name == "PENDING"
        assert EntryStatus.REVIEWED.name == "REVIEWED"
        assert EntryStatus.APPROVED.name == "APPROVED"
        assert EntryStatus.REJECTED.name == "REJECTED"


class TestEntryConstantsIntegration(TestCase):
    """Integration tests for entry constants."""

    def test_entry_type_choices_are_unique(self):
        """Test that entry type choices have unique values."""
        values = [choice[0] for choice in EntryType.choices]
        assert len(values) == len(set(values)), "Entry type values should be unique"

    def test_entry_status_choices_are_unique(self):
        """Test that entry status choices have unique values."""
        values = [choice[0] for choice in EntryStatus.choices]
        assert len(values) == len(set(values)), "Entry status values should be unique"

    def test_choices_are_text_choices(self):
        """Test that both choice classes inherit from TextChoices."""
        from django.db import models
        assert issubclass(EntryType, models.TextChoices)
        assert issubclass(EntryStatus, models.TextChoices)
