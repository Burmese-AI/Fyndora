"""Tests for WorkspaceAuditLogger."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.workspace_logger import WorkspaceAuditLogger
from tests.factories.workspace_factories import WorkspaceFactory


class TestWorkspaceAuditLogger(TestCase):
    """Test cases for WorkspaceAuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = WorkspaceAuditLogger()
        self.mock_user = Mock(spec=User)
        self.mock_user.user_id = "test-user-123"
        self.mock_user.email = "test@example.com"
        self.mock_user.is_authenticated = True

        self.mock_request = Mock(spec=HttpRequest)
        self.mock_request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "Test Browser",
        }
        self.mock_request.method = "POST"
        self.mock_request.path = "/test/path"
        self.mock_request.session = Mock()
        self.mock_request.session.session_key = "test-session-key"

        self.mock_workspace = Mock()
        self.mock_workspace.workspace_id = "workspace-123"
        self.mock_workspace.title = "Test Workspace"
        self.mock_workspace.status = "active"
        self.mock_workspace.description = "Test workspace description"
        self.mock_workspace.pk = "workspace-123"
        self.mock_workspace.__class__.__name__ = "Workspace"
        self.mock_workspace.__class__.__module__ = "apps.workspaces.models"
        self.mock_workspace._meta = Mock()
        self.mock_workspace._meta.pk = Mock()
        self.mock_workspace._meta.pk.name = "pk"

        self.mock_team = Mock()
        self.mock_team.team_id = "team-456"
        self.mock_team.name = "Test Team"
        self.mock_team.role = "translator"
        self.mock_team.pk = "team-456"
        self.mock_team.__class__.__name__ = "Team"
        self.mock_team.__class__.__module__ = "apps.teams.models"
        self.mock_team._meta = Mock()
        self.mock_team._meta.pk = Mock()
        self.mock_team._meta.pk.name = "pk"
        self.mock_team.workspace = Mock()
        self.mock_team.workspace.pk = "workspace-123"

        self.mock_exchange_rate = Mock()
        self.mock_exchange_rate.id = "rate-789"
        self.mock_exchange_rate.from_currency = "USD"
        self.mock_exchange_rate.to_currency = "EUR"
        self.mock_exchange_rate.rate = 0.85
        self.mock_exchange_rate.pk = "rate-789"
        self.mock_exchange_rate.__class__.__name__ = "ExchangeRate"
        self.mock_exchange_rate.__class__.__module__ = "apps.currencies.models"
        self.mock_exchange_rate._meta = Mock()
        self.mock_exchange_rate._meta.pk = Mock()
        self.mock_exchange_rate._meta.pk.name = "pk"
        self.mock_exchange_rate.workspace = Mock()
        self.mock_exchange_rate.workspace.pk = "workspace-123"

    def test_get_supported_actions(self):
        """Test that get_supported_actions returns correct actions."""
        expected_actions = {
            "create",
            "update",
            "delete",
            "archive",
            "activate",
            "close",
            "status_change",
        }
        self.assertEqual(set(self.logger.get_supported_actions()), expected_actions)

    def test_get_logger_name(self):
        """Test that get_logger_name returns correct name."""
        self.assertEqual(self.logger.get_logger_name(), "workspace_logger")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_create(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for create action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {
            "workspace_id": "workspace-123",
            "workspace_title": "Test Workspace",
        }

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            workspace=self.mock_workspace,
        )

        # Verify calls
        mock_workspace_metadata.assert_called_once_with(self.mock_workspace)
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_CREATED)  # action_type
        # call_args[2] is metadata, call_args[3] is workspace, call_args[4] is workspace

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_action_update(self, mock_finalize_audit):
        """Test log_workspace_action for update action."""
        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            workspace=self.mock_workspace,
            updated_fields=["title"],
            old_title="Old Title",
            new_title="New Title",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_UPDATED)  # action_type

        # Verify title change metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_title"], "Old Title")
        self.assertEqual(metadata["new_title"], "New Title")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_action_delete(self, mock_finalize_audit):
        """Test log_workspace_action for delete action."""
        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            workspace=self.mock_workspace,
            soft_delete=True,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_DELETED)  # action_type

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_archive(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for archive action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="archive",
            workspace=self.mock_workspace,
            reason="Project completed",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_ARCHIVED
        )  # action_type

        # Verify reason is included in metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["reason"], "Project completed")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_activate(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for activate action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="activate",
            workspace=self.mock_workspace,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_ACTIVATED
        )  # action_type

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_close(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for close action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="close",
            workspace=self.mock_workspace,
            reason="Budget exhausted",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.WORKSPACE_CLOSED)  # action_type

        # Verify reason is included in metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["reason"], "Budget exhausted")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
    )
    def test_log_workspace_action_status_change(
        self, mock_workspace_metadata, mock_finalize_audit
    ):
        """Test log_workspace_action for status_change action."""
        # Setup mocks
        mock_workspace_metadata.return_value = {"workspace_id": "workspace-123"}

        # Call method
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="status_change",
            workspace=self.mock_workspace,
            old_status="draft",
            new_status="active",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_STATUS_CHANGED
        )  # action_type

        # Verify status change metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_status"], "draft")
        self.assertEqual(metadata["new_status"], "active")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_team_action_add(self, mock_finalize_audit):
        """Test log_workspace_team_action for add action."""
        # Call method
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="add",
            workspace=self.mock_workspace,
            team=self.mock_team,
            role="translator",
        )

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_TEAM_ADDED
        )  # action_type

        # Verify team role metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["role"], "translator")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_team_action_remove(self, mock_finalize_audit):
        """Test log_workspace_team_action for remove action."""
        # Call method
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="remove",
            workspace=self.mock_workspace,
            team=self.mock_team,
            reason="Team reassignment",
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_TEAM_REMOVED
        )  # action_type

        # Verify reason is included in metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["reason"], "Team reassignment")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_team_action_remittance_rate_update(
        self, mock_finalize_audit
    ):
        """Test log_workspace_team_action for remittance_rate_update action."""
        # Call method
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="remittance_rate_update",
            workspace=self.mock_workspace,
            team=self.mock_team,
            old_rate=0.15,
            new_rate=0.18,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1],
            AuditActionType.WORKSPACE_TEAM_REMITTANCE_RATE_UPDATED,
        )  # action_type

        # Verify rate change metadata
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_rate"], 0.15)
        self.assertEqual(metadata["new_rate"], 0.18)

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_exchange_rate_action_create(self, mock_finalize_audit):
        """Test log_workspace_exchange_rate_action for create action."""
        # Call method
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_EXCHANGE_RATE_CREATED
        )  # action_type

        # Verify exchange rate metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["exchange_rate_id"], "rate-789")
        self.assertEqual(metadata["from_currency"], "USD")
        self.assertEqual(metadata["to_currency"], "EUR")
        self.assertEqual(metadata["rate"], "0.85")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_exchange_rate_action_update(self, mock_finalize_audit):
        """Test log_workspace_exchange_rate_action for update action."""
        # Call method
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
            updated_fields=["rate"],
            old_rate=0.80,
            new_rate=0.85,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_EXCHANGE_RATE_UPDATED
        )  # action_type

        # Verify rate change metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_rate"], 0.80)
        self.assertEqual(metadata["new_rate"], 0.85)

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_log_workspace_exchange_rate_action_delete(self, mock_finalize_audit):
        """Test log_workspace_exchange_rate_action for delete action."""
        # Call method
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.WORKSPACE_EXCHANGE_RATE_DELETED
        )  # action_type

    @patch("apps.auditlog.loggers.base_logger.logger")
    def test_log_workspace_action_invalid_action(self, mock_logger):
        """Test log_workspace_action with invalid action logs warning."""
        self.logger.log_workspace_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            workspace=self.mock_workspace,
        )

        mock_logger.warning.assert_called_once_with("Unknown action: invalid_action")

    @patch("apps.auditlog.loggers.workspace_logger.logger")
    def test_log_workspace_team_action_invalid_action(self, mock_logger):
        """Test log_workspace_team_action with invalid action logs warning."""
        self.logger.log_workspace_team_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            workspace=self.mock_workspace,
            team=self.mock_team,
        )

        mock_logger.warning.assert_called_once_with(
            "Unknown workspace team action: invalid_action"
        )

    @patch("apps.auditlog.loggers.workspace_logger.logger")
    def test_log_workspace_exchange_rate_action_invalid_action(self, mock_logger):
        """Test log_workspace_exchange_rate_action with invalid action logs warning."""
        self.logger.log_workspace_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            workspace=self.mock_workspace,
            exchange_rate=self.mock_exchange_rate,
        )

        mock_logger.warning.assert_called_once_with(
            "Unknown workspace exchange rate action: invalid_action"
        )

    # Removed test_validation_methods_called - covered by comprehensive tests

    # Removed test_metadata_combination - covered by comprehensive tests

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_exchange_rate_metadata_extraction(self, mock_finalize_audit):
        """Test that exchange rate metadata is properly extracted."""
        with patch(
            "apps.auditlog.loggers.workspace_logger.EntityMetadataBuilder.build_workspace_metadata"
        ):
            with patch(
                "apps.auditlog.loggers.workspace_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ):
                # Test with exchange rate that has additional attributes
                self.mock_exchange_rate.effective_date = "2024-01-01"
                self.mock_exchange_rate.created_by = "admin-user"

                self.logger.log_workspace_exchange_rate_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    workspace=self.mock_workspace,
                    exchange_rate=self.mock_exchange_rate,
                )

                # Verify exchange rate metadata extraction
                call_args = mock_finalize_audit.call_args[0]
                user, action_type, metadata, target_entity = call_args
                self.assertEqual(metadata["exchange_rate_id"], "rate-789")
                self.assertEqual(metadata["from_currency"], "USD")
                self.assertEqual(metadata["to_currency"], "EUR")
                self.assertEqual(metadata["rate"], "0.85")

    # Removed test_team_action_metadata_combination - covered by comprehensive tests


