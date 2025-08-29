"""Workspace-specific audit logger for workspace management operations."""

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


class WorkspaceAuditLogger(BaseAuditLogger):
    """Audit logger for workspace-related operations."""

    def get_supported_actions(self) -> Dict[str, str]:
        """Return mapping of supported workspace actions to audit action types."""
        return {
            "create": AuditActionType.WORKSPACE_CREATED,
            "update": AuditActionType.WORKSPACE_UPDATED,
            "delete": AuditActionType.WORKSPACE_DELETED,
            "archive": AuditActionType.WORKSPACE_ARCHIVED,
            "activate": AuditActionType.WORKSPACE_ACTIVATED,
            "close": AuditActionType.WORKSPACE_CLOSED,
            "status_change": AuditActionType.WORKSPACE_STATUS_CHANGED,
        }

    def get_logger_name(self) -> str:
        """Return the name of this logger for identification."""
        return "workspace_logger"

    @safe_audit_log
    def log_workspace_action(
        self,
        user: User,
        workspace: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log workspace-specific actions with rich business context."""
        action_type = self._handle_action_with_mapping(
            user, workspace, action, self.get_supported_actions(), request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = self._build_base_metadata(action, request, **kwargs)

        # Add workspace-specific metadata
        metadata.update(EntityMetadataBuilder.build_workspace_metadata(workspace))

        # Add CRUD action metadata
        metadata.update(
            UserActionMetadataBuilder.build_crud_action_metadata(
                user,
                action,
                **kwargs,
            )
        )

        # Add status change specific metadata
        if action in ["archive", "activate", "close", "status_change"]:
            metadata.update(
                {
                    "modifier_id": str(user.user_id),
                    "modifier_email": user.email,
                    "modification_timestamp": timezone.now().isoformat(),
                    "previous_status": kwargs.get("previous_status"),
                    "new_status": kwargs.get("new_status"),
                }
            )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, action_type, metadata, workspace, workspace
        )

    @safe_audit_log
    def log_workspace_team_action(
        self,
        user: User,
        workspace: Any,
        team: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log workspace team operations with rich business context."""
        self._validate_request_and_user(request, user)

        action_mapping = {
            "add": AuditActionType.WORKSPACE_TEAM_ADDED,
            "remove": AuditActionType.WORKSPACE_TEAM_REMOVED,
            "remittance_rate_update": AuditActionType.WORKSPACE_TEAM_REMITTANCE_RATE_UPDATED,
        }

        if action not in action_mapping:
            logger.warning(f"Unknown workspace team action: {action}")
            return

        # Base metadata for workspace team actions
        metadata = {
            "action": action,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add workspace and team metadata
        if workspace:
            metadata.update(
                {
                    "workspace_id": str(workspace.workspace_id),
                    "workspace_title": workspace.title,
                    "organization_id": str(workspace.organization.organization_id),
                    "organization_title": workspace.organization.title,
                }
            )

        if team:
            metadata.update(
                {
                    "team_id": str(team.team_id),
                    "team_title": team.title,
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

        # Add action-specific metadata
        if action == "add":
            metadata.update(
                {
                    "added_by_id": str(user.user_id),
                    "added_by_email": user.email,
                    "addition_timestamp": timezone.now().isoformat(),
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
        elif action == "remittance_rate_update":
            metadata.update(
                {
                    "updated_by_id": str(user.user_id),
                    "updated_by_email": user.email,
                    "update_timestamp": timezone.now().isoformat(),
                    "previous_rate": kwargs.get("previous_rate", ""),
                    "new_rate": kwargs.get("new_rate", ""),
                }
            )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, action_mapping[action], metadata, team, workspace
        )

    @safe_audit_log
    def log_workspace_exchange_rate_action(
        self,
        user: User,
        exchange_rate: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log workspace exchange rate operations with rich business context."""
        self._validate_request_and_user(request, user)

        action_mapping = {
            "create": AuditActionType.WORKSPACE_EXCHANGE_RATE_CREATED,
            "update": AuditActionType.WORKSPACE_EXCHANGE_RATE_UPDATED,
            "delete": AuditActionType.WORKSPACE_EXCHANGE_RATE_DELETED,
        }

        if action not in action_mapping:
            logger.warning(f"Unknown workspace exchange rate action: {action}")
            return

        # Base metadata for workspace exchange rate actions
        metadata = {
            "action": action,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add exchange rate-specific metadata if exchange_rate exists
        if exchange_rate:
            metadata.update(
                {
                    "exchange_rate_id": str(exchange_rate.pk),
                    "workspace_id": str(exchange_rate.workspace.workspace_id),
                    "workspace_title": exchange_rate.workspace.title,
                    "organization_id": str(
                        exchange_rate.workspace.organization.organization_id
                    ),
                    "organization_title": exchange_rate.workspace.organization.title,
                    "from_currency": getattr(exchange_rate, "from_currency", ""),
                    "to_currency": getattr(exchange_rate, "to_currency", ""),
                    "rate": str(getattr(exchange_rate, "rate", "")),
                    "effective_date": getattr(exchange_rate, "effective_date", ""),
                }
            )

        # Add action-specific metadata
        if action == "create":
            metadata.update(
                {
                    "creator_id": str(user.user_id),
                    "creator_email": user.email,
                    "creation_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "update":
            metadata.update(
                {
                    "updater_id": str(user.user_id),
                    "updater_email": user.email,
                    "updated_fields": kwargs.get("updated_fields", []),
                    "update_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "delete":
            metadata.update(
                {
                    "deleter_id": str(user.user_id),
                    "deleter_email": user.email,
                    "deletion_timestamp": timezone.now().isoformat(),
                }
            )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, action_mapping[action], metadata, exchange_rate
        )
