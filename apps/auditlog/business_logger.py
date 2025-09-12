"""Business audit logger for manual audit logging operations.

This module provides backward compatibility for the original BusinessAuditLogger
while delegating to the new domain-specific loggers for improved maintainability.
"""

import logging

from django.utils import timezone

from apps.auditlog.services import (
    audit_create,
    audit_create_security_event,
    make_json_serializable,
)

from .loggers import LoggerFactory
from .utils import safe_audit_log

logger = logging.getLogger(__name__)


class BusinessAuditLogger:
    """
    Enhanced helper class for manual business logic audit logging.
    Use this for complex operations that require rich context.

    This class now delegates to domain-specific loggers for improved maintainability
    while preserving backward compatibility with existing code.
    """

    # Class-level logger factory instance
    _factory = LoggerFactory()

    @staticmethod
    def _validate_request_and_user(request, user):
        """Validate request and user objects"""
        if not user or not user.is_authenticated:
            raise ValueError("Valid authenticated user required for audit logging")

    @staticmethod
    def _safe_get_related_field(obj, field_path, converter=None):
        """Safely get a related field value with dot notation"""
        try:
            value = obj
            for field in field_path.split("."):
                if value is None:
                    return None
                value = getattr(value, field, None)

            if value is not None and converter:
                return converter(value)
            return value
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _build_base_metadata(action, request=None, **kwargs):
        """Build base metadata for audit entries"""
        metadata = {
            "action": action,
            "manual_logging": True,
            **kwargs,
        }
        return metadata

    @staticmethod
    def _build_user_action_metadata(user, role_prefix, timestamp_key):
        """Build user action metadata with role-specific keys"""
        return {
            f"{role_prefix}_id": str(user.user_id),
            f"{role_prefix}_email": user.email,
            timestamp_key: timezone.now().isoformat(),
        }

    @staticmethod
    def _build_entity_metadata(entity):
        """Build entity-specific metadata"""
        if entity is None:
            return {}

        metadata = {
            "entity_type": type(entity).__name__,
            "entity_id": str(getattr(entity, "pk", "")),
        }

        # Add common fields if they exist
        for field in ["title", "name", "description", "status"]:
            value = getattr(entity, field, None)
            if value is not None:
                metadata[f"entity_{field}"] = str(value)

        return metadata

    @staticmethod
    def _build_crud_action_metadata(user, action, **kwargs):
        """Build CRUD action metadata"""
        metadata = {}

        if action == "create":
            metadata.update(
                BusinessAuditLogger._build_user_action_metadata(
                    user, "creator", "creation_timestamp"
                )
            )
        elif action == "update":
            metadata.update(
                BusinessAuditLogger._build_user_action_metadata(
                    user, "updater", "update_timestamp"
                )
            )
            metadata["updated_fields"] = kwargs.get("updated_fields", [])
        elif action == "delete":
            metadata.update(
                BusinessAuditLogger._build_user_action_metadata(
                    user, "deleter", "deletion_timestamp"
                )
            )
            metadata["soft_delete"] = kwargs.get("soft_delete", False)

        return metadata

    @staticmethod
    def _handle_action_with_mapping(
        user, entity, action, action_mapping, request=None, **kwargs
    ):
        """Generic handler for actions with mapping validation"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        if action not in action_mapping:
            logger.warning(f"Unknown action: {action}")
            return None

        return action_mapping[action]

    @staticmethod
    def _finalize_and_create_audit(
        user, action_type, metadata, target_entity=None, is_security_event=False
    ):
        """Finalize metadata and create audit log entry"""
        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        if is_security_event:
            audit_create_security_event(
                user=user,
                action_type=action_type,
                target_entity=target_entity,
                metadata=serializable_metadata,
            )
        else:
            audit_create(
                user=user,
                action_type=action_type,
                target_entity=target_entity,
                metadata=serializable_metadata,
            )

    # Entry-related methods
    @classmethod
    @safe_audit_log
    def log_entry_workflow_action(
        cls, user, entry, action, request=None, workflow_stage=None, **kwargs
    ):
        """Log entry workflow actions with rich business context"""
        entry_logger = cls._factory.get_logger("entry")
        if entry_logger:
            # Add workflow_stage to kwargs if provided
            if workflow_stage:
                kwargs["workflow_stage"] = workflow_stage
            entry_logger.log_entry_workflow_action(
                user, entry, action, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_entry_action(cls, user, entry, action, request=None, **kwargs):
        """Log entry actions with rich business context"""
        entry_logger = cls._factory.get_logger("entry")
        if entry_logger:
            entry_logger.log_entry_action(user, entry, action, request, **kwargs)

    @classmethod
    @safe_audit_log
    def log_status_change(
        cls, user, entity, old_status, new_status, request=None, **kwargs
    ):
        """Log status changes for any entity"""
        entry_logger = cls._factory.get_logger("entry")
        if entry_logger:
            kwargs.update(
                {
                    "previous_status": old_status,
                    "new_status": new_status,
                }
            )
            entry_logger.log_status_change(
                user, entity, "status_change", request, **kwargs
            )

    # Organization-related methods
    @classmethod
    @safe_audit_log
    def log_organization_action(
        cls, user, organization, action, request=None, **kwargs
    ):
        """Log organization-specific actions"""
        org_logger = cls._factory.get_logger("organization")
        if org_logger:
            org_logger.log_organization_action(
                user, organization, action, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_organization_exchange_rate_action(
        cls, user, exchange_rate, action, request=None, **kwargs
    ):
        """Log organization exchange rate actions"""
        org_logger = cls._factory.get_logger("organization")
        if org_logger:
            org_logger.log_organization_exchange_rate_action(
                user, exchange_rate, action, request, **kwargs
            )

    # Workspace-related methods
    @classmethod
    @safe_audit_log
    def log_workspace_action(cls, user, workspace, action, request=None, **kwargs):
        """Log workspace-specific actions"""
        workspace_logger = cls._factory.get_logger("workspace")
        if workspace_logger:
            workspace_logger.log_workspace_action(
                user, workspace, action, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_workspace_team_action(
        cls, user, workspace, team, action, request=None, **kwargs
    ):
        """Log workspace team operations"""
        workspace_logger = cls._factory.get_logger("workspace")
        if workspace_logger:
            workspace_logger.log_workspace_team_action(
                user, workspace, team, action, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_workspace_exchange_rate_action(
        cls, user, exchange_rate, action, request=None, **kwargs
    ):
        """Log workspace exchange rate operations"""
        workspace_logger = cls._factory.get_logger("workspace")
        if workspace_logger:
            workspace_logger.log_workspace_exchange_rate_action(
                user, exchange_rate, action, request, **kwargs
            )

    # Team-related methods
    @classmethod
    @safe_audit_log
    def log_team_action(cls, user, team, action, request=None, **kwargs):
        """Log team-specific actions"""
        team_logger = cls._factory.get_logger("team")
        if team_logger:
            team_logger.log_team_action(user, team, action, request, **kwargs)

    @classmethod
    @safe_audit_log
    def log_team_member_action(cls, user, team_member, action, request=None, **kwargs):
        """Log team member operations"""
        team_logger = cls._factory.get_logger("team")
        if team_logger:
            # Extract team and member from the context
            team = kwargs.get("team") or getattr(team_member, "team", None)
            team_logger.log_team_member_action(
                user, team, team_member, action, request, **kwargs
            )

    # System-related methods
    @classmethod
    @safe_audit_log
    def log_permission_change(
        cls, user, target_user, permission_type, action, request=None, **kwargs
    ):
        """Log permission changes"""
        system_logger = cls._factory.get_logger("system")
        if system_logger:
            system_logger.log_permission_change(
                user, target_user, permission_type, action, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_data_export(cls, user, export_type, request=None, **kwargs):
        """Log data export operations"""
        system_logger = cls._factory.get_logger("system")
        if system_logger:
            system_logger.log_data_export(user, export_type, request, **kwargs)

    @classmethod
    @safe_audit_log
    def log_bulk_operation(
        cls, user, operation_type, affected_entities, request=None, **kwargs
    ):
        """Log bulk operations"""
        system_logger = cls._factory.get_logger("system")
        if system_logger:
            system_logger.log_bulk_operation(
                user, operation_type, affected_entities, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_file_operation(cls, user, file_obj, operation, request=None, **kwargs):
        """Log file operations"""
        system_logger = cls._factory.get_logger("system")
        if system_logger:
            system_logger.log_file_operation(
                user, file_obj, operation, request, **kwargs
            )

    @classmethod
    @safe_audit_log
    def log_operation_failure(cls, user, operation_type, error, request=None, **kwargs):
        """Log system operation failures"""
        system_logger = cls._factory.get_logger("system")
        if system_logger:
            error_details = {
                "error_type": type(error).__name__ if error else "Unknown",
                "error_message": str(error) if error else "Unknown error",
                "error_code": kwargs.get("error_code", ""),
                "stack_trace": kwargs.get("stack_trace", ""),
                "affected_component": kwargs.get("affected_component", ""),
                "severity": kwargs.get("severity", "medium"),
            }
            system_logger.log_operation_failure(
                user, operation_type, error_details, request, **kwargs
            )

    # Convenience method for auto-routing
    @classmethod
    @safe_audit_log
    def log_auto(cls, user, entity, action, request=None, logger_type=None, **kwargs):
        """Automatically route and log an action using the appropriate logger"""
        return cls._factory.log_auto(
            user, entity, action, request, logger_type, **kwargs
        )
