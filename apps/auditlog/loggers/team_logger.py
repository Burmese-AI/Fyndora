"""Team-specific audit logger for team management operations."""

import logging
from typing import Any, Dict, Optional

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.utils import timezone

from apps.auditlog.constants import AuditActionType
from apps.auditlog.utils import safe_audit_log

from .base_logger import BaseAuditLogger
from .metadata_builders import (
    EntityMetadataBuilder,
    UserActionMetadataBuilder,
)

logger = logging.getLogger(__name__)


class TeamAuditLogger(BaseAuditLogger):
    """Audit logger for team-related operations."""

    def get_supported_actions(self) -> Dict[str, str]:
        """Return mapping of supported team actions to audit action types."""
        return {
            "create": AuditActionType.TEAM_CREATED,
            "update": AuditActionType.TEAM_UPDATED,
            "delete": AuditActionType.TEAM_DELETED,
        }

    def get_logger_name(self) -> str:
        """Return the name of this logger for identification."""
        return "team_logger"

    @safe_audit_log
    def log_team_action(
        self,
        user: User,
        team: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log team-specific actions with rich business context."""
        action_type = self._handle_action_with_mapping(
            user, team, action, self.get_supported_actions(), request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = self._build_base_metadata(action, request, **kwargs)

        # Add team-specific metadata
        metadata.update(EntityMetadataBuilder.build_team_metadata(team))

        # Add CRUD action metadata
        # Extract parameters to avoid duplicate keyword arguments
        updated_fields = kwargs.pop("updated_fields", [])
        soft_delete = kwargs.pop("soft_delete", False)
        metadata.update(
            UserActionMetadataBuilder.build_crud_action_metadata(
                user,
                action,
                updated_fields=updated_fields,
                soft_delete=soft_delete,
                **kwargs,
            )
        )

        # Finalize and create audit log
        workspace = getattr(team, "workspace", None)
        self._finalize_and_create_audit(user, action_type, metadata, team, workspace)

    @safe_audit_log
    def log_team_member_action(
        self,
        user: User,
        team: Any,
        member: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log team member operations with rich business context."""
        self._validate_request_and_user(request, user)

        action_mapping = {
            "add": AuditActionType.TEAM_MEMBER_ADDED,
            "remove": AuditActionType.TEAM_MEMBER_REMOVED,
            "role_change": AuditActionType.TEAM_MEMBER_ROLE_CHANGED,
        }

        if action not in action_mapping:
            logger.warning(f"Unknown team member action: {action}")
            return

        # Base metadata for team member actions
        metadata = {
            "action": action,
            "manual_logging": True,
            **kwargs,
        }

        # Add team metadata
        if team:
            metadata.update(
                {
                    "team_id": str(team.team_id),
                    "team_title": team.title,
                    "organization_id": str(team.organization.organization_id),
                    "organization_title": team.organization.title,
                    "team_coordinator_id": str(
                        team.team_coordinator.organization_member_id
                    )
                    if team.team_coordinator
                    else None,
                    "team_coordinator_email": team.team_coordinator.user.email
                    if team.team_coordinator
                    else None,
                }
            )

        # Add member metadata
        if member:
            metadata.update(
                {
                    "member_id": str(member.organization_member_id),
                    "member_email": member.user.email,
                    "member_role": getattr(member, "role", ""),
                    "member_status": getattr(member, "status", ""),
                }
            )

        # Add action-specific metadata
        if action == "add":
            metadata.update(
                {
                    "added_by_id": str(user.user_id),
                    "added_by_email": user.email,
                    "addition_timestamp": timezone.now().isoformat(),
                    "assigned_role": kwargs.get("assigned_role", ""),
                }
            )
        elif action == "remove":
            metadata.update(
                {
                    "removed_by_id": str(user.user_id),
                    "removed_by_email": user.email,
                    "removal_timestamp": timezone.now().isoformat(),
                    "removal_reason": kwargs.get("reason", ""),
                }
            )
        elif action == "role_change":
            metadata.update(
                {
                    "changed_by_id": str(user.user_id),
                    "changed_by_email": user.email,
                    "role_change_timestamp": timezone.now().isoformat(),
                    "previous_role": kwargs.get("previous_role", ""),
                    "new_role": kwargs.get("new_role", ""),
                    "role_change_reason": kwargs.get("reason", ""),
                }
            )

        # Finalize and create audit log
        workspace = getattr(team, "workspace", None)
        self._finalize_and_create_audit(
            user, action_mapping[action], metadata, team, workspace
        )
