"""Base audit logger with common functionality for all domain-specific loggers."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from django.contrib.auth.models import User
from django.http import HttpRequest

from apps.auditlog.services import make_json_serializable
from apps.auditlog.tasks import audit_create_async, audit_create_security_event_async
from apps.organizations.models import OrganizationMember

logger = logging.getLogger(__name__)


class BaseAuditLogger(ABC):
    """Abstract base class for all audit loggers with common functionality."""

    @staticmethod
    def _validate_request_and_user(request: Optional[HttpRequest], user: User) -> None:
        """Validate request and user objects."""
        if not user or not user.is_authenticated:
            raise ValueError("Valid authenticated user required for audit logging")





    @staticmethod
    def _build_base_metadata(
        action: str, request: Optional[HttpRequest], **kwargs
    ) -> Dict[str, Any]:
        """Build base metadata common to all logging operations."""
        return {
            "action": action,
            "manual_logging": True,
            **kwargs,
        }

    @staticmethod
    def _safe_get_related_field(obj: Any, field_path: str, default: Any = None) -> Any:
        """Safely get nested field value with None checks."""
        try:
            current = obj
            for field in field_path.split("."):
                if current is None:
                    return default
                current = getattr(current, field, None)
            return current
        except (AttributeError, TypeError):
            return default

    @staticmethod
    def _handle_action_with_mapping(
        user: User,
        entity: Any,
        action: str,
        action_mapping: Dict[str, str],
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> Optional[str]:
        """Generic handler for actions with mapping validation."""
        BaseAuditLogger._validate_request_and_user(request, user)

        if action not in action_mapping:
            logger.warning(f"Unknown action: {action}")
            return None

        return action_mapping[action]

    @staticmethod
    def _finalize_and_create_audit(
        user: Union[User, OrganizationMember],
        action_type: str,
        metadata: Dict[str, Any],
        target_entity: Any = None,
        workspace: Any = None,
        is_security_event: bool = False,
    ) -> None:
        """Finalize metadata and create audit log entry."""
        # Prepare user_id
        if user:
            if hasattr(user, "user"):
                # OrganizationMember object
                user_id = str(user.user.user_id)
            else:
                # User object
                user_id = str(user.user_id)
        else:
            user_id = None

        # Prepare target_entity dict
        target_entity_dict = None
        if target_entity:
            target_entity_dict = {
                "model": f"{target_entity.__class__.__module__}.{target_entity.__class__.__name__}",
                "pk": target_entity.pk,
            }

        # Prepare workspace dict
        workspace_dict = None
        if workspace:
            workspace_dict = {"pk": workspace.pk}

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        if is_security_event:
            audit_create_security_event_async.delay(
                user_id=user_id,
                action_type=action_type,
                target_entity=target_entity_dict,
                metadata=serializable_metadata,
            )
        else:
            audit_create_async.delay(
                user_id=user_id,
                action_type=action_type,
                target_entity=target_entity_dict,
                workspace=workspace_dict,
                metadata=serializable_metadata,
            )

    @abstractmethod
    def get_supported_actions(self) -> Dict[str, str]:
        """Return mapping of supported actions to audit action types."""
        pass

    @abstractmethod
    def get_logger_name(self) -> str:
        """Return the name of this logger for identification."""
        pass
