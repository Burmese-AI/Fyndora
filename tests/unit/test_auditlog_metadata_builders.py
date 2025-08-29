"""Tests for metadata builders."""

from datetime import datetime, timezone as dt_timezone
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.auditlog.loggers.metadata_builders import (
    EntityMetadataBuilder,
    FileMetadataBuilder,
    UserActionMetadataBuilder,
    WorkflowMetadataBuilder,
)
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
    OrganizationFactory,
    TeamFactory,
    WorkspaceFactory,
)


class TestUserActionMetadataBuilder(TestCase):
    """Test cases for UserActionMetadataBuilder."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUserFactory(email="test@example.com")
        # Store the generated UUID as string for test assertions
        self.test_user_id = str(self.user.user_id)

    def test_build_user_action_metadata_without_timestamp(self):
        """Test build_user_action_metadata without timestamp."""
        metadata = UserActionMetadataBuilder.build_user_action_metadata(
            user=self.user, action_type="creator"
        )

        expected = {
            "creator_id": self.test_user_id,
            "creator_email": "test@example.com",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_user_action_metadata_with_timestamp(self, mock_now):
        """Test build_user_action_metadata with timestamp."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = UserActionMetadataBuilder.build_user_action_metadata(
            user=self.user, action_type="updater", timestamp_key="update_timestamp"
        )

        expected = {
            "updater_id": self.test_user_id,
            "updater_email": "test@example.com",
            "update_timestamp": "2024-01-01T12:00:00+00:00",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_crud_action_metadata_create(self, mock_now):
        """Test build_crud_action_metadata for create action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user, action="create"
        )

        expected = {
            "creator_id": self.test_user_id,
            "creator_email": "test@example.com",
            "creation_timestamp": "2024-01-01T12:00:00+00:00",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_crud_action_metadata_update(self, mock_now):
        """Test build_crud_action_metadata for update action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user, action="update", updated_fields=["title", "description"]
        )

        expected = {
            "updater_id": self.test_user_id,
            "updater_email": "test@example.com",
            "update_timestamp": "2024-01-01T12:00:00+00:00",
            "updated_fields": ["title", "description"],
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_crud_action_metadata_update_no_fields(self, mock_now):
        """Test build_crud_action_metadata for update action without fields."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user, action="update"
        )

        expected = {
            "updater_id": self.test_user_id,
            "updater_email": "test@example.com",
            "update_timestamp": "2024-01-01T12:00:00+00:00",
            "updated_fields": [],
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_crud_action_metadata_delete_soft(self, mock_now):
        """Test build_crud_action_metadata for soft delete action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user, action="delete", soft_delete=True
        )

        expected = {
            "deleter_id": self.test_user_id,
            "deleter_email": "test@example.com",
            "deletion_timestamp": "2024-01-01T12:00:00+00:00",
            "soft_delete": True,
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_crud_action_metadata_delete_hard(self, mock_now):
        """Test build_crud_action_metadata for hard delete action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user, action="delete", soft_delete=False
        )

        expected = {
            "deleter_id": self.test_user_id,
            "deleter_email": "test@example.com",
            "deletion_timestamp": "2024-01-01T12:00:00+00:00",
            "soft_delete": False,
        }
        self.assertEqual(metadata, expected)

    def test_build_crud_action_metadata_unknown_action(self):
        """Test build_crud_action_metadata for unknown action."""
        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user, action="unknown_action"
        )

        # Should return empty metadata for unknown actions
        self.assertEqual(metadata, {})

    def test_build_crud_action_metadata_with_kwargs(self):
        """Test build_crud_action_metadata with additional kwargs."""
        metadata = UserActionMetadataBuilder.build_crud_action_metadata(
            user=self.user,
            action="create",
            extra_field="extra_value",
            another_field=123,
        )

        # Should include basic create metadata, kwargs are ignored
        self.assertIn("creator_id", metadata)
        self.assertIn("creator_email", metadata)
        self.assertIn("creation_timestamp", metadata)
        self.assertNotIn("extra_field", metadata)
        self.assertNotIn("another_field", metadata)


class TestEntityMetadataBuilder(TestCase):
    """Test cases for EntityMetadataBuilder."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization = OrganizationFactory(
            title="Test Organization",
            status="active",
            description="Test organization description",
        )
        self.workspace = WorkspaceFactory(
            title="Test Workspace",
            description="Test workspace description",
            status="active",
            organization=self.organization,
        )
        self.team = TeamFactory(
            title="Test Team",
            description="Test team description",
            organization=self.organization,
        )
        self.entry = EntryFactory(
            description="Test entry description",
            status="draft",
            amount=100.50,
            entry_type="income",
            workspace=self.workspace,
            organization=self.organization,
        )

    def test_build_entity_metadata_with_defaults(self):
        """Test build_entity_metadata with default parameters."""
        mock_entity = Mock()
        mock_entity.__class__.__name__ = "TestEntity"
        mock_entity._meta = Mock()
        mock_entity._meta.pk = Mock()
        mock_entity._meta.pk.name = "id"
        mock_entity.id = "entity-123"
        mock_entity.title = "Test Entity Title"

        metadata = EntityMetadataBuilder.build_entity_metadata(mock_entity)

        expected = {
            "testentity_id": "entity-123",
            "testentity_title": "Test Entity Title",
        }
        self.assertEqual(metadata, expected)

    def test_build_entity_metadata_with_custom_fields(self):
        """Test build_entity_metadata with custom id and title fields."""
        mock_entity = Mock()
        mock_entity.__class__.__name__ = "CustomEntity"
        mock_entity.custom_id = "custom-456"
        mock_entity.name = "Custom Entity Name"

        metadata = EntityMetadataBuilder.build_entity_metadata(
            entity=mock_entity, id_field="custom_id", title_field="name"
        )

        expected = {
            "customentity_id": "custom-456",
            "customentity_name": "Custom Entity Name",
        }
        self.assertEqual(metadata, expected)

    def test_build_entity_metadata_missing_title_field(self):
        """Test build_entity_metadata when title field doesn't exist."""
        mock_entity = Mock()
        mock_entity.__class__.__name__ = "EntityNoTitle"
        mock_entity._meta = Mock()
        mock_entity._meta.pk = Mock()
        mock_entity._meta.pk.name = "pk"
        mock_entity.pk = "entity-789"
        # Remove title attribute to simulate missing field
        del mock_entity.title

        metadata = EntityMetadataBuilder.build_entity_metadata(mock_entity)

        expected = {
            "entitynotitle_id": "entity-789",
        }
        self.assertEqual(metadata, expected)

    def test_build_entity_metadata_none_entity(self):
        """Test build_entity_metadata with None entity."""
        metadata = EntityMetadataBuilder.build_entity_metadata(None)
        self.assertEqual(metadata, {})

    def test_build_organization_metadata(self):
        """Test build_organization_metadata with complete organization."""
        metadata = EntityMetadataBuilder.build_organization_metadata(self.organization)

        expected = {
            "organization_id": str(self.organization.organization_id),
            "organization_title": "Test Organization",
            "organization_status": "active",
            "organization_description": "Test organization description",
        }
        self.assertEqual(metadata, expected)

    def test_build_organization_metadata_minimal(self):
        """Test build_organization_metadata with minimal organization data."""
        minimal_org = Mock()
        minimal_org.organization_id = "minimal-org"
        minimal_org.title = "Minimal Org"
        minimal_org.status = None
        minimal_org.description = ""

        metadata = EntityMetadataBuilder.build_organization_metadata(minimal_org)

        expected = {
            "organization_id": "minimal-org",
            "organization_title": "Minimal Org",
            "organization_status": None,
            "organization_description": "",
        }
        self.assertEqual(metadata, expected)

    def test_build_organization_metadata_none(self):
        """Test build_organization_metadata with None organization."""
        metadata = EntityMetadataBuilder.build_organization_metadata(None)
        self.assertEqual(metadata, {})

    @patch("apps.auditlog.loggers.base_logger.BaseAuditLogger._safe_get_related_field")
    def test_build_workspace_metadata(self, mock_safe_get):
        """Test build_workspace_metadata with complete workspace."""
        # Mock the safe_get_related_field calls
        mock_safe_get.side_effect = [
            "org-123",  # organization.organization_id
            "Test Organization",  # organization.title
            "admin-123",  # workspace_admin.organization_member_id
            "admin@example.com",  # workspace_admin.user.email
            "reviewer-456",  # operations_reviewer.organization_member_id
            "reviewer@example.com",  # operations_reviewer.user.email
        ]

        metadata = EntityMetadataBuilder.build_workspace_metadata(self.workspace)

        expected = {
            "workspace_id": str(self.workspace.workspace_id),
            "workspace_title": "Test Workspace",
            "workspace_description": "Test workspace description",
            "workspace_status": "active",
            "organization_id": "org-123",
            "organization_title": "Test Organization",
            "workspace_admin_id": "admin-123",
            "workspace_admin_email": "admin@example.com",
            "workspace_reviewer_id": "reviewer-456",
            "workspace_reviewer_email": "reviewer@example.com",
        }
        self.assertEqual(metadata, expected)

    def test_build_workspace_metadata_none(self):
        """Test build_workspace_metadata with None workspace."""
        metadata = EntityMetadataBuilder.build_workspace_metadata(None)
        self.assertEqual(metadata, {})

    @patch("apps.auditlog.loggers.base_logger.BaseAuditLogger._safe_get_related_field")
    def test_build_team_metadata(self, mock_safe_get):
        """Test build_team_metadata with complete team."""
        # Mock the safe_get_related_field calls
        mock_safe_get.side_effect = [
            "org-123",  # organization.organization_id
            "Test Organization",  # organization.title
            "workspace-456",  # workspace.workspace_id
            "Test Workspace",  # workspace.title
            "coordinator-789",  # team_coordinator.organization_member_id
            "coordinator@example.com",  # team_coordinator.user.email
        ]

        metadata = EntityMetadataBuilder.build_team_metadata(self.team)

        expected = {
            "team_id": str(self.team.team_id),
            "team_title": "Test Team",
            "team_description": "Test team description",
            "organization_id": "org-123",
            "organization_title": "Test Organization",
            "workspace_id": "workspace-456",
            "workspace_title": "Test Workspace",
            "team_coordinator_id": "coordinator-789",
            "team_coordinator_email": "coordinator@example.com",
        }
        self.assertEqual(metadata, expected)

    def test_build_team_metadata_none(self):
        """Test build_team_metadata with None team."""
        metadata = EntityMetadataBuilder.build_team_metadata(None)
        self.assertEqual(metadata, {})

    @patch("apps.auditlog.loggers.base_logger.BaseAuditLogger._safe_get_related_field")
    def test_build_entry_metadata(self, mock_safe_get):
        """Test build_entry_metadata with complete entry."""
        # Mock the safe_get_related_field calls
        mock_safe_get.side_effect = [
            "workspace-456",  # workspace.workspace_id
            "Test Workspace",  # workspace.title
            "org-123",  # organization.organization_id
            "Test Organization",  # organization.title
            "submitter-101",  # submitter.organization_member_id
            "submitter@example.com",  # submitter.user.email
        ]

        metadata = EntityMetadataBuilder.build_entry_metadata(self.entry)

        expected = {
            "entry_id": str(self.entry.entry_id),
            "entry_description": "Test entry description",
            "entry_status": "draft",
            "entry_amount": "100.5",
            "entry_currency": str(self.entry.currency),
            "entry_type": "income",
            "workspace_id": "workspace-456",
            "workspace_title": "Test Workspace",
            "organization_id": "org-123",
            "organization_title": "Test Organization",
            "submitter_id": "submitter-101",
            "submitter_email": "submitter@example.com",
        }
        self.assertEqual(metadata, expected)

    def test_build_entry_metadata_none_amount(self):
        """Test build_entry_metadata with None amount."""
        entry_no_amount = Mock()
        entry_no_amount.entry_id = "entry-no-amount"
        entry_no_amount.description = "Entry without amount"
        entry_no_amount.status = "draft"
        entry_no_amount.amount = None
        entry_no_amount.currency = "USD"
        entry_no_amount.entry_type = "income"

        with patch(
            "apps.auditlog.loggers.base_logger.BaseAuditLogger._safe_get_related_field"
        ) as mock_safe_get:
            mock_safe_get.return_value = None
            metadata = EntityMetadataBuilder.build_entry_metadata(entry_no_amount)

        self.assertIsNone(metadata["entry_amount"])

    def test_build_entry_metadata_none(self):
        """Test build_entry_metadata with None entry."""
        metadata = EntityMetadataBuilder.build_entry_metadata(None)
        self.assertEqual(metadata, {})


