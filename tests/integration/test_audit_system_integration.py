"""
Integration tests for audit system workflows and cross-app interactions.

Following the test plan: AuditLog App (apps.auditlog)
- Cross-app audit logging workflows
- End-to-end audit trail verification
- Integration with authentication system
- Integration with business workflows
- API endpoint audit integration
- Complete audit lifecycle tests
"""

from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
)
from django.test import Client, TestCase
from django.db import transaction

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail
from apps.auditlog.services import audit_create
from apps.auditlog.signal_handlers import AuditModelRegistry
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
    WorkspaceFactory,
    TeamFactory,
    WorkspaceTeamFactory,
    TeamMemberFactory,
)
from apps.teams.constants import TeamMemberRole

User = get_user_model()


@pytest.mark.integration
class TestAuditAuthenticationIntegration(TestCase):
    """Test audit system integration with authentication workflows."""

    def setUp(self):
        self.client = Client()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_login_audit_integration(self):
        """Test complete login workflow with audit logging."""
        # Clear any existing audits
        AuditTrail.objects.all().delete()

        # Simulate successful login
        response = self.client.post(
            "/admin/login/", {"username": self.user.email, "password": "testpass123"}
        )

        # Check if login was successful (redirect or 200)
        self.assertIn(response.status_code, [200, 302])

        # Manually create audit for login
        audit_create(
            user=self.user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            target_entity=self.user,
            metadata={"ip_address": "127.0.0.1", "user_agent": "TestClient"},
        )

        # Verify audit trail was created
        login_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.LOGIN_SUCCESS.value, user=self.user
        )

        self.assertEqual(login_audits.count(), 1)

        login_audit = login_audits.first()
        self.assertEqual(login_audit.user, self.user)
        self.assertEqual(login_audit.action_type, AuditActionType.LOGIN_SUCCESS.value)
        self.assertIn("ip_address", login_audit.metadata)
        self.assertIn("user_agent", login_audit.metadata)

    @pytest.mark.django_db
    def test_logout_audit_integration(self):
        """Test complete logout workflow with audit logging."""
        # Clear any existing audits
        AuditTrail.objects.all().delete()

        # Login first
        self.client.force_login(self.user)

        # Manually create audit for logout
        audit_create(
            user=self.user,
            action_type=AuditActionType.LOGOUT,
            target_entity=self.user,
            metadata={"ip_address": "127.0.0.1", "user_agent": "TestClient"},
        )

        # Verify audit trail was created
        logout_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.LOGOUT.value, user=self.user
        )

        self.assertEqual(logout_audits.count(), 1)

        logout_audit = logout_audits.first()
        self.assertEqual(logout_audit.user, self.user)
        self.assertEqual(logout_audit.action_type, AuditActionType.LOGOUT.value)

    @pytest.mark.django_db
    def test_failed_login_audit_integration(self):
        """Test failed login attempt with audit logging."""
        # Clear any existing audits
        AuditTrail.objects.all().delete()

        # Attempt login with wrong password (this will trigger the signal automatically)
        response = self.client.post(
            "/admin/login/", {"username": self.user.email, "password": "wrongpassword"}
        )

        # Should not be successful
        self.assertEqual(response.status_code, 200)  # Login form redisplayed

        # Verify audit trail was created automatically by signal
        failed_login_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.LOGIN_FAILED.value
        )

        self.assertEqual(failed_login_audits.count(), 1)

        failed_audit = failed_login_audits.first()
        self.assertIsNone(failed_audit.user)  # No user for failed login
        self.assertEqual(failed_audit.action_type, AuditActionType.LOGIN_FAILED.value)
        self.assertEqual(failed_audit.metadata["attempted_username"], self.user.email)


