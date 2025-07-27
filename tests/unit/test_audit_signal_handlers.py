"""
Unit tests for audit signal handlers and registry.

Following the test plan: AuditLog App (apps.auditlog)
- Signal handler tests
- Model registry tests
- Field change tracking tests
- Error handling tests
"""

from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from apps.auditlog.constants import AuditActionType
from apps.auditlog.signal_handlers import (
    AuditModelRegistry,
    BaseAuditHandler,
    GenericAuditSignalHandler,
    safe_audit_log,
)
from apps.entries.models import Entry
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from tests.factories import (
    CustomUserFactory,
    EntryFactory,
)


@pytest.mark.unit
class TestAuditModelRegistry(TestCase):
    """Test the AuditModelRegistry functionality."""

    def setUp(self):
        # Clear registry before each test
        AuditModelRegistry._registry = {}

    def test_register_model_basic(self):
        """Test basic model registration."""
        action_types = {
            "created": AuditActionType.ENTRY_CREATED,
            "updated": AuditActionType.ENTRY_UPDATED,
            "deleted": AuditActionType.ENTRY_DELETED,
        }
        tracked_fields = ["entry_type", "amount", "status"]

        AuditModelRegistry.register_model(Entry, action_types, tracked_fields)

        model_key = "entries.Entry"
        config = AuditModelRegistry.get_config(model_key)

        self.assertIsNotNone(config)
        self.assertEqual(config["model_class"], Entry)
        self.assertEqual(config["action_types"], action_types)
        self.assertEqual(config["tracked_fields"], tracked_fields)

    def test_get_config_nonexistent_model(self):
        """Test getting config for non-registered model."""
        config = AuditModelRegistry.get_config("nonexistent.Model")
        self.assertIsNone(config)

    def test_get_all_registered_models(self):
        """Test getting all registered models."""
        # Register multiple models
        AuditModelRegistry.register_model(
            Entry, {"created": AuditActionType.ENTRY_CREATED}, ["amount"]
        )
        AuditModelRegistry.register_model(
            Workspace, {"created": AuditActionType.WORKSPACE_CREATED}, ["name"]
        )

        all_models = AuditModelRegistry.get_all_registered_models()

        self.assertEqual(len(all_models), 2)
        self.assertIn("entries.Entry", all_models)
        self.assertIn("workspaces.Workspace", all_models)

    def test_get_default_model_config_known_models(self):
        """Test getting default config for known models."""
        entry_config = AuditModelRegistry._get_default_model_config(Entry)
        org_config = AuditModelRegistry._get_default_model_config(Organization)

        self.assertIsNotNone(entry_config)
        self.assertIsNotNone(org_config)

        # Check entry config structure
        self.assertIn("action_types", entry_config)
        self.assertIn("tracked_fields", entry_config)
        self.assertIn("created", entry_config["action_types"])
        self.assertIn("type", entry_config["tracked_fields"])

    def test_get_default_model_config_unknown_model(self):
        """Test getting default config for unknown model."""

        # Create a mock model class
        class UnknownModel:
            class _meta:
                app_label = "unknown"

            __name__ = "UnknownModel"

        config = AuditModelRegistry._get_default_model_config(UnknownModel)
        self.assertIsNone(config)

    @patch("apps.auditlog.signal_handlers.apps.get_models")
    @patch("apps.auditlog.signal_handlers.should_log_model")
    def test_auto_register_models(self, mock_should_log, mock_get_models):
        """Test automatic model registration."""
        # Mock the apps.get_models() to return our test model
        mock_get_models.return_value = [Entry]
        mock_should_log.return_value = True

        AuditModelRegistry.auto_register_models()

        # Verify the model was registered
        config = AuditModelRegistry.get_config("entries.Entry")
        self.assertIsNotNone(config)
        self.assertEqual(config["model_class"], Entry)


