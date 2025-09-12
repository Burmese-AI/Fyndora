"""Tests for OrganizationAuditLogger."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.organization_logger import OrganizationAuditLogger
from tests.factories.organization_factories import OrganizationFactory


class TestOrganizationAuditLogger(TestCase):
    """Test cases for OrganizationAuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = OrganizationAuditLogger()
        self.mock_user = Mock(spec=User)
        self.mock_user.user_id = "test-user-123"
        self.mock_user.email = "test@example.com"
        self.mock_user.is_authenticated = True

        self.mock_request = Mock(spec=HttpRequest)
        self.mock_request.method = "POST"
        self.mock_request.path = "/test/path"
        self.mock_request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "Test Browser",
        }
        # Mock session with session_key attribute
        mock_session = Mock()
        mock_session.session_key = "test-session-key"
        self.mock_request.session = mock_session

        self.mock_organization = Mock()
        self.mock_organization.organization_id = "org-123"
        self.mock_organization.title = "Test Organization"
        self.mock_organization.status = "active"
        self.mock_organization.description = "Test organization description"

        self.mock_exchange_rate = Mock()
        self.mock_exchange_rate.id = "rate-123"
        self.mock_exchange_rate.pk = "rate-123"  # Django models use pk as primary key
        self.mock_exchange_rate.from_currency = "USD"
        self.mock_exchange_rate.to_currency = "EUR"
        self.mock_exchange_rate.rate = 0.85
        self.mock_exchange_rate.organization = self.mock_organization

    def test_get_supported_actions(self):
        """Test that get_supported_actions returns correct actions."""
        expected_actions = {"create", "update", "delete"}
        self.assertEqual(set(self.logger.get_supported_actions()), expected_actions)

    def test_get_logger_name(self):
        """Test that get_logger_name returns correct name."""
        self.assertEqual(self.logger.get_logger_name(), "organization_logger")

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
    )
    def test_log_organization_action_create(
        self, mock_org_metadata, mock_crud_metadata, mock_finalize_audit
    ):
        """Test log_organization_action for create action."""
        # Setup mocks
        mock_org_metadata.return_value = {
            "organization_id": "org-123",
            "organization_title": "Test Organization",
        }
        mock_crud_metadata.return_value = {
            "creator_id": "test-user-123",
            "creation_timestamp": "2024-01-01T00:00:00Z",
        }

        # Call method
        self.logger.log_organization_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            organization=self.mock_organization,
        )

        # Verify calls
        mock_org_metadata.assert_called_once_with(self.mock_organization)
        mock_crud_metadata.assert_called_once_with(
            self.mock_user, "create", updated_fields=[], soft_delete=False
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(
            call_args[1], AuditActionType.ORGANIZATION_CREATED
        )  # action_type
        # call_args[2] is metadata dict
        self.assertEqual(call_args[3], self.mock_organization)  # target_entity

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
    )
    def test_log_organization_action_update(
        self, mock_org_metadata, mock_crud_metadata, mock_finalize_audit
    ):
        """Test log_organization_action for update action."""
        # Setup mocks
        mock_org_metadata.return_value = {"organization_id": "org-123"}
        mock_crud_metadata.return_value = {
            "updater_id": "test-user-123",
            "updated_fields": ["title", "description"],
        }

        # Call method
        self.logger.log_organization_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            organization=self.mock_organization,
            updated_fields=["title", "description"],
        )

        # Verify calls
        mock_crud_metadata.assert_called_once_with(
            self.mock_user,
            "update",
            updated_fields=["title", "description"],
            soft_delete=False,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1], AuditActionType.ORGANIZATION_UPDATED
        )  # action_type

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
    )
    def test_log_organization_action_delete(
        self, mock_org_metadata, mock_crud_metadata, mock_finalize_audit
    ):
        """Test log_organization_action for delete action."""
        # Setup mocks
        mock_org_metadata.return_value = {"organization_id": "org-123"}
        mock_crud_metadata.return_value = {
            "deleter_id": "test-user-123",
            "soft_delete": True,
        }

        # Call method
        self.logger.log_organization_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            organization=self.mock_organization,
            soft_delete=True,
        )

        # Verify calls
        mock_crud_metadata.assert_called_once_with(
            self.mock_user, "delete", updated_fields=[], soft_delete=True
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1], AuditActionType.ORGANIZATION_DELETED
        )  # action_type

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
    )
    def test_log_organization_exchange_rate_action_create(
        self, mock_org_metadata, mock_crud_metadata, mock_finalize_audit
    ):
        """Test log_organization_exchange_rate_action for create action."""
        # Setup mocks
        mock_org_metadata.return_value = {"organization_id": "org-123"}
        mock_crud_metadata.return_value = {"creator_id": "test-user-123"}

        # Call method
        self.logger.log_organization_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="create",
            organization=self.mock_organization,
            exchange_rate=self.mock_exchange_rate,
        )

        # Verify calls
        mock_org_metadata.assert_called_once_with(self.mock_organization)
        mock_crud_metadata.assert_called_once_with(
            self.mock_user,
            "create",
            updated_fields=[],
            soft_delete=False,
            organization=self.mock_organization,
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1],
            AuditActionType.ORGANIZATION_EXCHANGE_RATE_CREATED,  # action_type
        )

        # Verify exchange rate metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["exchange_rate_id"], "rate-123")
        self.assertEqual(metadata["rate"], "0.85")  # rate is converted to string
        # Note: currency_code comes from exchange_rate.currency.code which would be a Mock

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
    )
    def test_log_organization_exchange_rate_action_update(
        self, mock_org_metadata, mock_crud_metadata, mock_finalize_audit
    ):
        """Test log_organization_exchange_rate_action for update action."""
        # Setup mocks
        mock_org_metadata.return_value = {"organization_id": "org-123"}
        mock_crud_metadata.return_value = {
            "updater_id": "test-user-123",
            "updated_fields": ["rate"],
        }

        # Call method
        self.logger.log_organization_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="update",
            organization=self.mock_organization,
            exchange_rate=self.mock_exchange_rate,
            updated_fields=["rate"],
            old_rate=0.80,
            new_rate=0.85,
        )

        # Verify calls
        mock_org_metadata.assert_called_once_with(self.mock_exchange_rate.organization)
        mock_crud_metadata.assert_called_once_with(
            self.mock_user,
            "update",
            updated_fields=["rate"],
            soft_delete=False,
            organization=self.mock_organization,
            old_rate=0.80,
            new_rate=0.85,
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1],
            AuditActionType.ORGANIZATION_EXCHANGE_RATE_UPDATED,  # action_type
        )

        # Verify rate change metadata is included
        metadata = call_args[2]  # metadata is the 3rd positional argument
        self.assertEqual(metadata["old_rate"], 0.80)
        self.assertEqual(metadata["new_rate"], 0.85)

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
    )
    @patch(
        "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
    )
    def test_log_organization_exchange_rate_action_delete(
        self, mock_org_metadata, mock_crud_metadata, mock_finalize_audit
    ):
        """Test log_organization_exchange_rate_action for delete action."""
        # Setup mocks
        mock_org_metadata.return_value = {"organization_id": "org-123"}
        mock_crud_metadata.return_value = {"deleter_id": "test-user-123"}

        # Call method
        self.logger.log_organization_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="delete",
            organization=self.mock_organization,
            exchange_rate=self.mock_exchange_rate,
        )

        # Verify calls
        mock_org_metadata.assert_called_once_with(self.mock_exchange_rate.organization)
        mock_crud_metadata.assert_called_once_with(
            self.mock_user,
            "delete",
            updated_fields=[],
            soft_delete=False,
            organization=self.mock_organization,
        )
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1],
            AuditActionType.ORGANIZATION_EXCHANGE_RATE_DELETED,  # action_type
        )

    @patch("apps.auditlog.loggers.base_logger.logger")
    def test_log_organization_action_invalid_action(self, mock_logger):
        """Test log_organization_action with invalid action logs warning."""
        self.logger.log_organization_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            organization=self.mock_organization,
        )

        mock_logger.warning.assert_called_once_with("Unknown action: invalid_action")

    @patch("apps.auditlog.loggers.base_logger.logger")
    def test_log_organization_exchange_rate_action_invalid_action(self, mock_logger):
        """Test log_organization_exchange_rate_action with invalid action logs warning."""
        self.logger.log_organization_exchange_rate_action(
            request=self.mock_request,
            user=self.mock_user,
            action="invalid_action",
            organization=self.mock_organization,
            exchange_rate=self.mock_exchange_rate,
        )

        mock_logger.warning.assert_called_once_with("Unknown action: invalid_action")

    # Removed test_validation_methods_called - covered by comprehensive tests

    # Removed test_metadata_combination - covered by comprehensive tests

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_exchange_rate_metadata_extraction(self, mock_finalize_audit):
        """Test that exchange rate metadata is properly extracted."""
        with patch(
            "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
        ) as mock_org_meta:
            with patch(
                "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ) as mock_crud_meta:
                # Setup mock return values
                mock_org_meta.return_value = {"organization_id": "org-123"}
                mock_crud_meta.return_value = {"creator_id": "test-user-123"}
                # Test with exchange rate that has additional attributes
                from datetime import datetime

                self.mock_exchange_rate.effective_date = datetime(2024, 1, 1)
                self.mock_exchange_rate.created_by = "admin-user"

                self.logger.log_organization_exchange_rate_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    organization=self.mock_organization,
                    exchange_rate=self.mock_exchange_rate,
                )

                # Verify exchange rate metadata extraction
                call_args = mock_finalize_audit.call_args[0]  # positional arguments
                metadata = call_args[2]  # metadata is the 3rd positional argument
                self.assertEqual(metadata["exchange_rate_id"], "rate-123")
                self.assertEqual(
                    metadata["rate"], "0.85"
                )  # rate is converted to string
                self.assertEqual(metadata["effective_date"], "2024-01-01T00:00:00")
                # Note: currency_code comes from exchange_rate.currency.code which would be a Mock

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_optional_parameters(self, mock_finalize_audit):
        """Test handling of optional parameters in logging methods."""
        with patch(
            "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
        ) as mock_org_meta:
            with patch(
                "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ) as mock_crud_meta:
                # Setup mock return values
                mock_org_meta.return_value = {"organization_id": "org-123"}
                mock_crud_meta.return_value = {"creator_id": "test-user-123"}
                # Test with minimal parameters
                self.logger.log_organization_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    organization=self.mock_organization,
                )

                # Verify call was successful
                self.assertTrue(mock_finalize_audit.called)

                # Test with all optional parameters
                self.logger.log_organization_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="update",
                    organization=self.mock_organization,
                    updated_fields=["title", "description"],
                    reason="Business requirement change",
                )

                # Verify second call was successful
                self.assertEqual(mock_finalize_audit.call_count, 2)