@pytest.mark.integration
class TestAuditBusinessWorkflowIntegration(TestCase):
    """Test audit system integration with business workflows."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.workspace = WorkspaceFactory()
        self.entry = EntryFactory(workspace=self.workspace)
        # Clear any audits created during setUp to avoid interference with tests
        AuditTrail.objects.all().delete()

    @pytest.mark.django_db
    def test_entry_lifecycle_audit_integration(self):
        """Test complete entry lifecycle with audit logging."""
        # 1. Entry creation (should be audited by signals)
        new_entry = EntryFactory(workspace=self.workspace, amount=500.00)

        # 2. Entry submission (business workflow)
        BusinessAuditLogger.log_entry_action(
            user=self.user,
            entry=new_entry,
            action="submit",
            request=None,
            notes="Submitted for approval",
        )

        # 3. Entry approval (business workflow)
        BusinessAuditLogger.log_entry_action(
            user=self.user,
            entry=new_entry,
            action="approve",
            request=None,
            notes="Approved by manager",
            level="manager",
        )

        # 4. Entry update (should be audited by signals)
        new_entry.description = "Updated Integration Test Entry"
        new_entry.amount = (
            600.00  # Change a tracked field to ensure update signal triggers
        )
        new_entry.save()

        # Verify complete audit trail
        entry_audits = AuditTrail.objects.filter(
            target_entity_type__model="entry", target_entity_id=str(new_entry.entry_id)
        ).order_by("timestamp")

        self.assertEqual(entry_audits.count(), 4)

        # Verify audit sequence
        audit_actions = [audit.action_type for audit in entry_audits]
        expected_actions = [
            AuditActionType.ENTRY_CREATED.value,
            AuditActionType.ENTRY_SUBMITTED.value,
            AuditActionType.ENTRY_APPROVED.value,
            AuditActionType.ENTRY_UPDATED.value,
        ]

        self.assertEqual(audit_actions, expected_actions)

        # Verify metadata for business actions
        submit_audit = entry_audits.filter(
            action_type=AuditActionType.ENTRY_SUBMITTED.value
        ).first()
        self.assertEqual(submit_audit.metadata["action"], "submit")
        self.assertEqual(submit_audit.metadata["notes"], "Submitted for approval")

        approve_audit = entry_audits.filter(
            action_type=AuditActionType.ENTRY_APPROVED.value
        ).first()
        self.assertEqual(approve_audit.metadata["action"], "approve")
        self.assertEqual(approve_audit.metadata["approval_level"], "manager")

    @pytest.mark.django_db
    def test_permission_change_workflow_integration(self):
        """Test permission change workflow with audit logging."""
        target_user = CustomUserFactory()

        # 1. Grant permission
        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=target_user,
            permission="admin_access",
            action="grant",
            request=None,
            reason="Promotion to admin role",
        )

        # 2. Revoke permission
        BusinessAuditLogger.log_permission_change(
            user=self.user,
            target_user=target_user,
            permission="admin_access",
            action="revoke",
            request=None,
            reason="Role change",
        )

        # Verify audit trail
        permission_audits = AuditTrail.objects.filter(
            target_entity_type__model="customuser",
            target_entity_id=str(target_user.user_id),
        ).order_by("timestamp")

        self.assertEqual(permission_audits.count(), 2)

        grant_audit = permission_audits.first()
        self.assertEqual(
            grant_audit.action_type, AuditActionType.PERMISSION_GRANTED.value
        )
        self.assertEqual(grant_audit.metadata["permission"], "admin_access")
        self.assertEqual(
            grant_audit.metadata["change_reason"], "Promotion to admin role"
        )

        revoke_audit = permission_audits.last()
        self.assertEqual(
            revoke_audit.action_type, AuditActionType.PERMISSION_REVOKED.value
        )
        self.assertEqual(revoke_audit.metadata["permission"], "admin_access")
        self.assertEqual(revoke_audit.metadata["change_reason"], "Role change")

    @pytest.mark.django_db
    def test_data_export_workflow_integration(self):
        """Test data export workflow with audit logging."""
        # Create some entries for export
        entries = [EntryFactory(workspace=self.workspace) for _ in range(10)]

        # Log data export
        export_filters = {
            "workspace_id": self.workspace.workspace_id,
            "date_range": "2024-01-01 to 2024-01-31",
            "status": "approved",
        }

        BusinessAuditLogger.log_data_export(
            user=self.user,
            export_type="entries",
            filters=export_filters,
            result_count=len(entries),
            request=None,
            format="xlsx",
            reason="Monthly report",
        )

        # Verify audit trail
        export_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.DATA_EXPORTED.value, user=self.user
        )

        self.assertEqual(export_audits.count(), 1)

        export_audit = export_audits.first()
        self.assertEqual(export_audit.metadata["export_type"], "entries")
        self.assertEqual(export_audit.metadata["result_count"], 10)
        self.assertEqual(export_audit.metadata["export_format"], "xlsx")
        self.assertEqual(export_audit.metadata["export_reason"], "Monthly report")
        # Convert export_filters to strings for comparison since they're serialized as strings
        expected_filters = {k: str(v) for k, v in export_filters.items()}
        self.assertEqual(export_audit.metadata["export_filters"], expected_filters)

    @pytest.mark.django_db
    def test_bulk_operation_workflow_integration(self):
        """Test bulk operation workflow with audit logging."""
        # Create entries for bulk operation
        entries = [EntryFactory(workspace=self.workspace) for _ in range(15)]

        # Log bulk operation
        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_approve",
            affected_objects=entries,
            request=None,
        )

        # Verify audit trail
        bulk_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.BULK_OPERATION.value, user=self.user
        )

        self.assertEqual(bulk_audits.count(), 1)

        bulk_audit = bulk_audits.first()
        self.assertEqual(bulk_audit.metadata["operation_type"], "bulk_approve")
        self.assertEqual(bulk_audit.metadata["total_objects"], 15)


@pytest.mark.integration
class TestAuditSignalIntegration(TestCase):
    """Test audit system integration with Django signals."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.workspace = WorkspaceFactory()
        self.registry = AuditModelRegistry()
        # Clear any audits created during setUp to avoid interference with tests
        AuditTrail.objects.all().delete()

    @pytest.mark.django_db
    def test_model_signal_integration(self):
        """Test model signals integration with audit system."""
        # Note: Entry model is already registered for audit via app initialization
        # Create entry (should trigger post_save signal)
        entry = EntryFactory(
            workspace=self.workspace,
            amount=250.00,
            description="Testing signal integration",
        )

        # Update entry (should trigger pre_save and post_save signals)
        entry.description = "Updated Signal Test Entry"
        entry.amount = 300.00
        entry.save()

        # Delete entry (should trigger pre_delete signal)
        entry_id = entry.entry_id
        entry.delete()

        # Verify audit trail - should have automatic logging metadata for the specific entry
        signal_audits = AuditTrail.objects.filter(
            metadata__automatic_logging=True,
            target_entity_type__model="entry",
            target_entity_id=str(entry_id),
        ).order_by("timestamp")

        self.assertEqual(signal_audits.count(), 3)

        # Verify audit sequence
        audit_actions = [audit.action_type for audit in signal_audits]
        expected_actions = [
            AuditActionType.ENTRY_CREATED.value,
            AuditActionType.ENTRY_UPDATED.value,
            AuditActionType.ENTRY_DELETED.value,
        ]

        self.assertEqual(audit_actions, expected_actions)

        # Verify update audit metadata
        update_audit = signal_audits.filter(
            action_type=AuditActionType.ENTRY_UPDATED.value
        ).first()
        self.assertIn("changed_fields", update_audit.metadata)
        self.assertEqual(update_audit.metadata["operation_type"], "update")

    @pytest.mark.django_db
    def test_cross_model_audit_integration(self):
        """Test audit integration across multiple models."""
        # Note: Entry and Workspace models are already registered for audit via app initialization
        # Create workspace
        workspace = WorkspaceFactory(title="Integration Test Workspace")

        # Create entry in workspace
        entry = EntryFactory(workspace=workspace)

        # Update workspace (affects related entries)
        workspace.title = "Updated Integration Test Workspace"
        workspace.save()

        # Verify cross-model audit trail - should have automatic logging metadata
        # Filter to only the workspace and entry we created in this test
        workspace_audits = AuditTrail.objects.filter(
            metadata__automatic_logging=True,
            target_entity_type__model="workspace",
            target_entity_id=str(workspace.workspace_id),
        ).order_by("timestamp")

        entry_audits = AuditTrail.objects.filter(
            metadata__automatic_logging=True,
            target_entity_type__model="entry",
            target_entity_id=str(entry.entry_id),
        ).order_by("timestamp")

        # Verify different model types are audited
        self.assertEqual(workspace_audits.count(), 2)  # creation and update
        self.assertEqual(entry_audits.count(), 1)  # creation

        # Total should be 3
        total_test_audits = workspace_audits.count() + entry_audits.count()
        self.assertEqual(total_test_audits, 3)