@pytest.mark.unit
class TestWorkspaceAuditLoggerComprehensiveScenarios(TestCase):
    """Comprehensive test scenarios for workspace audit logging."""

    def setUp(self):
        """Set up test fixtures."""
        from tests.factories.user_factories import CustomUserFactory
        from tests.factories.organization_factories import (
            OrganizationFactory,
            OrganizationMemberFactory,
        )
        from tests.factories.workspace_factories import WorkspaceFactory
        from tests.factories.team_factories import TeamFactory, TeamMemberFactory
        from tests.factories.auditlog_factories import (
            WorkspaceCreatedAuditFactory,
            WorkspaceUpdatedAuditFactory,
            WorkspaceDeletedAuditFactory,
        )

        self.logger = WorkspaceAuditLogger()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(
            team=self.team, organization_member=self.org_member
        )

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_workspace_creation_with_comprehensive_metadata(self, mock_finalize_audit):
        """Test workspace creation audit with comprehensive metadata tracking."""

        # Log workspace creation
        self.logger.log_workspace_action(
            user=self.user,
            action="create",
            workspace=self.workspace,
            project_type="translation",
            source_language="en",
            target_languages=["es", "fr", "de"],
            deadline="2024-03-15",
            priority="high",
            budget=15000.00,
            client_requirements={
                "quality_level": "premium",
                "delivery_format": "xliff",
                "review_cycles": 2,
            },
        )

        # Verify comprehensive metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]  # metadata is the third argument

        self.assertIn("project_type", metadata)
        self.assertIn("source_language", metadata)
        self.assertIn("target_languages", metadata)
        self.assertIn("deadline", metadata)
        self.assertIn("priority", metadata)
        self.assertIn("budget", metadata)
        self.assertIn("client_requirements", metadata)
        self.assertEqual(metadata["project_type"], "translation")
        self.assertEqual(metadata["priority"], "high")
        self.assertEqual(metadata["budget"], 15000.00)
        self.assertEqual(metadata["client_requirements"]["quality_level"], "premium")

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_workspace_status_change_with_detailed_tracking(self, mock_finalize_audit):
        """Test workspace status change audit with detailed tracking."""

        # Log workspace status change
        self.logger.log_workspace_action(
            user=self.user,
            action="status_change",
            workspace=self.workspace,
            old_status="in_progress",
            new_status="completed",
            completion_percentage=100,
            quality_score=98.5,
            final_word_count=25000,
            delivery_date="2024-01-20T14:30:00Z",
            client_approval=True,
            final_review_notes="Excellent quality, delivered on time",
        )

        # Verify status change tracking
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertIn("old_status", metadata)
        self.assertIn("new_status", metadata)
        self.assertIn("completion_percentage", metadata)
        self.assertIn("quality_score", metadata)
        self.assertIn("final_word_count", metadata)
        self.assertEqual(metadata["old_status"], "in_progress")
        self.assertEqual(metadata["new_status"], "completed")
        self.assertEqual(metadata["completion_percentage"], 100)
        self.assertEqual(metadata["quality_score"], 98.5)
        self.assertTrue(metadata["client_approval"])

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_workspace_team_assignment_comprehensive_tracking(
        self, mock_finalize_audit
    ):
        """Test workspace team assignment audit with comprehensive tracking."""

        # Log team assignment to workspace
        self.logger.log_workspace_team_action(
            user=self.user,
            action="add",
            workspace=self.workspace,
            team=self.team,
            assignment_type="primary",
            role="translation_team",
            permissions=["translate", "review", "approve"],
            expected_delivery="2024-02-15",
            team_capacity=5,
            specialization="technical_translation",
            rate_per_word=0.12,
            estimated_hours=120,
        )

        # Verify team assignment tracking
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertIn("assignment_type", metadata)
        self.assertIn("role", metadata)
        self.assertIn("permissions", metadata)
        self.assertIn("expected_delivery", metadata)
        self.assertIn("team_capacity", metadata)
        self.assertIn("specialization", metadata)
        self.assertEqual(metadata["assignment_type"], "primary")
        self.assertEqual(metadata["role"], "translation_team")
        self.assertEqual(metadata["rate_per_word"], 0.12)
        self.assertEqual(metadata["estimated_hours"], 120)

    def test_audit_factory_integration_workspace_created(self):
        """Test integration with WorkspaceCreatedAuditFactory."""
        from tests.factories.auditlog_factories import WorkspaceCreatedAuditFactory

        # Create audit log using factory
        audit_log = WorkspaceCreatedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.WORKSPACE_CREATED)
        self.assertIn("workspace_id", audit_log.metadata)
        self.assertIn("workspace_title", audit_log.metadata)
        self.assertIn("created_by", audit_log.metadata)

    def test_audit_factory_integration_workspace_updated(self):
        """Test integration with WorkspaceUpdatedAuditFactory."""
        from tests.factories.auditlog_factories import WorkspaceUpdatedAuditFactory

        # Create audit log using factory
        audit_log = WorkspaceUpdatedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.WORKSPACE_UPDATED)
        self.assertIn("updated_fields", audit_log.metadata)
        self.assertIn("updated_by", audit_log.metadata)
        self.assertEqual(audit_log.metadata["updated_by"], self.user.username)

    def test_audit_factory_integration_workspace_deleted(self):
        """Test integration with WorkspaceDeletedAuditFactory."""
        from tests.factories.auditlog_factories import WorkspaceDeletedAuditFactory

        # Create audit log using factory
        audit_log = WorkspaceDeletedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.WORKSPACE_DELETED)
        self.assertIn("deleted_by", audit_log.metadata)
        self.assertIn("soft_delete", audit_log.metadata)
        self.assertEqual(audit_log.metadata["deleted_by"], self.user.username)

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_bulk_workspace_operations_performance(self, mock_finalize_audit):
        """Test performance of bulk workspace operations."""
        import time

        # Create multiple workspaces
        workspaces = []
        for i in range(8):
            workspace = WorkspaceFactory(organization=self.organization)
            workspaces.append(workspace)

        start_time = time.time()

        # Log multiple workspace updates
        for workspace in workspaces:
            self.logger.log_workspace_action(
                user=self.user,
                action="update",
                workspace=workspace,
                updated_fields=["status"],
                bulk_operation=True,
                batch_id="batch_002",
            )

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete within reasonable time
        self.assertLess(execution_time, 1.5, "Bulk workspace operations took too long")
        self.assertEqual(mock_finalize_audit.call_count, 8)

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_workspace_exchange_rate_comprehensive_tracking(self, mock_finalize_audit):
        """Test comprehensive workspace exchange rate audit tracking."""

        # Mock exchange rate
        mock_exchange_rate = Mock()
        mock_exchange_rate.id = "rate-789"
        mock_exchange_rate.from_currency = "USD"
        mock_exchange_rate.to_currency = "JPY"
        mock_exchange_rate.rate = 150.25
        mock_exchange_rate.workspace = self.workspace

        # Log exchange rate update
        self.logger.log_workspace_exchange_rate_action(
            user=self.user,
            action="update",
            exchange_rate=mock_exchange_rate,
            rate_source="Bank_of_Japan",
            update_trigger="scheduled_daily",
            previous_rate=148.75,
            rate_change=1.50,
            impact_assessment="minimal",
            affected_transactions=15,
            recalculation_required=True,
        )

        # Verify exchange rate metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertIn("rate_source", metadata)
        self.assertIn("update_trigger", metadata)
        self.assertIn("previous_rate", metadata)
        self.assertIn("rate_change", metadata)
        self.assertIn("impact_assessment", metadata)
        self.assertIn("affected_transactions", metadata)
        self.assertEqual(metadata["rate_source"], "Bank_of_Japan")
        self.assertEqual(metadata["rate_change"], 1.50)
        self.assertEqual(metadata["affected_transactions"], 15)
        self.assertTrue(metadata["recalculation_required"])

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_workspace_archive_with_preservation_metadata(self, mock_finalize_audit):
        """Test workspace archival with preservation metadata."""

        # Log workspace archival
        self.logger.log_workspace_action(
            user=self.user,
            action="archive",
            workspace=self.workspace,
            archive_reason="Project completed",
            data_retention_period="7_years",
            backup_location="s3://archive-bucket/workspace-123",
            final_statistics={
                "total_words": 50000,
                "completed_tasks": 125,
                "team_members": 8,
                "duration_days": 45,
            },
            client_satisfaction=4.8,
            lessons_learned="Excellent team coordination",
            reactivation_possible=False,
        )

        # Verify archival metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertIn("archive_reason", metadata)
        self.assertIn("data_retention_period", metadata)
        self.assertIn("backup_location", metadata)
        self.assertIn("final_statistics", metadata)
        self.assertIn("client_satisfaction", metadata)
        self.assertEqual(metadata["archive_reason"], "Project completed")
        self.assertEqual(metadata["final_statistics"]["total_words"], 50000)
        self.assertEqual(metadata["client_satisfaction"], 4.8)
        self.assertFalse(metadata["reactivation_possible"])

    @patch(
        "apps.auditlog.loggers.workspace_logger.WorkspaceAuditLogger._finalize_and_create_audit"
    )
    def test_workspace_audit_metadata_validation(self, mock_finalize_audit):
        """Test validation of workspace audit metadata structure."""

        # Log workspace action with complex nested metadata
        complex_metadata = {
            "workflow_configuration": {
                "stages": ["translation", "review", "proofreading", "final_check"],
                "quality_gates": {
                    "translation_threshold": 95,
                    "review_threshold": 98,
                    "final_threshold": 99,
                },
                "automation_rules": {
                    "auto_assign": True,
                    "deadline_alerts": True,
                    "quality_checks": ["spell_check", "terminology", "consistency"],
                },
            },
            "resource_allocation": {
                "translators": 3,
                "reviewers": 2,
                "project_managers": 1,
                "estimated_hours": {"translation": 80, "review": 40, "management": 20},
            },
            "integration_settings": {
                "cat_tools": ["Trados", "MemoQ"],
                "tm_databases": ["client_tm", "general_tm"],
                "glossaries": ["technical_terms", "brand_terms"],
            },
        }

        self.logger.log_workspace_action(
            user=self.user,
            action="update",
            workspace=self.workspace,
            workflow_configuration=complex_metadata["workflow_configuration"],
            resource_allocation=complex_metadata["resource_allocation"],
            integration_settings=complex_metadata["integration_settings"],
            permissions=["read", "review"],
        )

        # Verify complex metadata is preserved
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        self.assertIn("workflow_configuration", metadata)
        self.assertIn("resource_allocation", metadata)
        self.assertIn("integration_settings", metadata)
        self.assertEqual(len(metadata["workflow_configuration"]["stages"]), 4)
        self.assertEqual(
            metadata["workflow_configuration"]["quality_gates"]["final_threshold"], 99
        )
        self.assertTrue(
            metadata["workflow_configuration"]["automation_rules"]["auto_assign"]
        )
        self.assertEqual(metadata["resource_allocation"]["translators"], 3)
        self.assertIn("Trados", metadata["integration_settings"]["cat_tools"])
        self.assertEqual(metadata["permissions"], ["read", "review"])
