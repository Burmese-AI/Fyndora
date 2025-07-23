"""
Signal handlers for automatic audit logging.
"""

import logging
from typing import Dict, List, Optional

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from apps.auditlog.constants import AuditActionType
from apps.auditlog.services import audit_create

from .config import AuditConfig
from .utils import safe_audit_log, should_log_model

logger = logging.getLogger(__name__)


class AuditModelRegistry:
    """Registry for managing audit configurations for different models."""
    
    _registry: Dict[str, Dict] = {}
    
    @classmethod
    def register_model(cls, model_class, action_types: Dict[str, str], tracked_fields: List[str]):
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
                        model, 
                        config["action_types"], 
                        config["tracked_fields"]
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
                },
                "tracked_fields": ["name", "status", "description"],
            },
            "workspaces.Workspace": {
                "action_types": {
                    "created": AuditActionType.WORKSPACE_CREATED,
                    "updated": AuditActionType.WORKSPACE_UPDATED,
                    "deleted": AuditActionType.WORKSPACE_DELETED,
                },
                "tracked_fields": ["name", "description", "status"],
            },
            "entries.Entry": {
                "action_types": {
                    "created": AuditActionType.ENTRY_CREATED,
                    "updated": AuditActionType.ENTRY_UPDATED,
                    "deleted": AuditActionType.ENTRY_DELETED,
                },
                "tracked_fields": ["type", "amount", "status"],
            },
            "teams.Team": {
                "action_types": {
                    "created": AuditActionType.TEAM_CREATED,
                    "updated": AuditActionType.TEAM_UPDATED,
                    "deleted": AuditActionType.TEAM_DELETED,
                },
                "tracked_fields": ["name", "description", "status"],
            },
            "remittance.Remittance": {
                "action_types": {
                    "created": AuditActionType.REMITTANCE_CREATED,
                    "updated": AuditActionType.REMITTANCE_UPDATED,
                    "deleted": AuditActionType.REMITTANCE_DELETED,
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
    def build_metadata(instance, changes=None, **extra_metadata):
        """Build metadata dictionary for audit logging."""
        metadata = {"automatic_logging": True, **extra_metadata}

        if changes:
            metadata["changed_fields"] = changes

        return metadata


class GenericAuditSignalHandler(BaseAuditHandler):
    """Generic signal handler for common CRUD operations with improved registry integration."""

    @classmethod
    def create_handlers(cls, model_string, action_types, tracked_fields):
        """
        Factory method to create signal handlers for a model.
        Enhanced with better error handling and logging.
        """

        @receiver(pre_save, sender=model_string)
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
                    logger.debug(f"Old instance not found for {sender.__name__} with pk={instance.pk}")
                except Exception as e:
                    logger.warning(f"Error capturing changes for {sender.__name__}: {e}")

        @receiver(post_save, sender=model_string)
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
                    **{
                        field: getattr(instance, field, None)
                        for field in tracked_fields
                        if hasattr(instance, field)
                    },
                    **audit_context["context"],
                )
                audit_create(
                    user=audit_context["user"],
                    action_type=action_types["created"],
                    target_entity=instance,
                    metadata=metadata,
                )
                logger.debug(f"Logged creation of {sender.__name__} with id={instance.pk}")
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
                                        "old_value": str(old_value)
                                        if old_value is not None
                                        else None,
                                        "new_value": str(new_value)
                                        if new_value is not None
                                        else None,
                                    }
                                )

                    if changes:
                        metadata = cls.build_metadata(
                            instance,
                            operation_type="update",
                            changes=changes,
                            **{
                                field: getattr(instance, field, None)
                                for field in tracked_fields
                                if hasattr(instance, field)
                            },
                            **audit_context["context"],
                        )
                        audit_create(
                            user=audit_context["user"],
                            action_type=action_types["updated"],
                            target_entity=instance,
                            metadata=metadata,
                        )
                        logger.debug(f"Logged update of {sender.__name__} with id={instance.pk}, {len(changes)} changes")

        @receiver(pre_delete, sender=model_string)
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
                **{
                    field: getattr(instance, field, None)
                    for field in tracked_fields
                    if hasattr(instance, field)
                },
                deletion_timestamp=getattr(instance, "updated_at", None).isoformat()
                if hasattr(instance, "updated_at") and getattr(instance, "updated_at")
                else None,
                **audit_context["context"],
            )
            audit_create(
                user=audit_context["user"],
                action_type=action_types["deleted"],
                target_entity=instance,
                metadata=metadata,
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
                    config["tracked_fields"]
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


# Initialize the audit signals when this module is imported
initialize_audit_signals()


# Utility functions for manual registration
def register_custom_model(model_class, action_types: Dict[str, str], tracked_fields: List[str]):
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