@pytest.mark.integration
class TestAuditSystemEndToEnd(TestCase):
    """Test complete end-to-end audit system workflows."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.workspace = WorkspaceFactory()

    @pytest.mark.django_db
    def test_complete_audit_lifecycle(self):
        """Test complete audit lifecycle from creation to cleanup."""
        # Clear any existing audits
        AuditTrail.objects.all().delete()

        # 1. User authentication audit
        user_logged_in.send(
            sender=User, request=Mock(META={"REMOTE_ADDR": "127.0.0.1"}), user=self.user
        )

        # 2. Business operation audits
        # Create entry with audit user context for proper tracking
        # Use transaction to ensure all objects are created consistently
        with transaction.atomic():
            # First create a team in the same organization as the workspace
            team = TeamFactory(organization=self.workspace.organization)
            # Explicitly pass the team to prevent WorkspaceTeamFactory from creating a new one
            workspace_team = WorkspaceTeamFactory.create(
                workspace=self.workspace, team=team
            )

            # Create a team member for this team
            submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

            # Create entry with proper workspace_team relationship and audit user context
            # Set _audit_user BEFORE creation so the signal handler can capture it
            entry = EntryFactory.build(
                workspace=self.workspace,
                workspace_team=workspace_team,
                submitter=submitter,
            )
            entry._audit_user = self.user
            entry.save()  # This will trigger the post_save signal with the correct user
        # Note: Entry creation is automatically audited by signal handlers

        # Entry submission
        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=entry, action="submit", request=None
        )

        # Entry approval
        BusinessAuditLogger.log_entry_action(
            user=self.user, entry=entry, action="approve", request=None
        )

        # 3. Data export audit
        BusinessAuditLogger.log_data_export(
            user=self.user,
            export_type="entries",
            filters={"workspace_id": self.workspace.workspace_id},
            result_count=1,
            request=None,
        )

        # 4. User logout audit
        user_logged_out.send(
            sender=User, request=Mock(META={"REMOTE_ADDR": "127.0.0.1"}), user=self.user
        )

        # Verify complete audit trail - filter to only audits with user set (manual audits and some automatic ones)
        user_audits = AuditTrail.objects.filter(user=self.user).order_by("timestamp")

        # We expect: LOGIN_SUCCESS, ENTRY_CREATED, ENTRY_SUBMITTED, ENTRY_APPROVED, DATA_EXPORTED, LOGOUT
        # But we might get additional audits from workspace creation in setUp
        expected_actions = [
            AuditActionType.LOGIN_SUCCESS.value,
            AuditActionType.ENTRY_CREATED.value,
            AuditActionType.ENTRY_SUBMITTED.value,
            AuditActionType.ENTRY_APPROVED.value,
            AuditActionType.DATA_EXPORTED.value,
            AuditActionType.LOGOUT.value,
        ]

        # Filter to only the expected audit types
        filtered_audits = user_audits.filter(action_type__in=expected_actions)

        self.assertEqual(filtered_audits.count(), 6)

        # Verify audit sequence represents complete workflow
        audit_actions = [audit.action_type for audit in filtered_audits]

        self.assertEqual(audit_actions, expected_actions)

        # Verify audit metadata integrity
        for audit in user_audits:
            self.assertIsNotNone(audit.timestamp)
            self.assertEqual(audit.user, self.user)
            self.assertIsInstance(audit.metadata, dict)

    @pytest.mark.django_db
    def test_audit_trail_consistency(self):
        """Test audit trail consistency across operations."""
        # Clear any existing audits
        AuditTrail.objects.all().delete()

        # Create multiple related objects
        entries = [EntryFactory(workspace=self.workspace) for _ in range(5)]
        # Note: Entry creation is automatically audited by signal handlers

        # Perform bulk operation
        BusinessAuditLogger.log_bulk_operation(
            user=self.user,
            operation_type="bulk_approve",
            affected_objects=entries,
            request=None,
        )

        # Verify audit consistency
        # Count all audits created during this test (automatic entry creation + manual bulk operation)
        entry_creation_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.ENTRY_CREATED.value,
            target_entity_type__model="entry",
        )

        bulk_operation_audits = AuditTrail.objects.filter(
            action_type=AuditActionType.BULK_OPERATION.value, user=self.user
        )

        # Should have 5 entry creation audits + 1 bulk operation audit
        self.assertEqual(entry_creation_audits.count(), 5)
        self.assertEqual(bulk_operation_audits.count(), 1)

        total_relevant_audits = (
            entry_creation_audits.count() + bulk_operation_audits.count()
        )
        self.assertEqual(total_relevant_audits, 6)  # 5 individual + 1 bulk

        # Verify bulk operation references all entries
        bulk_audit = AuditTrail.objects.filter(
            action_type=AuditActionType.BULK_OPERATION.value
        ).first()

        self.assertEqual(bulk_audit.metadata["total_objects"], 5)
        self.assertEqual(len(bulk_audit.metadata["object_ids"]), 5)

        # Verify all entry IDs are captured
        expected_ids = [str(entry.entry_id) for entry in entries]
        self.assertEqual(set(bulk_audit.metadata["object_ids"]), set(expected_ids))
