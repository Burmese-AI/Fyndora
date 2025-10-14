"""
Signal handlers for automatic audit logging.
"""

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from apps.auditlog.constants import AuditActionType
from apps.auditlog.services import audit_create
from apps.auditlog.loggers.metadata_builders import (
    EntityMetadataBuilder,
    UserActionMetadataBuilder,
)

from .config import AuditConfig
from .utils import safe_audit_log, should_log_model

logger = logging.getLogger(__name__)


class AuditModelRegistry:
    """Registry for managing audit configurations for different models."""

    _registry: Dict[str, Dict] = {}

    @classmethod
    def register_model(
        cls, model_class, action_types: Dict[str, str], tracked_fields: List[str]
    ):
        """Register a model for audit logging with its configuration."""
        model_key = f"{model_class._meta.app_label}.{model_class.__name__}"
        cls._registry[model_key] = {
            "model_class": model_class,
            "action_types": action_types,
            "tracked_fields": tracked_fields,
        }
        logger.info(f"Registered audit logging for model: {model_key}")

    @classmethod
    def get_config(cls, model_key: str) -> Optional[Dict]:
        """Get audit configuration for a model."""
        return cls._registry.get(model_key)

    @classmethod
    def get_all_registered_models(cls) -> Dict[str, Dict]:
        """Get all registered models and their configurations."""
        return cls._registry.copy()

    @classmethod
    def auto_register_models(cls):
        """Automatically register all models that should be logged."""
        for model in apps.get_models():
            if should_log_model(model):
                # Get default configuration for the model
                config = cls._get_default_model_config(model)
                if config:
                    cls.register_model(
                        model, config["action_types"], config["tracked_fields"]
                    )

    @classmethod
    def _get_default_model_config(cls, model_class) -> Optional[Dict]:
        """Get default audit configuration for a model based on its type."""
        app_label = model_class._meta.app_label
        model_name = model_class.__name__

        # Define default configurations for known models
        default_configs = {
            "organizations.Organization": {
                "action_types": {
                    "created": AuditActionType.ORGANIZATION_CREATED,
                    "updated": AuditActionType.ORGANIZATION_UPDATED,
                    "deleted": AuditActionType.ORGANIZATION_DELETED,
                    "status_changed": AuditActionType.ORGANIZATION_STATUS_CHANGED,
                },
                "tracked_fields": ["title", "status", "description"],
            },
            "workspaces.Workspace": {
                "action_types": {
                    "created": AuditActionType.WORKSPACE_CREATED,
                    "updated": AuditActionType.WORKSPACE_UPDATED,
                    "deleted": AuditActionType.WORKSPACE_DELETED,
                    "status_changed": AuditActionType.WORKSPACE_STATUS_CHANGED,
                },
                "tracked_fields": ["title", "description", "status"],
            },
            "entries.Entry": {
                "action_types": {
                    "created": AuditActionType.ENTRY_CREATED,
                    "updated": AuditActionType.ENTRY_UPDATED,
                    "deleted": AuditActionType.ENTRY_DELETED,
                    "status_changed": AuditActionType.ENTRY_STATUS_CHANGED,
                },
                "tracked_fields": ["type", "amount", "status"],
            },
            "teams.Team": {
                "action_types": {
                    "created": AuditActionType.TEAM_CREATED,
                    "updated": AuditActionType.TEAM_UPDATED,
                    "deleted": AuditActionType.TEAM_DELETED,
                },
                "tracked_fields": ["title", "description"],
            },
            "remittance.Remittance": {
                "action_types": {
                    "created": AuditActionType.REMITTANCE_CREATED,
                    "updated": AuditActionType.REMITTANCE_UPDATED,
                    "deleted": AuditActionType.REMITTANCE_DELETED,
                    "status_changed": AuditActionType.REMITTANCE_STATUS_CHANGED,
                },
                "tracked_fields": ["amount", "status", "type"],
            },
            "invitations.Invitation": {
                "action_types": {
                    "created": AuditActionType.INVITATION_SENT,
                    "updated": AuditActionType.INVITATION_RESENT,
                    "deleted": AuditActionType.INVITATION_CANCELED,
                },
                "tracked_fields": ["email", "status", "role"],
            },
            "teams.TeamMember": {
                "action_types": {
                    "created": AuditActionType.TEAM_MEMBER_ADDED,
                    "updated": AuditActionType.TEAM_MEMBER_ROLE_CHANGED,
                    "deleted": AuditActionType.TEAM_MEMBER_REMOVED,
                },
                "tracked_fields": ["role", "deleted_at"],
            },
            "accounts.CustomUser": {
                "action_types": {
                    "created": AuditActionType.USER_CREATED,
                    "updated": AuditActionType.USER_PROFILE_UPDATED,
                    "deleted": AuditActionType.USER_DELETED,
                },
                "tracked_fields": [
                    "email",
                    "username",
                    "status",
                    "is_active",
                    "is_staff",
                ],
            },
            "organizations.OrganizationMember": {
                "action_types": {
                    "created": AuditActionType.ORGANIZATION_MEMBER_ADDED,
                    "updated": AuditActionType.ORGANIZATION_MEMBER_UPDATED,
                    "deleted": AuditActionType.ORGANIZATION_MEMBER_REMOVED,
                },
                "tracked_fields": ["is_active"],
            },
            "workspaces.WorkspaceTeam": {
                "action_types": {
                    "created": AuditActionType.WORKSPACE_TEAM_ADDED,
                    "updated": AuditActionType.WORKSPACE_TEAM_UPDATED,
                    "deleted": AuditActionType.WORKSPACE_TEAM_REMOVED,
                },
                "tracked_fields": ["custom_remittance_rate"],
            },
            "attachments.Attachment": {
                "action_types": {
                    "created": AuditActionType.FILE_UPLOADED,
                    "deleted": AuditActionType.FILE_DELETED,
                },
                "tracked_fields": ["file_url", "file_type"],
            },
            "currencies.Currency": {
                "action_types": {
                    "created": AuditActionType.CURRENCY_ADDED,
                    "updated": AuditActionType.CURRENCY_UPDATED,
                    "deleted": AuditActionType.CURRENCY_REMOVED,
                },
                "tracked_fields": ["code", "name"],
            },
            "organizations.OrganizationExchangeRate": {
                "action_types": {
                    "created": AuditActionType.ORGANIZATION_EXCHANGE_RATE_CREATED,
                    "updated": AuditActionType.ORGANIZATION_EXCHANGE_RATE_UPDATED,
                    "deleted": AuditActionType.ORGANIZATION_EXCHANGE_RATE_DELETED,
                },
                "tracked_fields": ["rate", "effective_date", "note", "deleted_at"],
            },
            "workspaces.WorkspaceExchangeRate": {
                "action_types": {
                    "created": AuditActionType.WORKSPACE_EXCHANGE_RATE_CREATED,
                    "updated": AuditActionType.WORKSPACE_EXCHANGE_RATE_UPDATED,
                    "deleted": AuditActionType.WORKSPACE_EXCHANGE_RATE_DELETED,
                },
                "tracked_fields": [
                    "rate",
                    "effective_date",
                    "note",
                    "is_approved",
                    "deleted_at",
                ],
            },
        }

        model_key = f"{app_label}.{model_name}"
        return default_configs.get(model_key)