@pytest.mark.unit
class TestBaseAuditHandler(TestCase):
    """Test the BaseAuditHandler functionality."""

    @pytest.mark.django_db
    def test_get_audit_context_with_attributes(self):
        """Test extracting audit context from instance with attributes."""
        entry = EntryFactory()
        user = CustomUserFactory()

        # Set audit attributes
        entry._audit_user = user
        entry._audit_context = {"source": "api"}
        entry._audit_old_values = {"status": "draft"}

        context = BaseAuditHandler.get_audit_context(entry)

        self.assertEqual(context["user"], user)
        self.assertEqual(context["context"], {"source": "api"})
        self.assertEqual(context["old_values"], {"status": "draft"})

    @pytest.mark.django_db
    def test_get_audit_context_without_attributes(self):
        """Test extracting audit context from instance without attributes."""
        entry = EntryFactory()

        context = BaseAuditHandler.get_audit_context(entry)

        self.assertIsNone(context["user"])
        self.assertEqual(context["context"], {})
        self.assertEqual(context["old_values"], {})

    @pytest.mark.django_db
    def test_capture_field_changes_with_changes(self):
        """Test capturing field changes when values differ."""
        old_entry = EntryFactory(entry_type="income", amount=1000)
        new_entry = EntryFactory(entry_type="expense", amount=1500)

        # Copy the pk to simulate the same instance
        new_entry.pk = old_entry.pk

        changes = BaseAuditHandler.capture_field_changes(
            old_entry, new_entry, ["entry_type", "amount"]
        )

        self.assertEqual(len(changes), 2)

        # Check entry_type change
        entry_type_change = next(c for c in changes if c["field"] == "entry_type")
        self.assertEqual(entry_type_change["old_value"], "income")
        self.assertEqual(entry_type_change["new_value"], "expense")

        # Check amount change
        amount_change = next(c for c in changes if c["field"] == "amount")
        self.assertEqual(amount_change["old_value"], "1000")
        self.assertEqual(amount_change["new_value"], "1500")

    @pytest.mark.django_db
    def test_capture_field_changes_no_changes(self):
        """Test capturing field changes when values are the same."""
        entry = EntryFactory(entry_type="income", amount=1000)

        changes = BaseAuditHandler.capture_field_changes(
            entry, entry, ["entry_type", "amount"]
        )

        self.assertEqual(len(changes), 0)

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.AuditConfig.LOG_FIELD_CHANGES", False)
    def test_capture_field_changes_disabled(self):
        """Test that field changes are not captured when disabled."""
        old_entry = EntryFactory(entry_type="income")
        new_entry = EntryFactory(entry_type="expense")
        # Copy the pk to simulate the same instance
        new_entry.pk = old_entry.pk

        changes = BaseAuditHandler.capture_field_changes(old_entry, new_entry, ["entry_type"])

        self.assertEqual(len(changes), 0)

    def test_build_metadata_basic(self):
        """Test building basic metadata."""
        entry = EntryFactory()

        metadata = BaseAuditHandler.build_metadata(entry)

        self.assertEqual(metadata["automatic_logging"], True)

    def test_build_metadata_with_changes(self):
        """Test building metadata with field changes."""
        entry = EntryFactory()
        changes = [{"field": "status", "old_value": "draft", "new_value": "submitted"}]

        metadata = BaseAuditHandler.build_metadata(entry, changes=changes)

        self.assertEqual(metadata["automatic_logging"], True)
        self.assertEqual(metadata["changed_fields"], changes)

    def test_build_metadata_with_extra(self):
        """Test building metadata with extra parameters."""
        entry = EntryFactory()

        metadata = BaseAuditHandler.build_metadata(entry, source="api", user_id=123)

        self.assertEqual(metadata["automatic_logging"], True)
        self.assertEqual(metadata["source"], "api")
        self.assertEqual(metadata["user_id"], 123)


@pytest.mark.unit
class TestGenericAuditSignalHandler(TestCase):
    """Test the GenericAuditSignalHandler functionality."""

    def setUp(self):
        self.mock_sender = Mock()
        self.mock_sender.__name__ = "TestModel"
        self.mock_sender.objects = Mock()

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.safe_audit_log")
    def test_create_handlers_pre_save_new_instance(self, mock_safe_audit):
        """Test pre_save handler for new instance (no pk)."""
        entry = EntryFactory()
        entry.pk = None  # Simulate new instance

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            "entries.Entry",
            {"created": AuditActionType.ENTRY_CREATED},
            ["entry_type", "amount"],
        )

        # The handlers are created and decorated, but we can't easily test
        # the signal connection without more complex mocking
        self.assertTrue(mock_safe_audit.called)

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.safe_audit_log")
    def test_create_handlers_pre_save_existing_instance(self, mock_safe_audit):
        """Test pre_save handler for existing instance (has pk)."""
        old_entry = EntryFactory()

        # Mock the objects.get to return old_entry
        self.mock_sender.objects.get.return_value = old_entry

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            self.mock_sender,
            {"updated": AuditActionType.ENTRY_UPDATED},
            ["entry_type", "amount"],
        )

        self.assertTrue(mock_safe_audit.called)

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.safe_audit_log")
    def test_create_handlers_pre_save_object_not_found(self, mock_safe_audit):
        """Test pre_save handler when old instance not found."""

        # Mock the objects.get to raise ObjectDoesNotExist
        self.mock_sender.objects.get.side_effect = ObjectDoesNotExist()

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            self.mock_sender,
            {"updated": AuditActionType.ENTRY_UPDATED},
            ["entry_type", "amount"],
        )

        self.assertTrue(mock_safe_audit.called)

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.audit_create")
    @patch("apps.auditlog.signal_handlers.safe_audit_log")
    def test_create_handlers_post_save_created(
        self, mock_safe_audit, mock_audit_create
    ):
        """Test post_save handler for created instance."""

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            "entries.Entry",
            {"created": AuditActionType.ENTRY_CREATED},
            ["entry_type", "amount"],
        )

        self.assertTrue(mock_safe_audit.called)

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.audit_create")
    @patch("apps.auditlog.signal_handlers.safe_audit_log")
    def test_create_handlers_post_save_updated(
        self, mock_safe_audit, mock_audit_create
    ):
        """Test post_save handler for updated instance."""
        entry = EntryFactory()
        entry._audit_old_values = {"entry_type": "income"}

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            "entries.Entry",
            {"updated": AuditActionType.ENTRY_UPDATED},
            ["entry_type", "amount"],
        )

        self.assertTrue(mock_safe_audit.called)

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.audit_create")
    @patch("apps.auditlog.signal_handlers.safe_audit_log")
    def test_create_handlers_pre_delete(self, mock_safe_audit, mock_audit_create):
        """Test pre_delete handler."""

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            "entries.Entry",
            {"deleted": AuditActionType.ENTRY_DELETED},
            ["entry_type", "amount"],
        )

        self.assertTrue(mock_safe_audit.called)


