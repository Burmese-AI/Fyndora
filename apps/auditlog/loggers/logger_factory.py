"""Logger factory for routing audit logging requests to appropriate domain-specific loggers."""

import logging
from typing import Any, Dict, Optional, Type

from django.contrib.auth.models import User
from django.http import HttpRequest

from .base_logger import BaseAuditLogger
from .entry_logger import EntryAuditLogger
from .organization_logger import OrganizationAuditLogger
from .system_logger import SystemAuditLogger
from .team_logger import TeamAuditLogger
from .workspace_logger import WorkspaceAuditLogger

logger = logging.getLogger(__name__)


class LoggerFactory:
    """Factory class for creating and routing to appropriate audit loggers."""

    # Registry of available loggers
    _loggers: Dict[str, Type[BaseAuditLogger]] = {
        "entry": EntryAuditLogger,
        "organization": OrganizationAuditLogger,
        "workspace": WorkspaceAuditLogger,
        "team": TeamAuditLogger,
        "system": SystemAuditLogger,
    }

    # Cache for logger instances
    _logger_instances: Dict[str, BaseAuditLogger] = {}

    @classmethod
    def get_logger(cls, logger_type: str) -> Optional[BaseAuditLogger]:
        """Get a logger instance for the specified type.
        
        Args:
            logger_type: The type of logger to retrieve (entry, organization, etc.)
            
        Returns:
            BaseAuditLogger instance or None if logger type not found
        """
        if logger_type not in cls._loggers:
            logger.warning(f"Unknown logger type: {logger_type}")
            return None

        # Return cached instance if available
        if logger_type in cls._logger_instances:
            return cls._logger_instances[logger_type]

        # Create new instance and cache it
        logger_class = cls._loggers[logger_type]
        logger_instance = logger_class()
        cls._logger_instances[logger_type] = logger_instance
        
        return logger_instance

    @classmethod
    def get_available_loggers(cls) -> Dict[str, str]:
        """Get a mapping of available logger types to their class names.
        
        Returns:
            Dictionary mapping logger type to class name
        """
        return {logger_type: logger_class.__name__ for logger_type, logger_class in cls._loggers.items()}

    @classmethod
    def register_logger(cls, logger_type: str, logger_class: Type[BaseAuditLogger]) -> None:
        """Register a new logger type.
        
        Args:
            logger_type: The type identifier for the logger
            logger_class: The logger class to register
        """
        if not issubclass(logger_class, BaseAuditLogger):
            raise ValueError("Logger class must inherit from BaseAuditLogger")
        
        cls._loggers[logger_type] = logger_class
        # Clear cached instance if it exists
        if logger_type in cls._logger_instances:
            del cls._logger_instances[logger_type]
        
        logger.info(f"Registered logger type '{logger_type}' with class {logger_class.__name__}")

    @classmethod
    def auto_detect_logger_type(cls, entity: Any) -> Optional[str]:
        """Auto-detect the appropriate logger type based on entity type.
        
        Args:
            entity: The entity object to analyze
            
        Returns:
            Logger type string or None if cannot be determined
        """
        if entity is None:
            return "system"
        
        entity_type = type(entity).__name__.lower()
        
        # Map entity types to logger types
        entity_mapping = {
            "entry": "entry",
            "organization": "organization",
            "organizationexchangerate": "organization",
            "workspace": "workspace",
            "workspaceteam": "workspace",
            "workspaceexchangerate": "workspace",
            "team": "team",
            "teammember": "team",
            "user": "system",
            "file": "system",
            "attachment": "system",
        }
        
        return entity_mapping.get(entity_type, "system")

    @classmethod
    def log_auto(
        cls,
        user: User,
        entity: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        logger_type: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Automatically route and log an action using the appropriate logger.
        
        Args:
            user: The user performing the action
            entity: The entity being acted upon
            action: The action being performed
            request: Optional HTTP request object
            logger_type: Optional explicit logger type (overrides auto-detection)
            **kwargs: Additional metadata for the log entry
            
        Returns:
            True if logging was successful, False otherwise
        """
        try:
            # Determine logger type
            if logger_type is None:
                logger_type = cls.auto_detect_logger_type(entity)
            
            if logger_type is None:
                logger.warning(f"Could not determine logger type for entity: {type(entity).__name__}")
                return False
            
            # Get appropriate logger
            audit_logger = cls.get_logger(logger_type)
            if audit_logger is None:
                logger.warning(f"Could not get logger for type: {logger_type}")
                return False
            
            # Route to appropriate method based on logger type and action
            success = cls._route_to_logger_method(
                audit_logger, logger_type, user, entity, action, request, **kwargs
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error in auto logging: {str(e)}", exc_info=True)
            return False

    @classmethod
    def _route_to_logger_method(
        cls,
        audit_logger: BaseAuditLogger,
        logger_type: str,
        user: User,
        entity: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs
    ) -> bool:
        """Route to the appropriate logger method based on logger type and action.
        
        Args:
            audit_logger: The logger instance to use
            logger_type: The type of logger
            user: The user performing the action
            entity: The entity being acted upon
            action: The action being performed
            request: Optional HTTP request object
            **kwargs: Additional metadata
            
        Returns:
            True if logging was successful, False otherwise
        """
        try:
            if logger_type == "entry":
                if action in ["submit", "approve", "reject", "update", "delete"]:
                    audit_logger.log_entry_action(user, entity, action, request, **kwargs)
                elif action in ["workflow_transition"]:
                    audit_logger.log_entry_workflow_action(user, entity, action, request, **kwargs)
                else:
                    audit_logger.log_status_change(user, entity, action, request, **kwargs)
            
            elif logger_type == "organization":
                if "exchange_rate" in str(type(entity).__name__).lower():
                    audit_logger.log_organization_exchange_rate_action(user, entity, action, request, **kwargs)
                else:
                    audit_logger.log_organization_action(user, entity, action, request, **kwargs)
            
            elif logger_type == "workspace":
                if "team" in str(type(entity).__name__).lower():
                    team = kwargs.get("team", entity)
                    audit_logger.log_workspace_team_action(user, entity, team, action, request, **kwargs)
                elif "exchange_rate" in str(type(entity).__name__).lower():
                    audit_logger.log_workspace_exchange_rate_action(user, entity, action, request, **kwargs)
                else:
                    audit_logger.log_workspace_action(user, entity, action, request, **kwargs)
            
            elif logger_type == "team":
                if "member" in str(type(entity).__name__).lower():
                    team = kwargs.get("team", entity)
                    member = kwargs.get("member", entity)
                    audit_logger.log_team_member_action(user, team, member, action, request, **kwargs)
                else:
                    audit_logger.log_team_action(user, entity, action, request, **kwargs)
            
            elif logger_type == "system":
                if action.startswith("permission_"):
                    target_user = kwargs.get("target_user", entity)
                    permission_type = kwargs.get("permission_type", "")
                    audit_logger.log_permission_change(user, target_user, permission_type, action.replace("permission_", ""), request, **kwargs)
                elif action == "data_export":
                    export_type = kwargs.get("export_type", "")
                    audit_logger.log_data_export(user, export_type, request, **kwargs)
                elif action == "bulk_operation":
                    operation_type = kwargs.get("operation_type", "")
                    affected_entities = kwargs.get("affected_entities", [])
                    audit_logger.log_bulk_operation(user, operation_type, affected_entities, request, **kwargs)
                elif action.startswith("file_"):
                    audit_logger.log_file_operation(user, entity, action.replace("file_", ""), request, **kwargs)
                elif action == "operation_failure":
                    operation = kwargs.get("operation", "")
                    error_details = kwargs.get("error_details", {})
                    audit_logger.log_operation_failure(user, operation, error_details, request, **kwargs)
                else:
                    logger.warning(f"Unknown system action: {action}")
                    return False
            
            else:
                logger.warning(f"Unknown logger type for routing: {logger_type}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error routing to logger method: {str(e)}", exc_info=True)
            return False


# Convenience functions for backward compatibility
def get_entry_logger() -> Optional[EntryAuditLogger]:
    """Get the entry audit logger instance."""
    return LoggerFactory.get_logger("entry")


def get_organization_logger() -> Optional[OrganizationAuditLogger]:
    """Get the organization audit logger instance."""
    return LoggerFactory.get_logger("organization")


def get_workspace_logger() -> Optional[WorkspaceAuditLogger]:
    """Get the workspace audit logger instance."""
    return LoggerFactory.get_logger("workspace")


def get_team_logger() -> Optional[TeamAuditLogger]:
    """Get the team audit logger instance."""
    return LoggerFactory.get_logger("team")


def get_system_logger() -> Optional[SystemAuditLogger]:
    """Get the system audit logger instance."""
    return LoggerFactory.get_logger("system")