class BaseAuditHandler:
    """Base class for handling audit logging with common functionality."""

    @staticmethod
    def get_audit_context(instance):
        """Extract audit context from instance."""
        return {
            "user": getattr(instance, "_audit_user", None),
            "context": getattr(instance, "_audit_context", {}),
            "old_values": getattr(instance, "_audit_old_values", {}),
        }

    @staticmethod
    def capture_field_changes(old_instance, new_instance, fields):
        """Capture changes between old and new instance for specified fields."""
        if not AuditConfig.LOG_FIELD_CHANGES:
            return []

        changes = []
        for field in fields:
            # Skip sensitive fields
            if AuditConfig.is_sensitive_field(field):
                continue

            old_value = getattr(old_instance, field, None)
            new_value = getattr(new_instance, field, None)
            if old_value != new_value:
                changes.append(
                    {
                        "field": field,
                        "old_value": str(old_value) if old_value is not None else None,
                        "new_value": str(new_value) if new_value is not None else None,
                    }
                )
        return changes

    @staticmethod
    def _serialize_field_value(value):
        """Convert field value to JSON-serializable type."""
        if value is None:
            return None

        # Handle common Django field types that aren't JSON serializable

        if isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, (datetime, date, time)):
            return value.isoformat()
        elif isinstance(value, UUID):
            return str(value)
        elif hasattr(value, "pk"):  # Django model instance
            return str(value.pk)
        else:
            return value

    @staticmethod
    def build_metadata(
        instance, changes=None, operation_type=None, user=None, **extra_metadata
    ):
        """Build enhanced metadata dictionary for audit logging with rich context."""
        metadata = {"automatic_logging": True, **extra_metadata}

        if changes:
            metadata["changed_fields"] = changes

        # Add operation_type to metadata if provided
        if operation_type:
            metadata["operation_type"] = operation_type

        # Add user action metadata if user is available
        if user and operation_type:
            try:
                user_metadata = UserActionMetadataBuilder.build_user_action_metadata(
                    user, operation_type
                )
                metadata.update(user_metadata)
            except Exception as e:
                logger.warning(f"Failed to build user metadata: {e}")

        # Add entity-specific metadata based on model type
        try:
            model_name = instance._meta.model_name.lower()
            if hasattr(EntityMetadataBuilder, f"build_{model_name}_metadata"):
                entity_metadata_method = getattr(
                    EntityMetadataBuilder, f"build_{model_name}_metadata"
                )
                entity_metadata = entity_metadata_method(instance)
                metadata.update(entity_metadata)
            else:
                # Fallback to general entity metadata
                general_metadata = EntityMetadataBuilder.build_entity_metadata(instance)
                metadata.update(general_metadata)
        except Exception as e:
            logger.warning(
                f"Failed to build entity metadata for {instance._meta.model_name}: {e}"
            )

        return metadata