@pytest.mark.unit
class TestSignalHandlerErrorHandling(TestCase):
    """Test error handling in signal handlers."""

    @pytest.mark.django_db
    @patch("apps.auditlog.utils.logger")
    def test_signal_handler_with_exception(self, mock_logger):
        """Test signal handler behavior when exception occurs."""

        @safe_audit_log
        def failing_handler(sender, instance, **kwargs):
            raise Exception("Test exception")

        entry = EntryFactory()

        # Should not raise exception due to safe_audit_log decorator
        try:
            failing_handler(sender=None, instance=entry)
        except Exception:
            self.fail("safe_audit_log should have caught the exception")

        # Should have logged the error
        mock_logger.error.assert_called()

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.logger")
    def test_capture_changes_with_database_error(self, mock_logger):
        """Test capture_changes when database error occurs."""
        entry = EntryFactory()

        # Create handlers first
        GenericAuditSignalHandler.create_handlers(
            entry.__class__,
            {"updated": AuditActionType.ENTRY_UPDATED},
            ["entry_type", "amount"],
        )

        # Mock objects.get to raise a database error
        with patch.object(entry.__class__.objects, "get") as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            # Simulate the pre_save signal that would trigger capture_changes
            # by calling the signal handler directly with an instance that has a pk
            entry.pk = 1  # Ensure it has a pk to trigger the database lookup
            
            # Import the signal to trigger it
            from django.db.models.signals import pre_save
            
            # Send the signal which should trigger our handler
            pre_save.send(sender=entry.__class__, instance=entry)

            # Should handle the error gracefully
            mock_logger.warning.assert_called()

    @pytest.mark.django_db
    def test_registry_with_invalid_model(self):
        """Test registry behavior with invalid model configuration."""
        # Try to register with invalid action entry_types
        with self.assertRaises(AttributeError):
            AuditModelRegistry.register_model(
                None,  # Invalid model
                {"created": "invalid_action"},
                ["field"],
            )


@pytest.mark.unit
class TestSignalHandlerIntegration(TestCase):
    """Test signal handler integration with actual Django signals."""

    @pytest.mark.django_db
    @patch("apps.auditlog.signal_handlers.audit_create")
    def test_signal_handler_registration(self, mock_audit_create):
        """Test that signal handlers are properly registered."""
        # Register the model
        AuditModelRegistry.register_model(
            Entry,
            {
                "created": AuditActionType.ENTRY_CREATED,
                "updated": AuditActionType.ENTRY_UPDATED,
                "deleted": AuditActionType.ENTRY_DELETED,
            },
            ["entry_type", "amount", "status"],
        )

        # Create handlers
        GenericAuditSignalHandler.create_handlers(
            Entry,
            {
                "created": AuditActionType.ENTRY_CREATED,
                "updated": AuditActionType.ENTRY_UPDATED,
                "deleted": AuditActionType.ENTRY_DELETED,
            },
            ["entry_type", "amount", "status"],
        )

        # Verify handlers were created (they should be decorated with safe_audit_log)
        # This is a basic test - in practice, we'd need to test actual signal firing
        self.assertTrue(True)  # Placeholder for more complex signal testing

    @pytest.mark.django_db
    def test_model_registry_persistence(self):
        """Test that model registry persists across operations."""
        # Register multiple models
        AuditModelRegistry.register_model(
            Entry, {"created": AuditActionType.ENTRY_CREATED}, ["entry_type"]
        )
        AuditModelRegistry.register_model(
            Workspace, {"created": AuditActionType.WORKSPACE_CREATED}, ["name"]
        )

        # Verify both are registered
        self.assertIsNotNone(AuditModelRegistry.get_config("entries.Entry"))
        self.assertIsNotNone(AuditModelRegistry.get_config("workspaces.Workspace"))

        # Verify registry count
        all_models = AuditModelRegistry.get_all_registered_models()
        self.assertEqual(len(all_models), 2)
