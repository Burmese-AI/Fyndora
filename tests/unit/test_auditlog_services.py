"""
Unit tests for the auditlog app services.

Following the test plan: AuditLog App (apps.auditlog)
- Service function tests
- Business logic validation
"""

from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from apps.auditlog.services import audit_create
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
    WorkspaceFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestAuditCreateService(TestCase):
    """Test the audit_create service function."""

    @pytest.mark.django_db
    def test_audit_create_with_user(self):
        """Test creating audit log with user."""
        user = CustomUserFactory()
        entry = EntryFactory()
        metadata = {"key": "value", "amount": 1000}

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata=metadata,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsInstance(audit, AuditTrail)
        self.assertEqual(audit.user, user)
        self.assertEqual(audit.action_type, AuditActionType.ENTRY_CREATED)
        self.assertEqual(audit.target_entity, entry)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertEqual(audit.metadata, metadata)
        self.assertIsNotNone(audit.timestamp)
        self.assertIsNotNone(audit.audit_id)

    @pytest.mark.django_db
    def test_audit_create_without_user(self):
        """Test creating audit log without user (system action)."""
        entry = EntryFactory()
        metadata = {"system_action": "automated_cleanup"}

        audit = audit_create(
            user=None,
            action_type=AuditActionType.ENTRY_STATUS_CHANGED,
            target_entity=entry,
            metadata=metadata,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.user)
        self.assertEqual(audit.action_type, AuditActionType.ENTRY_STATUS_CHANGED)
        self.assertEqual(audit.target_entity, entry)
        self.assertEqual(
            audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertEqual(audit.metadata, metadata)

    @pytest.mark.django_db
    def test_audit_create_without_metadata(self):
        """Test creating audit log without metadata."""
        user = CustomUserFactory()
        entry = EntryFactory()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, user)
        self.assertIsNone(audit.metadata)

    @pytest.mark.django_db
    def test_audit_create_with_none_metadata(self):
        """Test creating audit log with explicitly None metadata."""
        user = CustomUserFactory()
        entry = EntryFactory()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata=None,
        )

        # Verify audit was created correctly
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.metadata)

    @pytest.mark.django_db
    def test_audit_create_with_complex_metadata(self):
        """Test creating audit log with complex metadata structure."""
        user = CustomUserFactory()
        entry = EntryFactory()
        complex_metadata = {
            "user_details": {"username": user.username, "role": "admin"},
            "changes": {"old_value": "draft", "new_value": "submitted"},
            "context": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_STATUS_CHANGED,
            target_entity=entry,
            metadata=complex_metadata,
        )

        # Verify complex metadata was stored correctly
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata, complex_metadata)
        self.assertEqual(audit.metadata["user_details"]["username"], user.username)
        self.assertEqual(audit.metadata["changes"]["old_value"], "draft")

    @pytest.mark.django_db
    def test_audit_create_persists_to_database(self):
        """Test that audit_create actually persists to database."""
        user = CustomUserFactory()
        entry = EntryFactory()

        # Count existing audits
        initial_count = AuditTrail.objects.count()

        audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
        )

        # Verify it was saved to database
        self.assertEqual(AuditTrail.objects.count(), initial_count + 1)

        # Verify we can retrieve it
        retrieved_audit = AuditTrail.objects.get(audit_id=audit.audit_id)
        self.assertEqual(retrieved_audit.user, user)
        self.assertEqual(retrieved_audit.target_entity, entry)

    @pytest.mark.django_db
    def test_audit_create_with_all_action_types(self):
        """Test audit_create with all available action types."""
        user = CustomUserFactory()
        entry = EntryFactory()

        action_types = [choice[0] for choice in AuditActionType.choices]

        for action_type in action_types:
            audit = audit_create(
                user=user,
                action_type=action_type,
                target_entity=entry,
                metadata={"test": f"test_{action_type}"},
            )

            self.assertEqual(audit.action_type, action_type)
            self.assertIsNotNone(audit.audit_id)

    @pytest.mark.django_db
    def test_audit_create_with_different_entity_types(self):
        """Test audit_create with different model types as target entities."""
        user = CustomUserFactory()

        # Create different model instances
        entry = EntryFactory()
        workspace = WorkspaceFactory()

        # Test with entry model
        entry_audit = audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_CREATED,
            target_entity=entry,
            metadata={"test": "test_entry"},
        )

        # Test with workspace model
        workspace_audit = audit_create(
            user=user,
            action_type=AuditActionType.WORKSPACE_CREATED,
            target_entity=workspace,
            metadata={"test": "test_workspace"},
        )

        # Test with user model
        user_audit = audit_create(
            user=user,
            action_type=AuditActionType.USER_CREATED,
            target_entity=user,
            metadata={"test": "test_user"},
        )

        # Verify different entity types are handled correctly
        self.assertEqual(
            entry_audit.target_entity_type, ContentType.objects.get_for_model(entry)
        )
        self.assertEqual(
            workspace_audit.target_entity_type,
            ContentType.objects.get_for_model(workspace),
        )
        self.assertEqual(
            user_audit.target_entity_type, ContentType.objects.get_for_model(user)
        )