class TestWorkflowMetadataBuilder(TestCase):
    """Test cases for WorkflowMetadataBuilder."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUserFactory(email="workflow@example.com")

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_submit(self, mock_now):
        """Test build_workflow_metadata for submit action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user,
            action="submit",
            workflow_stage="review",
            notes="Submitting for review",
        )

        expected = {
            "workflow_action": True,
            "workflow_stage": "review",
            "stage_timestamp": "2024-01-01T12:00:00+00:00",
            "submitter_id": str(self.user.user_id),
            "submitter_email": "workflow@example.com",
            "submission_timestamp": "2024-01-01T12:00:00+00:00",
            "submission_notes": "Submitting for review",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_resubmit(self, mock_now):
        """Test build_workflow_metadata for resubmit action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user, action="resubmit", notes="Resubmitting with corrections"
        )

        expected = {
            "workflow_action": True,
            "submitter_id": str(self.user.user_id),
            "submitter_email": "workflow@example.com",
            "submission_timestamp": "2024-01-01T12:00:00+00:00",
            "submission_notes": "Resubmitting with corrections",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_approve(self, mock_now):
        """Test build_workflow_metadata for approve action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user,
            action="approve",
            workflow_stage="approved",
            notes="Approved with conditions",
        )

        expected = {
            "workflow_action": True,
            "workflow_stage": "approved",
            "stage_timestamp": "2024-01-01T12:00:00+00:00",
            "reviewer_id": str(self.user.user_id),
            "reviewer_email": "workflow@example.com",
            "review_timestamp": "2024-01-01T12:00:00+00:00",
            "review_notes": "Approved with conditions",
            "review_decision": "approve",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_reject(self, mock_now):
        """Test build_workflow_metadata for reject action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user,
            action="reject",
            notes="Rejected due to insufficient documentation",
        )

        expected = {
            "workflow_action": True,
            "reviewer_id": str(self.user.user_id),
            "reviewer_email": "workflow@example.com",
            "review_timestamp": "2024-01-01T12:00:00+00:00",
            "review_notes": "Rejected due to insufficient documentation",
            "review_decision": "reject",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_return(self, mock_now):
        """Test build_workflow_metadata for return action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user, action="return", notes="Returned for additional information"
        )

        expected = {
            "workflow_action": True,
            "reviewer_id": str(self.user.user_id),
            "reviewer_email": "workflow@example.com",
            "review_timestamp": "2024-01-01T12:00:00+00:00",
            "review_notes": "Returned for additional information",
            "review_decision": "return",
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_withdraw(self, mock_now):
        """Test build_workflow_metadata for withdraw action."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user, action="withdraw", reason="No longer needed"
        )

        expected = {
            "workflow_action": True,
            "withdrawer_id": str(self.user.user_id),
            "withdrawer_email": "workflow@example.com",
            "withdrawal_timestamp": "2024-01-01T12:00:00+00:00",
            "withdrawal_reason": "No longer needed",
        }
        self.assertEqual(metadata, expected)

    def test_build_workflow_metadata_unknown_action(self):
        """Test build_workflow_metadata for unknown action."""
        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user, action="unknown_action"
        )

        expected = {
            "workflow_action": True,
        }
        self.assertEqual(metadata, expected)

    @patch("django.utils.timezone.now")
    def test_build_workflow_metadata_with_kwargs(self, mock_now):
        """Test build_workflow_metadata with additional kwargs."""
        mock_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = mock_datetime

        metadata = WorkflowMetadataBuilder.build_workflow_metadata(
            user=self.user,
            action="approve",
            extra_field="extra_value",
            another_field=123,
        )

        # Should include basic approve metadata, kwargs are ignored
        self.assertIn("workflow_action", metadata)
        self.assertIn("reviewer_id", metadata)
        self.assertIn("review_decision", metadata)
        self.assertNotIn("extra_field", metadata)
        self.assertNotIn("another_field", metadata)


class TestFileMetadataBuilder(TestCase):
    """Test cases for FileMetadataBuilder."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_file = Mock()
        self.mock_file.name = "test_document.pdf"
        self.mock_file.size = 2048
        self.mock_file.content_type = "application/pdf"

    def test_build_file_metadata_upload(self):
        """Test build_file_metadata for upload operation."""
        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=self.mock_file,
            operation="upload",
            file_category="document",
            source="web_interface",
            purpose="expense_receipt",
        )

        expected = {
            "file_name": "test_document.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "operation": "upload",
            "file_category": "document",
            "upload_source": "web_interface",
            "upload_purpose": "expense_receipt",
        }
        self.assertEqual(metadata, expected)

    def test_build_file_metadata_upload_defaults(self):
        """Test build_file_metadata for upload with default values."""
        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=self.mock_file, operation="upload"
        )

        expected = {
            "file_name": "test_document.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "operation": "upload",
            "file_category": "general",
            "upload_source": "web_interface",
            "upload_purpose": "",
        }
        self.assertEqual(metadata, expected)

    def test_build_file_metadata_download(self):
        """Test build_file_metadata for download operation."""
        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=self.mock_file,
            operation="download",
            file_category="attachment",
            reason="audit_review",
        )

        expected = {
            "file_name": "test_document.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "operation": "download",
            "file_category": "attachment",
            "download_reason": "audit_review",
        }
        self.assertEqual(metadata, expected)

    def test_build_file_metadata_delete(self):
        """Test build_file_metadata for delete operation."""
        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=self.mock_file, operation="delete", file_category="temporary"
        )

        expected = {
            "file_name": "test_document.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "operation": "delete",
            "file_category": "temporary",
        }
        self.assertEqual(metadata, expected)

    def test_build_file_metadata_missing_attributes(self):
        """Test build_file_metadata with file object missing attributes."""
        minimal_file = Mock()
        # Only has name, missing size and content_type
        minimal_file.name = "minimal.txt"
        # Remove size and content_type attributes to trigger getattr defaults
        del minimal_file.size
        del minimal_file.content_type

        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=minimal_file, operation="upload"
        )

        expected = {
            "file_name": "minimal.txt",
            "file_size": 0,
            "file_type": "unknown",
            "operation": "upload",
            "file_category": "general",
            "upload_source": "web_interface",
            "upload_purpose": "",
        }
        self.assertEqual(metadata, expected)

    def test_build_file_metadata_no_name(self):
        """Test build_file_metadata with file object without name."""
        no_name_file = Mock()
        no_name_file.size = 1024
        no_name_file.content_type = "text/plain"
        # Remove name attribute to trigger getattr default
        del no_name_file.name

        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=no_name_file, operation="upload"
        )

        expected = {
            "file_name": "unknown",
            "file_size": 1024,
            "file_type": "text/plain",
            "operation": "upload",
            "file_category": "general",
            "upload_source": "web_interface",
            "upload_purpose": "",
        }
        self.assertEqual(metadata, expected)

    def test_build_file_metadata_with_extra_kwargs(self):
        """Test build_file_metadata with extra kwargs for unknown operation."""
        metadata = FileMetadataBuilder.build_file_metadata(
            file_obj=self.mock_file,
            operation="unknown_operation",
            extra_field="extra_value",
            another_field=456,
        )

        # Should include basic metadata but not extra kwargs
        expected = {
            "file_name": "test_document.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "operation": "unknown_operation",
            "file_category": "general",
        }
        self.assertEqual(metadata, expected)


