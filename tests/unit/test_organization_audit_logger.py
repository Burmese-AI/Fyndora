"""Tests for OrganizationAuditLogger."""

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.loggers.organization_logger import OrganizationAuditLogger


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
        mock_crud_metadata.assert_called_once_with(self.mock_user, "create", updated_fields=[], soft_delete=False)
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation arguments
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(call_args[0], self.mock_user)  # user
        self.assertEqual(call_args[1], AuditActionType.ORGANIZATION_CREATED)  # action_type
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
            self.mock_user, "update", updated_fields=["title", "description"], soft_delete=False
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(call_args[1], AuditActionType.ORGANIZATION_UPDATED)  # action_type

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
        self.assertEqual(call_args[1], AuditActionType.ORGANIZATION_DELETED)  # action_type

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
            self.mock_user, "create", updated_fields=[], soft_delete=False, organization=self.mock_organization
        )

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1], AuditActionType.ORGANIZATION_EXCHANGE_RATE_CREATED  # action_type
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
        mock_crud_metadata.assert_called_once_with(self.mock_user, "update", updated_fields=["rate"], soft_delete=False, organization=self.mock_organization, old_rate=0.80, new_rate=0.85)
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1], AuditActionType.ORGANIZATION_EXCHANGE_RATE_UPDATED  # action_type
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
        mock_crud_metadata.assert_called_once_with(self.mock_user, "delete", updated_fields=[], soft_delete=False, organization=self.mock_organization)
        mock_finalize_audit.assert_called_once()

        # Verify audit log creation with correct action type
        call_args = mock_finalize_audit.call_args[0]  # positional arguments
        self.assertEqual(
            call_args[1], AuditActionType.ORGANIZATION_EXCHANGE_RATE_DELETED  # action_type
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

    @patch(
        "apps.auditlog.loggers.base_logger.BaseAuditLogger._validate_request_and_user"
    )
    def test_validation_methods_called(self, mock_validate_request_and_user):
        """Test that validation methods are called during logging."""
        with patch(
            "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
        ):
            with patch(
                "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
            ):
                with patch(
                    "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
                ):
                    self.logger.log_organization_action(
                        request=self.mock_request,
                        user=self.mock_user,
                        action="create",
                        organization=self.mock_organization,
                    )

        # Verify validation method was called
        mock_validate_request_and_user.assert_called_once_with(self.mock_request, self.mock_user)

    @patch(
        "apps.auditlog.loggers.organization_logger.OrganizationAuditLogger._finalize_and_create_audit"
    )
    def test_metadata_combination(self, mock_finalize_audit):
        """Test that metadata from different builders is properly combined."""
        with patch(
            "apps.auditlog.loggers.organization_logger.EntityMetadataBuilder.build_organization_metadata"
        ) as mock_org_meta:
            with patch(
                "apps.auditlog.loggers.organization_logger.UserActionMetadataBuilder.build_crud_action_metadata"
            ) as mock_crud_meta:
                # Setup return values
                mock_org_meta.return_value = {
                    "organization_id": "org-123",
                    "organization_title": "Test Org",
                }
                mock_crud_meta.return_value = {
                    "creator_id": "user-123",
                    "creation_timestamp": "2024-01-01T00:00:00Z",
                }

                self.logger.log_organization_action(
                    request=self.mock_request,
                    user=self.mock_user,
                    action="create",
                    organization=self.mock_organization,
                )

                # Verify combined metadata
                call_args = mock_finalize_audit.call_args[0]  # positional arguments
                metadata = call_args[2]  # metadata is the 3rd positional argument
                self.assertEqual(metadata["organization_id"], "org-123")
                self.assertEqual(metadata["organization_title"], "Test Org")
                self.assertEqual(metadata["creator_id"], "user-123")
                self.assertEqual(metadata["creation_timestamp"], "2024-01-01T00:00:00Z")

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
                self.assertEqual(metadata["rate"], "0.85")  # rate is converted to string
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