class GenericAuditSignalHandler(BaseAuditHandler):
    """Generic signal handler for common CRUD operations with improved registry integration."""

    @classmethod
    def create_handlers(cls, model_class, action_types, tracked_fields):
        """
        Factory method to create signal handlers for a model.
        Enhanced with better error handling and logging.
        """

        @receiver(pre_save, sender=model_class)
        @safe_audit_log
        def capture_changes(sender, instance, **kwargs):
            """Capture field changes before save for update tracking."""
            if instance.pk:
                try:
                    old_instance = sender.objects.get(pk=instance.pk)
                    instance._audit_old_values = {
                        field: getattr(old_instance, field, None)
                        for field in tracked_fields
                        if hasattr(old_instance, field)
                    }
                except ObjectDoesNotExist:
                    logger.debug(
                        f"Old instance not found for {sender.__name__} with pk={instance.pk}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Error capturing changes for {sender.__name__}: {e}"
                    )

        @receiver(post_save, sender=model_class)
        @safe_audit_log
        def log_changes(sender, instance, created, **kwargs):
            """Log create and update operations."""
            # Skip logging if model should not be logged (dynamic check)
            if not should_log_model(sender):
                return

            audit_context = cls.get_audit_context(instance)

            if created:
                # Log creation
                metadata = cls.build_metadata(
                    instance,
                    operation_type="create",
                    user=audit_context["user"],
                    **{
                        field: cls._serialize_field_value(
                            getattr(instance, field, None)
                        )
                        for field in tracked_fields
                        if hasattr(instance, field)
                    },
                    **audit_context["context"],
                )
                # Check if this model should exclude workspace context
                workspace_param = {}
                from .config import AuditConfig

                if AuditConfig.should_exclude_workspace_context(instance):
                    workspace_param["workspace"] = False

                audit_create(
                    user=audit_context["user"],
                    action_type=action_types["created"],
                    target_entity=instance,
                    metadata=metadata,
                    **workspace_param,
                )
                logger.debug(
                    f"Logged creation of {sender.__name__} with id={instance.pk}"
                )
            else:
                # Log updates only if there are actual changes
                old_values = audit_context["old_values"]
                if old_values:
                    changes = []
                    for field, old_value in old_values.items():
                        if hasattr(instance, field):
                            new_value = getattr(instance, field, None)
                            if old_value != new_value:
                                changes.append(
                                    {
                                        "field": field,
                                        "old_value": cls._serialize_field_value(
                                            old_value
                                        ),
                                        "new_value": cls._serialize_field_value(
                                            new_value
                                        ),
                                    }
                                )

                    if changes:
                        # Check if deleted_at field was changed from None to a timestamp (soft deletion)
                        deleted_at_changed = any(
                            change["field"] == "deleted_at"
                            and change["old_value"] is None
                            and change["new_value"] is not None
                            for change in changes
                        )

                        if deleted_at_changed and "deleted" in action_types:
                            # This is a soft deletion - use deletion action type
                            action_type = action_types["deleted"]
                            operation_type = "delete"

                            # Add soft deletion specific metadata
                            deleted_at_change = next(
                                change
                                for change in changes
                                if change["field"] == "deleted_at"
                            )
                            extra_metadata = {
                                "soft_delete": True,
                                "deletion_timestamp": deleted_at_change["new_value"],
                            }
                        else:
                            # Check if status field was changed to use specific action type
                            status_changed = any(
                                change["field"] == "status" for change in changes
                            )

                            if status_changed and "status_changed" in action_types:
                                # Use specific status changed action type
                                action_type = action_types["status_changed"]
                                operation_type = "status_change"

                                # Add status change specific metadata
                                status_change = next(
                                    change
                                    for change in changes
                                    if change["field"] == "status"
                                )
                                extra_metadata = {
                                    "old_status": status_change["old_value"],
                                    "new_status": status_change["new_value"],
                                }
                            else:
                                # Use generic update action type
                                action_type = action_types["updated"]
                                operation_type = "update"
                                extra_metadata = {}

                        metadata = cls.build_metadata(
                            instance,
                            operation_type=operation_type,
                            user=audit_context["user"],
                            changes=changes,
                            **{
                                field: cls._serialize_field_value(
                                    getattr(instance, field, None)
                                )
                                for field in tracked_fields
                                if hasattr(instance, field)
                            },
                            **extra_metadata,
                            **audit_context["context"],
                        )
                        # Check if this model should exclude workspace context
                        workspace_param = {}
                        from .config import AuditConfig

                        if AuditConfig.should_exclude_workspace_context(instance):
                            workspace_param["workspace"] = False

                        audit_create(
                            user=audit_context["user"],
                            action_type=action_type,
                            target_entity=instance,
                            metadata=metadata,
                            **workspace_param,
                        )
                        logger.debug(
                            f"Logged {operation_type} of {sender.__name__} with id={instance.pk}, {len(changes)} changes"
                        )

        @receiver(pre_delete, sender=model_class)
        @safe_audit_log
        def log_deletion(sender, instance, **kwargs):
            """Log deletion operations."""
            # Skip logging if model should not be logged (dynamic check)
            if not should_log_model(sender):
                return

            audit_context = cls.get_audit_context(instance)
            metadata = cls.build_metadata(
                instance,
                operation_type="delete",
                user=audit_context["user"],
                **{
                    field: cls._serialize_field_value(getattr(instance, field, None))
                    for field in tracked_fields
                    if hasattr(instance, field)
                },
                deletion_timestamp=getattr(instance, "updated_at", None).isoformat()
                if hasattr(instance, "updated_at") and getattr(instance, "updated_at")
                else None,
                **audit_context["context"],
            )
            # Check if this model should exclude workspace context
            workspace_param = {}
            from .config import AuditConfig

            if AuditConfig.should_exclude_workspace_context(instance):
                workspace_param["workspace"] = False

            audit_create(
                user=audit_context["user"],
                action_type=action_types["deleted"],
                target_entity=instance,
                metadata=metadata,
                **workspace_param,
            )
            logger.debug(f"Logged deletion of {sender.__name__} with id={instance.pk}")

        return capture_changes, log_changes, log_deletion

    @classmethod
    def register_all_models(cls):
        """Register signal handlers for all models in the registry."""
        AuditModelRegistry.auto_register_models()

        for model_key, config in AuditModelRegistry.get_all_registered_models().items():
            try:
                cls.create_handlers(
                    config["model_class"],
                    config["action_types"],
                    config["tracked_fields"],
                )
                logger.info(f"Successfully registered signal handlers for {model_key}")
            except Exception as e:
                logger.error(f"Failed to register signal handlers for {model_key}: {e}")


def initialize_audit_signals():
    """Initialize all audit signal handlers."""
    try:
        GenericAuditSignalHandler.register_all_models()
        logger.info("Audit signal handlers initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize audit signal handlers: {e}")


# Utility functions for manual registration
def register_custom_model(
    model_class, action_types: Dict[str, str], tracked_fields: List[str]
):
    """
    Manually register a custom model for audit logging.
    """
    AuditModelRegistry.register_model(model_class, action_types, tracked_fields)
    GenericAuditSignalHandler.create_handlers(model_class, action_types, tracked_fields)


def get_registered_models():
    """Get a list of all currently registered models for audit logging."""
    return list(AuditModelRegistry.get_all_registered_models().keys())


def is_model_registered(model_class) -> bool:
    """Check if a model is registered for audit logging."""
    model_key = f"{model_class._meta.app_label}.{model_class.__name__}"
    return model_key in AuditModelRegistry.get_all_registered_models()