@pytest.mark.unit
class TestOrganizationAuditLoggerComprehensiveScenarios(TestCase):
    """Comprehensive test scenarios for organization audit logging."""

    def setUp(self):
        """Set up test fixtures."""
        from tests.factories.user_factories import CustomUserFactory
        from tests.factories.organization_factories import (
            OrganizationFactory,
            OrganizationMemberFactory,
        )
        from tests.factories.workspace_factories import WorkspaceFactory

        self.logger = OrganizationAuditLogger()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.workspace = WorkspaceFactory(organization=self.organization)

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_organization_creation_with_comprehensive_metadata(
        self, mock_finalize_audit
    ):
        """Test organization creation audit with comprehensive metadata tracking."""
        # Test organization creation audit with standard metadata

        # Log organization creation
        self.logger.log_organization_action(
            request=None,
            user=self.user,
            action="create",
            organization=self.organization,
        )

        # Verify standard creation metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]  # metadata is the third argument

        # Test standard audit metadata fields for creation
        self.assertIn("action", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("organization_title", metadata)
        self.assertIn("creator_id", metadata)
        self.assertIn("creator_email", metadata)
        self.assertIn("creation_timestamp", metadata)
        self.assertEqual(metadata["action"], "create")
        self.assertEqual(metadata["organization_id"], str(self.organization.pk))
        self.assertEqual(metadata["creator_id"], str(self.user.user_id))

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_organization_update_with_field_tracking(self, mock_finalize_audit):
        """Test organization update audit with detailed field change tracking."""
        # Log organization update
        self.logger.log_organization_action(
            request=None,
            user=self.user,
            action="update",
            organization=self.organization,
            updated_fields=["title", "description", "status"],
        )

        # Verify field change tracking
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        # Test standard audit metadata fields for update
        self.assertIn("action", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("organization_title", metadata)
        self.assertIn("updater_id", metadata)
        self.assertIn("updater_email", metadata)
        self.assertIn("update_timestamp", metadata)
        self.assertIn("updated_fields", metadata)
        self.assertEqual(metadata["action"], "update")
        self.assertEqual(metadata["updated_fields"], ["title", "description", "status"])
        self.assertEqual(metadata["organization_id"], str(self.organization.pk))

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_organization_deletion_with_context(self, mock_finalize_audit):
        """Test organization deletion audit with contextual information."""

        # Log organization deletion
        self.logger.log_organization_action(
            request=None,
            user=self.user,
            action="delete",
            organization=self.organization,
            soft_delete=True,
        )

        # Verify deletion context
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        # Test standard audit metadata fields for deletion
        self.assertIn("action", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("organization_title", metadata)
        self.assertIn("deleter_id", metadata)
        self.assertIn("deleter_email", metadata)
        self.assertIn("deletion_timestamp", metadata)
        self.assertIn("soft_delete", metadata)
        self.assertEqual(metadata["action"], "delete")
        self.assertTrue(metadata["soft_delete"])
        self.assertEqual(metadata["organization_id"], str(self.organization.pk))

    def test_audit_factory_integration_organization_created(self):
        """Test integration with OrganizationCreatedAuditFactory."""
        from tests.factories.auditlog_factories import OrganizationCreatedAuditFactory

        # Create audit log using factory
        audit_log = OrganizationCreatedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.ORGANIZATION_CREATED)
        self.assertIn("organization_id", audit_log.metadata)
        self.assertIn("organization_title", audit_log.metadata)
        self.assertIn("created_by", audit_log.metadata)

    def test_audit_factory_integration_organization_updated(self):
        """Test integration with OrganizationUpdatedAuditFactory."""
        from tests.factories.auditlog_factories import OrganizationUpdatedAuditFactory

        # Create audit log using factory
        audit_log = OrganizationUpdatedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.ORGANIZATION_UPDATED)
        self.assertIn("updated_by", audit_log.metadata)
        self.assertEqual(audit_log.metadata["updated_by"], self.user.username)

    def test_audit_factory_integration_organization_deleted(self):
        """Test integration with OrganizationDeletedAuditFactory."""
        from tests.factories.auditlog_factories import OrganizationDeletedAuditFactory

        # Create audit log using factory
        audit_log = OrganizationDeletedAuditFactory(user=self.user)

        # Verify factory creates proper relationships
        self.assertIsNotNone(audit_log.target_entity_id)
        self.assertEqual(audit_log.action_type, AuditActionType.ORGANIZATION_DELETED)
        self.assertIn("deleted_by", audit_log.metadata)
        self.assertEqual(audit_log.metadata["deleted_by"], self.user.username)

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_bulk_organization_operations_performance(self, mock_finalize_audit):
        """Test performance of bulk organization operations."""
        import time

        # Create multiple organizations
        organizations = []
        for i in range(5):
            org = OrganizationFactory()
            organizations.append(org)

        start_time = time.time()

        # Log multiple organization updates
        for org in organizations:
            self.logger.log_organization_action(
                request=None,
                user=self.user,
                action="update",
                organization=org,
                updated_fields=["status"],
                bulk_operation=True,
                batch_id="batch_001",
            )

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete within reasonable time
        self.assertLess(
            execution_time, 1.0, "Bulk organization operations took too long"
        )
        self.assertEqual(mock_finalize_audit.call_count, 5)

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_organization_exchange_rate_comprehensive_tracking(
        self, mock_finalize_audit
    ):
        """Test comprehensive exchange rate audit tracking."""

        # Mock exchange rate
        mock_exchange_rate = Mock()
        mock_exchange_rate.pk = "rate-456"
        mock_exchange_rate.from_currency = "EUR"
        mock_exchange_rate.to_currency = "GBP"
        mock_exchange_rate.rate = 0.86
        mock_exchange_rate.organization = self.organization

        # Log exchange rate creation
        self.logger.log_organization_exchange_rate_action(
            request=None,
            user=self.user,
            action="create",
            organization=self.organization,
            exchange_rate=mock_exchange_rate,
        )

        # Verify exchange rate metadata
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        # Test standard exchange rate audit metadata fields
        self.assertIn("action", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("organization_title", metadata)
        self.assertIn("exchange_rate_id", metadata)
        self.assertIn("currency_code", metadata)
        self.assertIn("rate", metadata)
        self.assertEqual(metadata["action"], "create")
        self.assertEqual(metadata["exchange_rate_id"], "rate-456")
        self.assertEqual(metadata["rate"], "0.86")

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_organization_audit_with_workspace_relationships(self, mock_finalize_audit):
        """Test organization audit logging with workspace relationship tracking."""

        # Log organization action with workspace context
        self.logger.log_organization_action(
            request=None,
            user=self.user,
            action="update",
            organization=self.organization,
            updated_fields=["workspace_settings"],
        )

        # Verify workspace relationship is tracked
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args
        workspace_arg = call_args[0][4]  # workspace is the 5th argument
        metadata = call_args[0][2]  # metadata is the 3rd argument

        # Workspace should be derived from organization.workspace
        expected_workspace = getattr(self.organization, "workspace", None)
        self.assertEqual(workspace_arg, expected_workspace)
        self.assertIn("action", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("updated_fields", metadata)
        self.assertEqual(metadata["action"], "update")
        self.assertEqual(metadata["updated_fields"], ["workspace_settings"])

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_organization_audit_metadata_validation(self, mock_finalize_audit):
        """Test validation of organization audit metadata structure."""

        # Log organization action with standard parameters
        self.logger.log_organization_action(
            request=None,
            user=self.user,
            action="update",
            organization=self.organization,
            updated_fields=["title", "description"],
        )

        # Verify standard metadata structure
        mock_finalize_audit.assert_called_once()
        call_args = mock_finalize_audit.call_args[0]
        metadata = call_args[2]

        # Test standard audit metadata fields
        self.assertIn("action", metadata)
        self.assertIn("organization_id", metadata)
        self.assertIn("organization_title", metadata)
        self.assertIn("updater_id", metadata)
        self.assertIn("updater_email", metadata)
        self.assertIn("update_timestamp", metadata)
        self.assertIn("updated_fields", metadata)
        self.assertEqual(metadata["action"], "update")
        self.assertEqual(metadata["updated_fields"], ["title", "description"])