class TestMetadataBuildersEdgeCases(TestCase):
    """Test edge cases and error conditions for all metadata builders."""

    def test_user_action_metadata_with_none_user(self):
        """Test UserActionMetadataBuilder with None user."""
        with self.assertRaises(AttributeError):
            UserActionMetadataBuilder.build_user_action_metadata(
                user=None, action_type="creator"
            )

    def test_crud_action_metadata_with_none_user(self):
        """Test UserActionMetadataBuilder.build_crud_action_metadata with None user."""
        with self.assertRaises(AttributeError):
            UserActionMetadataBuilder.build_crud_action_metadata(
                user=None, action="create"
            )

    def test_workflow_metadata_with_none_user(self):
        """Test WorkflowMetadataBuilder with None user."""
        with self.assertRaises(AttributeError):
            WorkflowMetadataBuilder.build_workflow_metadata(user=None, action="submit")

    def test_entity_metadata_with_none_entity(self):
        """Test EntityMetadataBuilder with None entity."""
        result = EntityMetadataBuilder.build_entity_metadata(None)
        self.assertEqual(result, {})

    def test_organization_metadata_with_none_organization(self):
        """Test EntityMetadataBuilder.build_organization_metadata with None."""
        result = EntityMetadataBuilder.build_organization_metadata(None)
        self.assertEqual(result, {})

    def test_workspace_metadata_with_none_workspace(self):
        """Test EntityMetadataBuilder.build_workspace_metadata with None."""
        result = EntityMetadataBuilder.build_workspace_metadata(None)
        self.assertEqual(result, {})

    def test_team_metadata_with_none_team(self):
        """Test EntityMetadataBuilder.build_team_metadata with None."""
        result = EntityMetadataBuilder.build_team_metadata(None)
        self.assertEqual(result, {})

    def test_entry_metadata_with_none_entry(self):
        """Test EntityMetadataBuilder.build_entry_metadata with None."""
        result = EntityMetadataBuilder.build_entry_metadata(None)
        self.assertEqual(result, {})

    def test_file_metadata_with_none_file(self):
        """Test FileMetadataBuilder with None file object."""
        result = FileMetadataBuilder.build_file_metadata(
            file_obj=None, operation="upload"
        )
        expected = {
            "file_name": "unknown",
            "file_size": 0,
            "file_type": "unknown",
            "operation": "upload",
            "file_category": "general",
            "upload_source": "web_interface",
            "upload_purpose": "",
        }
        self.assertEqual(result, expected)

    def test_entity_metadata_with_entity_no_meta(self):
        """Test EntityMetadataBuilder with entity missing _meta attribute."""
        mock_entity = Mock()
        mock_entity.__class__.__name__ = "TestEntity"
        # Remove _meta attribute to trigger AttributeError
        del mock_entity._meta

        with self.assertRaises(AttributeError):
            EntityMetadataBuilder.build_entity_metadata(mock_entity)

    def test_entity_metadata_with_custom_id_field_missing(self):
        """Test EntityMetadataBuilder with missing custom id field."""
        mock_entity = Mock()
        mock_entity.__class__.__name__ = "TestEntity"
        mock_entity.title = "Test Title"
        # Create and then delete the custom_id_field attribute to ensure it doesn't exist
        mock_entity.custom_id_field = "temp"
        del mock_entity.custom_id_field

        with self.assertRaises(AttributeError):
            EntityMetadataBuilder.build_entity_metadata(
                entity=mock_entity, id_field="custom_id_field"
            )

    def test_organization_metadata_missing_required_fields(self):
        """Test EntityMetadataBuilder.build_organization_metadata with missing required fields."""
        incomplete_org = Mock()
        # Remove required attributes to trigger AttributeError
        del incomplete_org.organization_id
        del incomplete_org.title

        with self.assertRaises(AttributeError):
            EntityMetadataBuilder.build_organization_metadata(incomplete_org)

    def test_workspace_metadata_missing_required_fields(self):
        """Test EntityMetadataBuilder.build_workspace_metadata with missing required fields."""
        incomplete_workspace = Mock()
        # Remove required attributes to trigger AttributeError
        del incomplete_workspace.workspace_id
        del incomplete_workspace.title

        with self.assertRaises(AttributeError):
            EntityMetadataBuilder.build_workspace_metadata(incomplete_workspace)

    def test_team_metadata_missing_required_fields(self):
        """Test EntityMetadataBuilder.build_team_metadata with missing required fields."""
        incomplete_team = Mock()
        # Remove required attributes to trigger AttributeError
        del incomplete_team.team_id
        del incomplete_team.title

        with self.assertRaises(AttributeError):
            EntityMetadataBuilder.build_team_metadata(incomplete_team)

    def test_entry_metadata_missing_required_fields(self):
        """Test EntityMetadataBuilder.build_entry_metadata with missing required fields."""
        incomplete_entry = Mock()
        # Remove required attributes to trigger AttributeError
        del incomplete_entry.entry_id

        with self.assertRaises(AttributeError):
            EntityMetadataBuilder.build_entry_metadata(incomplete_entry)
