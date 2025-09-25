"""Metadata builders for constructing audit log metadata in a consistent way."""

from typing import Any, Dict, List, Optional
from django.contrib.auth.models import User
from django.utils import timezone


class UserActionMetadataBuilder:
    """Builder for user action metadata (create/update/delete)."""

    @staticmethod
    def build_user_action_metadata(
        user: User, action_type: str, timestamp_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build metadata for user actions (create/update/delete)."""
        # Use better naming conventions for clarity
        action_suffix = "by" if action_type in ["create", "update", "delete"] else ""
        id_key = f"{action_type}{'_' + action_suffix if action_suffix else ''}_id"
        email_key = f"{action_type}{'_' + action_suffix if action_suffix else ''}_email"

        metadata = {
            id_key: str(user.user_id),
            email_key: user.email,
        }

        if timestamp_key:
            metadata[timestamp_key] = timezone.now().isoformat()

        return metadata

    @staticmethod
    def build_crud_action_metadata(
        user: User,
        action: str,
        updated_fields: Optional[List[str]] = None,
        soft_delete: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build metadata for CRUD operations (create/update/delete)."""
        metadata = {}

        if action == "create":
            metadata.update(
                UserActionMetadataBuilder.build_user_action_metadata(
                    user, "creator", "creation_timestamp"
                )
            )
        elif action == "update":
            metadata.update(
                UserActionMetadataBuilder.build_user_action_metadata(
                    user, "updater", "update_timestamp"
                )
            )
            metadata["updated_fields"] = updated_fields or []
        elif action == "delete":
            metadata.update(
                UserActionMetadataBuilder.build_user_action_metadata(
                    user, "deleter", "deletion_timestamp"
                )
            )
            metadata["soft_delete"] = soft_delete

        return metadata


class EntityMetadataBuilder:
    """Builder for entity-specific metadata."""

    @staticmethod
    def build_entity_metadata(
        entity: Any, id_field: Optional[str] = None, title_field: str = "title"
    ) -> Dict[str, Any]:
        """Build metadata for entity objects."""
        if not entity:
            return {}

        # Get primary key field name if not specified
        if id_field is None:
            id_field = entity._meta.pk.name

        metadata = {
            f"{entity.__class__.__name__.lower()}_id": str(getattr(entity, id_field)),
        }

        # Add title/name if exists
        if hasattr(entity, title_field):
            metadata[f"{entity.__class__.__name__.lower()}_{title_field}"] = getattr(
                entity, title_field
            )

        return metadata

    @staticmethod
    def build_organization_metadata(organization: Any) -> Dict[str, Any]:
        """Build organization-specific metadata."""
        if not organization:
            return {}

        return {
            "organization_id": str(organization.organization_id),
            "organization_title": organization.title,
            "organization_status": getattr(organization, "status", None),
            "organization_description": getattr(organization, "description", ""),
        }

    @staticmethod
    def build_workspace_metadata(workspace: Any) -> Dict[str, Any]:
        """Build workspace-specific metadata."""
        if not workspace:
            return {}

        from .base_logger import BaseAuditLogger

        return {
            "workspace_id": str(workspace.workspace_id),
            "workspace_title": workspace.title,
            "workspace_description": getattr(workspace, "description", ""),
            "workspace_status": getattr(workspace, "status", ""),
            "organization_id": BaseAuditLogger._safe_get_related_field(
                workspace, "organization.organization_id", str
            ),
            "organization_title": BaseAuditLogger._safe_get_related_field(
                workspace, "organization.title"
            ),
            "workspace_admin_id": BaseAuditLogger._safe_get_related_field(
                workspace, "workspace_admin.organization_member_id", str
            ),
            "workspace_admin_email": BaseAuditLogger._safe_get_related_field(
                workspace, "workspace_admin.user.email"
            ),
            "workspace_reviewer_id": BaseAuditLogger._safe_get_related_field(
                workspace, "operations_reviewer.organization_member_id", str
            ),
            "workspace_reviewer_email": BaseAuditLogger._safe_get_related_field(
                workspace, "operations_reviewer.user.email"
            ),
        }

    @staticmethod
    def build_team_metadata(team: Any) -> Dict[str, Any]:
        """Build team-specific metadata."""
        if not team:
            return {}

        from .base_logger import BaseAuditLogger

        return {
            "team_id": str(team.team_id),
            "team_title": team.title,
            "team_description": getattr(team, "description", ""),
            "organization_id": BaseAuditLogger._safe_get_related_field(
                team, "organization.organization_id", str
            ),
            "organization_title": BaseAuditLogger._safe_get_related_field(
                team, "organization.title"
            ),
            "workspace_id": BaseAuditLogger._safe_get_related_field(
                team, "workspace.workspace_id", str
            ),
            "workspace_title": BaseAuditLogger._safe_get_related_field(
                team, "workspace.title"
            ),
            "team_coordinator_id": BaseAuditLogger._safe_get_related_field(
                team, "team_coordinator.organization_member_id", str
            ),
            "team_coordinator_email": BaseAuditLogger._safe_get_related_field(
                team, "team_coordinator.user.email"
            ),
        }

    @staticmethod
    def build_entry_metadata(entry: Any) -> Dict[str, Any]:
        """Build entry-specific metadata."""
        if not entry:
            return {}

        from .base_logger import BaseAuditLogger

        return {
            "entry_id": str(entry.entry_id),
            "entry_description": getattr(entry, "description", ""),
            "entry_status": getattr(entry, "status", ""),
            "entry_amount": str(entry.amount)
            if getattr(entry, "amount", None)
            else None,
            "entry_currency": str(getattr(entry, "currency", "")),
            "entry_type": getattr(entry, "entry_type", ""),
            "workspace_id": BaseAuditLogger._safe_get_related_field(
                entry, "workspace.workspace_id", str
            ),
            "workspace_title": BaseAuditLogger._safe_get_related_field(
                entry, "workspace.title"
            ),
            "organization_id": BaseAuditLogger._safe_get_related_field(
                entry, "organization.organization_id", str
            ),
            "organization_title": BaseAuditLogger._safe_get_related_field(
                entry, "organization.title"
            ),
        }

    @staticmethod
    def build_workspaceteam_metadata(workspace_team: Any) -> Dict[str, Any]:
        """Build workspace team-specific metadata."""
        if not workspace_team:
            return {}

        from .base_logger import BaseAuditLogger

        return {
            "workspace_team_id": str(workspace_team.workspace_team_id),
            "workspace_id": BaseAuditLogger._safe_get_related_field(
                workspace_team, "workspace.workspace_id", str
            ),
            "workspace_title": BaseAuditLogger._safe_get_related_field(
                workspace_team, "workspace.title"
            ),
            "team_id": BaseAuditLogger._safe_get_related_field(
                workspace_team, "team.team_id", str
            ),
            "team_title": BaseAuditLogger._safe_get_related_field(
                workspace_team, "team.title"
            ),
            "organization_id": BaseAuditLogger._safe_get_related_field(
                workspace_team, "workspace.organization.organization_id", str
            ),
            "organization_title": BaseAuditLogger._safe_get_related_field(
                workspace_team, "workspace.organization.title"
            ),
        }

    @staticmethod
    def build_teammember_metadata(team_member: Any) -> Dict[str, Any]:
        """Build team member-specific metadata."""
        if not team_member:
            return {}

        from .base_logger import BaseAuditLogger

        return {
            "team_member_id": str(team_member.team_member_id),
            "team_member_role": getattr(team_member, "role", ""),
            "team_id": BaseAuditLogger._safe_get_related_field(
                team_member, "team.team_id", str
            ),
            "team_title": BaseAuditLogger._safe_get_related_field(
                team_member, "team.title"
            ),
            "organization_member_id": BaseAuditLogger._safe_get_related_field(
                team_member, "organization_member.organization_member_id", str
            ),
            "user_id": BaseAuditLogger._safe_get_related_field(
                team_member, "organization_member.user.user_id", str
            ),
            "user_email": BaseAuditLogger._safe_get_related_field(
                team_member, "organization_member.user.email"
            ),
            "organization_id": BaseAuditLogger._safe_get_related_field(
                team_member, "team.organization.organization_id", str
            ),
            "organization_title": BaseAuditLogger._safe_get_related_field(
                team_member, "team.organization.title"
            ),
        }


class WorkflowMetadataBuilder:
    """Builder for workflow-specific metadata."""

    @staticmethod
    def build_workflow_metadata(
        user: User,
        action: str,
        workflow_stage: Optional[str] = None,
        notes: str = "",
        reason: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Build workflow action metadata."""
        metadata = {"workflow_action": True}

        # Add workflow stage information
        if workflow_stage:
            metadata.update(
                {
                    "workflow_stage": workflow_stage,
                    "stage_timestamp": timezone.now().isoformat(),
                }
            )

        # Add action-specific metadata
        if action in ["submit", "resubmit"]:
            metadata.update(
                {
                    "submitter_id": str(user.user_id),
                    "submitter_email": user.email,
                    "submission_timestamp": timezone.now().isoformat(),
                    "submission_notes": notes,
                }
            )
        elif action in ["approve", "reject", "return"]:
            metadata.update(
                {
                    "reviewer_id": str(user.user_id),
                    "reviewer_email": user.email,
                    "review_timestamp": timezone.now().isoformat(),
                    "review_notes": notes,
                    "review_decision": action,
                }
            )
        elif action == "withdraw":
            metadata.update(
                {
                    "withdrawer_id": str(user.user_id),
                    "withdrawer_email": user.email,
                    "withdrawal_timestamp": timezone.now().isoformat(),
                    "withdrawal_reason": reason,
                }
            )

        return metadata


class FileMetadataBuilder:
    """Builder for file operation metadata."""

    @staticmethod
    def build_file_metadata(
        file_obj: Any, operation: str, file_category: str = "general", **kwargs
    ) -> Dict[str, Any]:
        """Build file operation metadata."""
        metadata = {
            "file_name": getattr(file_obj, "name", "unknown"),
            "file_size": getattr(file_obj, "size", 0),
            "file_type": getattr(file_obj, "content_type", "unknown"),
            "operation": operation,
            "file_category": file_category,
        }

        # Add operation-specific metadata
        if operation == "upload":
            metadata.update(
                {
                    "upload_source": kwargs.get("source", "web_interface"),
                    "upload_purpose": kwargs.get("purpose", ""),
                }
            )
        elif operation == "download":
            metadata.update(
                {
                    "download_reason": kwargs.get("reason", ""),
                }
            )

        return metadata
