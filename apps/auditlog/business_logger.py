"""
Business audit logger for manual audit logging operations.
"""

import logging

from django.utils import timezone

from apps.auditlog.constants import AuditActionType
from apps.auditlog.config import AuditConfig
from apps.auditlog.services import (
    audit_create,
    audit_create_security_event,
    make_json_serializable,
)

from .utils import safe_audit_log

logger = logging.getLogger(__name__)


class BusinessAuditLogger:
    """
    Enhanced helper class for manual business logic audit logging.
    Use this for complex operations that require rich context.
    """

    @staticmethod
    def _validate_request_and_user(request, user):
        """Validate request and user objects"""
        if not user or not user.is_authenticated:
            raise ValueError("Valid authenticated user required for audit logging")

    @staticmethod
    def _extract_request_metadata(request):
        """Extract metadata from Django request object"""
        if request is None:
            return {
                "ip_address": "unknown",
                "user_agent": "unknown",
                "http_method": "unknown",
                "request_path": "unknown",
                "session_key": None,
                "source": "service_call",
            }

        return {
            "ip_address": request.META.get("REMOTE_ADDR", "unknown"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "unknown"),
            "http_method": request.method,
            "request_path": request.path,
            "session_key": getattr(
                getattr(request, "session", None), "session_key", None
            ),
            "source": "web_request",
        }

    @staticmethod
    def _get_request_param(request, param_name, default="", method="POST"):
        """Extract parameter from request with fallback to kwargs"""
        if request is None:
            return default
        
        if method == "POST":
            return request.POST.get(param_name, default)
        elif method == "GET":
            return request.GET.get(param_name, default)
        return default

    @staticmethod
    def _build_base_metadata(action, request, **kwargs):
        """Build base metadata common to all logging operations"""
        return {
            "action": action,
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

    @staticmethod
    def _build_user_action_metadata(user, action_type, timestamp_key=None):
        """Build metadata for user actions (create/update/delete)"""
        metadata = {
            f"{action_type}_id": str(user.user_id),
            f"{action_type}_email": user.email,
        }
        
        if timestamp_key:
            metadata[timestamp_key] = timezone.now().isoformat()
        
        return metadata

    @staticmethod
    def _build_entity_metadata(entity, id_field=None, title_field="title"):
        """Build metadata for entity objects"""
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
            metadata[f"{entity.__class__.__name__.lower()}_{title_field}"] = getattr(entity, title_field)
        
        return metadata

    @staticmethod
    def _safe_get_related_field(obj, field_path, default=None):
        """Safely get nested field value with None checks"""
        try:
            current = obj
            for field in field_path.split('.'):
                if current is None:
                    return default
                current = getattr(current, field, None)
            return current
        except (AttributeError, TypeError):
            return default

    @staticmethod
    def _build_crud_action_metadata(user, action, request=None, **kwargs):
        """Build metadata for CRUD operations (create/update/delete)"""
        metadata = {}
        
        if action == "create":
            metadata.update(BusinessAuditLogger._build_user_action_metadata(
                user, "creator", "creation_timestamp"
            ))
        elif action == "update":
            metadata.update(BusinessAuditLogger._build_user_action_metadata(
                user, "updater", "update_timestamp"
            ))
            metadata["updated_fields"] = kwargs.get("updated_fields", [])
        elif action == "delete":
            metadata.update(BusinessAuditLogger._build_user_action_metadata(
                user, "deleter", "deletion_timestamp"
            ))
            metadata["soft_delete"] = kwargs.get("soft_delete", False)
        
        return metadata

    @staticmethod
    def _handle_action_with_mapping(user, entity, action, action_mapping, request=None, **kwargs):
        """Generic handler for actions with mapping validation"""
        BusinessAuditLogger._validate_request_and_user(request, user)
        
        if action not in action_mapping:
            logger.warning(f"Unknown action: {action}")
            return None
        
        return action_mapping[action]

    @staticmethod
    def _finalize_and_create_audit(user, action_type, metadata, target_entity=None, is_security_event=False):
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

    @staticmethod
    @safe_audit_log
    def log_entry_workflow_action(
        user, entry, action, request=None, workflow_stage=None, **kwargs
    ):
        """Log entry workflow actions with rich business context"""
        # Map workflow actions to audit action types
        action_mapping = {
            "submit": AuditActionType.ENTRY_SUBMITTED,
            "approve": AuditActionType.ENTRY_APPROVED,
            "reject": AuditActionType.ENTRY_REJECTED,
        }

        action_type = BusinessAuditLogger._handle_action_with_mapping(
            user, entry, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata with workflow flag
        metadata = BusinessAuditLogger._build_base_metadata(action, request, **kwargs)
        metadata["workflow_action"] = True

        # Add entry-specific metadata
        if entry:
            metadata.update({
                "entry_id": str(entry.entry_id),
                "entry_description": entry.description,
                "entry_status": entry.status,
                "entry_amount": str(entry.amount) if entry.amount else None,
                "entry_currency": entry.currency,
                "workspace_id": BusinessAuditLogger._safe_get_related_field(
                    entry, "workspace.workspace_id", str
                ),
                "workspace_title": BusinessAuditLogger._safe_get_related_field(
                    entry, "workspace.title"
                ),
                "organization_id": BusinessAuditLogger._safe_get_related_field(
                    entry, "organization.organization_id", str
                ),
                "organization_title": BusinessAuditLogger._safe_get_related_field(
                    entry, "organization.title"
                ),
                "submitter_id": BusinessAuditLogger._safe_get_related_field(
                    entry, "submitter.organization_member_id", str
                ),
                "submitter_email": BusinessAuditLogger._safe_get_related_field(
                    entry, "submitter.user.email"
                ),
            })

        # Add workflow stage information
        if workflow_stage:
            metadata.update({
                "workflow_stage": workflow_stage,
                "stage_timestamp": timezone.now().isoformat(),
            })

        # Add action-specific metadata
        if action in ["submit", "resubmit"]:
            metadata.update({
                "submitter_id": str(user.user_id),
                "submitter_email": user.email,
                "submission_timestamp": timezone.now().isoformat(),
                "submission_notes": kwargs.get("notes", ""),
            })
        elif action in ["approve", "reject", "return"]:
            metadata.update({
                "reviewer_id": str(user.user_id),
                "reviewer_email": user.email,
                "review_timestamp": timezone.now().isoformat(),
                "review_notes": kwargs.get("notes", ""),
                "review_decision": action,
            })
        elif action == "withdraw":
            metadata.update({
                "withdrawer_id": str(user.user_id),
                "withdrawer_email": user.email,
                "withdrawal_timestamp": timezone.now().isoformat(),
                "withdrawal_reason": kwargs.get("reason", ""),
            })

        # Finalize and create audit log
        BusinessAuditLogger._finalize_and_create_audit(
            user, action_type, metadata, entry
        )

    @staticmethod
    @safe_audit_log
    def log_entry_action(user, entry, action, request=None, **kwargs):
        """Log entry workflow actions with rich business context"""
        action_mapping = {
            "submit": AuditActionType.ENTRY_SUBMITTED,
            "review": AuditActionType.ENTRY_REVIEWED,
            "approve": AuditActionType.ENTRY_APPROVED,
            "reject": AuditActionType.ENTRY_REJECTED,
            "flag": AuditActionType.ENTRY_FLAGGED,
            "unflag": AuditActionType.ENTRY_UNFLAGGED,
            "update": AuditActionType.ENTRY_UPDATED,
            "delete": AuditActionType.ENTRY_DELETED,
        }

        action_type = BusinessAuditLogger._handle_action_with_mapping(
            user, entry, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = BusinessAuditLogger._build_base_metadata(action, request, **kwargs)
        
        # Add entry-specific metadata
        if entry:
            metadata.update({
                "entry_id": str(entry.entry_id),
                "entry_type": entry.entry_type,
                "entry_amount": str(entry.amount) if hasattr(entry, "amount") else None,
                "workspace_id": BusinessAuditLogger._safe_get_related_field(
                    entry, "workspace.workspace_id", str
                ),
                "workspace_name": BusinessAuditLogger._safe_get_related_field(
                    entry, "workspace.title"
                ),
                "organization_id": BusinessAuditLogger._safe_get_related_field(
                    entry, "workspace.organization.organization_id", str
                ),
            })

        # Add action-specific metadata
        if action == "approve":
            metadata.update(
                {
                    "approver_id": str(user.user_id),
                    "approver_email": user.email,
                    "approval_notes": request.POST.get("notes", "")
                    if request
                    else kwargs.get("notes", ""),
                    "approval_level": request.POST.get("level", "standard")
                    if request
                    else kwargs.get("level", "standard"),
                    "approval_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "reject":
            metadata.update(
                {
                    "rejector_id": str(user.user_id),
                    "rejector_email": user.email,
                    "rejection_reason": request.POST.get("reason", "")
                    if request
                    else kwargs.get("reason", ""),
                    "rejection_notes": request.POST.get("notes", "")
                    if request
                    else kwargs.get("notes", ""),
                    "can_resubmit": request.POST.get("can_resubmit", True)
                    if request
                    else kwargs.get("can_resubmit", True),
                    "rejection_timestamp": timezone.now().isoformat(),
                }
            )
        elif action in ["flag", "unflag"]:
            metadata.update(
                {
                    "flag_reason": request.POST.get("reason", "")
                    if request
                    else kwargs.get("reason", ""),
                    "flag_notes": request.POST.get("notes", "")
                    if request
                    else kwargs.get("notes", ""),
                    "flag_severity": request.POST.get("severity", "medium")
                    if request
                    else kwargs.get("severity", "medium"),
                }
            )
        elif action == "update":
            metadata.update(
                {
                    "updater_id": str(user.user_id),
                    "updater_email": user.email,
                    "updated_fields": kwargs.get("updated_fields", []),
                    "original_values": kwargs.get("original_values", {}),
                    "new_values": kwargs.get("new_values", {}),
                    "update_reason": request.POST.get("reason", "")
                    if request
                    else kwargs.get("reason", ""),
                    "update_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "delete":
            metadata.update(
                {
                    "deleter_id": str(user.user_id),
                    "deleter_email": user.email,
                    "deletion_reason": request.POST.get("reason", "")
                    if request
                    else kwargs.get("reason", ""),
                    "soft_delete": kwargs.get("soft_delete", False),
                    "deletion_timestamp": timezone.now().isoformat(),
                    "entry_status_at_deletion": kwargs.get("entry_status", "unknown"),
                }
            )

        # Finalize and create audit log
        BusinessAuditLogger._finalize_and_create_audit(
            user, action_type, metadata, entry
        )

    @staticmethod
    @safe_audit_log
    def log_permission_change(
        user, target_user, permission, action, request=None, **kwargs
    ):
        """Log permission changes with full context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        if action not in ["grant", "revoke"]:
            logger.warning(f"Unknown permission action: {action}")
            return

        metadata = {
            "target_user_id": str(target_user.user_id),
            "target_user_email": target_user.user.email,
            "permission": permission,
            "action": action,
            "change_reason": request.POST.get("reason", "")
            if request
            else kwargs.get("reason", ""),
            "effective_date": request.POST.get(
                "effective_date", timezone.now().isoformat()
            )
            if request
            else kwargs.get("effective_date", timezone.now().isoformat()),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create_security_event(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED
            if action == "grant"
            else AuditActionType.PERMISSION_REVOKED,
            target_entity=target_user,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_data_export(
        user, export_type, filters, result_count, request=None, **kwargs
    ):
        """Log data export operations with detailed context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        # Ensure filters are JSON serializable
        serializable_filters = make_json_serializable(filters or {})

        metadata = {
            "export_type": export_type,
            "export_filters": serializable_filters,
            "result_count": result_count,
            "export_format": request.GET.get("format", "csv")
            if request
            else kwargs.get("format", "csv"),
            "export_reason": request.POST.get("reason", "business_analysis")
            if request
            else kwargs.get("reason", "business_analysis"),
            "file_size_estimate": f"{result_count * 100}B",  # Rough estimate
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.DATA_EXPORTED,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_bulk_operation(
        user, operation_type, affected_objects, request=None, **kwargs
    ):
        """Log bulk operations with sampling for large datasets"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        # Sample object IDs for large operations
        object_ids = []
        for obj in affected_objects:
            # Get the primary key value, handling different field names
            pk_field = obj._meta.pk.name
            pk_value = getattr(obj, pk_field)
            object_ids.append(str(pk_value))

        total_objects = len(object_ids)

        # Use AuditConfig values for threshold and sampling
        if total_objects > AuditConfig.BULK_OPERATION_THRESHOLD:
            # For large operations, sample only the first N objects
            sampled_ids = object_ids[: AuditConfig.BULK_SAMPLE_SIZE]
        else:
            # For small operations, include all object IDs
            sampled_ids = object_ids

        metadata = {
            "operation_type": operation_type,
            "total_objects": total_objects,
            "object_ids": sampled_ids,
            "operation_criteria": request.POST.get("criteria", "manual_selection")
            if request
            else kwargs.get("criteria", "manual_selection"),
            "batch_size": request.POST.get("batch_size", total_objects)
            if request
            else kwargs.get("batch_size", total_objects),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.BULK_OPERATION,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_status_change(user, entity, old_status, new_status, request=None, **kwargs):
        """Log status changes for any entity"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        metadata = {
            "entity_type": entity.__class__.__name__,
            "entity_id": str(getattr(entity, entity._meta.pk.name)),
            "old_status": old_status,
            "new_status": new_status,
            "status_change_reason": request.POST.get("reason", "")
            if request
            else kwargs.get("reason", ""),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.ENTRY_STATUS_CHANGED,
            target_entity=entity,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_file_operation(user, file_obj, operation, request=None, **kwargs):
        """Log file operations (upload, download, delete)"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        operation_mapping = {
            "upload": AuditActionType.FILE_UPLOADED,
            "download": AuditActionType.FILE_DOWNLOADED,
            "delete": AuditActionType.FILE_DELETED,
        }

        if operation not in operation_mapping:
            logger.warning(f"Unknown file operation: {operation}")
            return

        metadata = {
            "file_name": getattr(file_obj, "name", "unknown"),
            "file_size": getattr(file_obj, "size", 0),
            "file_type": getattr(file_obj, "content_type", "unknown"),
            "operation": operation,
            "file_category": kwargs.get("file_category", "general"),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
        }

        # Add operation-specific metadata
        if operation == "upload":
            metadata.update(
                {
                    "upload_source": request.POST.get("source", "web_interface")
                    if request
                    else kwargs.get("source", "web_interface"),
                    "upload_purpose": request.POST.get("purpose", "")
                    if request
                    else kwargs.get("purpose", ""),
                }
            )
        elif operation == "download":
            metadata.update(
                {
                    "download_reason": request.POST.get("reason", "")
                    if request
                    else kwargs.get("reason", ""),
                }
            )

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=operation_mapping[operation],
            target_entity=file_obj
            if hasattr(file_obj, "_meta") and hasattr(file_obj._meta, "pk")
            else None,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_organization_action(user, organization, action, request=None, **kwargs):
        """Log organization-specific actions with rich business context"""
        action_mapping = {
            "create": AuditActionType.ORGANIZATION_CREATED,
            "update": AuditActionType.ORGANIZATION_UPDATED,
            "delete": AuditActionType.ORGANIZATION_DELETED,
        }

        action_type = BusinessAuditLogger._handle_action_with_mapping(
            user, organization, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = BusinessAuditLogger._build_base_metadata(action, request, **kwargs)

        # Add organization-specific metadata
        if organization:
            metadata.update({
                "organization_id": str(organization.organization_id),
                "organization_title": organization.title,
                "organization_status": getattr(organization, "status", None),
                "organization_description": getattr(organization, "description", ""),
            })

        # Add CRUD action metadata
        metadata.update(BusinessAuditLogger._build_crud_action_metadata(
            user, action, request, **kwargs
        ))

        # Finalize and create audit log
        BusinessAuditLogger._finalize_and_create_audit(
            user, action_type, metadata, organization
        )

    @staticmethod
    @safe_audit_log
    def log_organization_exchange_rate_action(
        user, exchange_rate, action, request=None, **kwargs
    ):
        """Log organization exchange rate actions with rich business context"""
        # Custom action types for exchange rate operations
        action_mapping = {
            "create": AuditActionType.ORGANIZATION_UPDATED,  # Using existing action type
            "update": AuditActionType.ORGANIZATION_UPDATED,
            "delete": AuditActionType.ORGANIZATION_UPDATED,
        }

        action_type = BusinessAuditLogger._handle_action_with_mapping(
            user, exchange_rate, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = BusinessAuditLogger._build_base_metadata(action, request, **kwargs)
        metadata["operation_type"] = f"organization_exchange_rate_{action}"

        # Add exchange rate-specific metadata
        if exchange_rate:
            metadata.update({
                "exchange_rate_id": str(exchange_rate.pk),
                "organization_id": BusinessAuditLogger._safe_get_related_field(
                    exchange_rate, "organization.organization_id", str
                ),
                "currency_code": BusinessAuditLogger._safe_get_related_field(
                    exchange_rate, "currency.code"
                ),
                "rate": str(exchange_rate.rate),
                "effective_date": exchange_rate.effective_date.isoformat()
                if exchange_rate.effective_date
                else None,
                "note": exchange_rate.note,
            })

        # Add CRUD action metadata
        metadata.update(BusinessAuditLogger._build_crud_action_metadata(
            user, action, request, **kwargs
        ))

        # Finalize and create audit log
        BusinessAuditLogger._finalize_and_create_audit(
            user, action_type, metadata, exchange_rate
        )

    @staticmethod
    @safe_audit_log
    def log_team_action(user, team, action, request=None, **kwargs):
        """Log team-specific actions with rich business context"""
        action_mapping = {
            "create": AuditActionType.TEAM_CREATED,
            "update": AuditActionType.TEAM_UPDATED,
            "delete": AuditActionType.TEAM_DELETED,
        }

        action_type = BusinessAuditLogger._handle_action_with_mapping(
            user, team, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = BusinessAuditLogger._build_base_metadata(action, request, **kwargs)

        # Add team-specific metadata
        if team:
            metadata.update({
                "team_id": str(team.team_id),
                "team_title": team.title,
                "team_description": getattr(team, "description", ""),
                "organization_id": BusinessAuditLogger._safe_get_related_field(
                    team, "organization.organization_id", str
                ),
                "organization_title": BusinessAuditLogger._safe_get_related_field(
                    team, "organization.title"
                ),
                "workspace_id": BusinessAuditLogger._safe_get_related_field(
                    team, "workspace.workspace_id", str
                ),
                "workspace_title": BusinessAuditLogger._safe_get_related_field(
                    team, "workspace.title"
                ),
                "team_coordinator_id": BusinessAuditLogger._safe_get_related_field(
                    team, "team_coordinator.organization_member_id", str
                ),
                "team_coordinator_email": BusinessAuditLogger._safe_get_related_field(
                    team, "team_coordinator.user.email"
                ),
            })

        # Add CRUD action metadata
        metadata.update(BusinessAuditLogger._build_crud_action_metadata(
            user, action, request, **kwargs
        ))

        # Finalize and create audit log
        BusinessAuditLogger._finalize_and_create_audit(
            user, action_type, metadata, team
        )

    @staticmethod
    @safe_audit_log
    def log_team_member_action(user, team_member, action, request=None, **kwargs):
        """Log team member actions with rich business context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

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
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Add team member-specific metadata if team_member exists
        if team_member:
            metadata.update(
                {
                    "team_member_id": str(team_member.pk),
                    "team_id": str(team_member.team.team_id),
                    "team_title": team_member.team.title,
                    "organization_id": str(
                        team_member.team.organization.organization_id
                    ),
                    "organization_title": team_member.team.organization.title,
                    "member_user_id": str(team_member.organization_member.user.user_id),
                    "member_email": team_member.organization_member.user.email,
                    "member_role": team_member.role,
                    "workspace_id": str(team_member.team.workspace.workspace_id)
                    if hasattr(team_member.team, "workspace")
                    and team_member.team.workspace
                    else None,
                    "workspace_title": team_member.team.workspace.title
                    if hasattr(team_member.team, "workspace")
                    and team_member.team.workspace
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
                    "assigned_role": kwargs.get(
                        "role", team_member.role if team_member else None
                    ),
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
                    "new_role": kwargs.get(
                        "new_role", team_member.role if team_member else ""
                    ),
                    "role_change_reason": kwargs.get("reason", ""),
                }
            )

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=action_mapping[action],
            target_entity=team_member,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_workspace_action(user, workspace, action, request=None, **kwargs):
        """Log workspace-specific actions with rich business context"""
        action_mapping = {
            "create": AuditActionType.WORKSPACE_CREATED,
            "update": AuditActionType.WORKSPACE_UPDATED,
            "delete": AuditActionType.WORKSPACE_DELETED,
            "archive": AuditActionType.WORKSPACE_ARCHIVED,
            "activate": AuditActionType.WORKSPACE_ACTIVATED,
            "close": AuditActionType.WORKSPACE_CLOSED,
            "status_change": AuditActionType.WORKSPACE_STATUS_CHANGED,
        }

        action_type = BusinessAuditLogger._handle_action_with_mapping(
            user, workspace, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = BusinessAuditLogger._build_base_metadata(action, request, **kwargs)

        # Add workspace-specific metadata
        if workspace:
            metadata.update({
                "workspace_id": str(workspace.workspace_id),
                "workspace_title": workspace.title,
                "workspace_description": getattr(workspace, "description", ""),
                "workspace_status": getattr(workspace, "status", ""),
                "organization_id": BusinessAuditLogger._safe_get_related_field(
                    workspace, "organization.organization_id", str
                ),
                "organization_title": BusinessAuditLogger._safe_get_related_field(
                    workspace, "organization.title"
                ),
                "workspace_admin_id": BusinessAuditLogger._safe_get_related_field(
                    workspace, "workspace_admin.organization_member_id", str
                ),
                "workspace_admin_email": BusinessAuditLogger._safe_get_related_field(
                    workspace, "workspace_admin.user.email"
                ),
                "workspace_reviewer_id": BusinessAuditLogger._safe_get_related_field(
                    workspace, "operations_reviewer.organization_member_id", str
                ),
                "workspace_reviewer_email": BusinessAuditLogger._safe_get_related_field(
                    workspace, "operations_reviewer.user.email"
                ),
            })

        # Add CRUD action metadata
        metadata.update(BusinessAuditLogger._build_crud_action_metadata(
            user, action, request, **kwargs
        ))

        # Add status change specific metadata
        if action in ["archive", "activate", "close", "status_change"]:
            metadata.update({
                "modifier_id": str(user.user_id),
                "modifier_email": user.email,
                "modification_timestamp": timezone.now().isoformat(),
                "previous_status": kwargs.get("previous_status"),
                "new_status": kwargs.get("new_status"),
            })

        # Finalize and create audit log
        BusinessAuditLogger._finalize_and_create_audit(
            user, action_type, metadata, workspace
        )

    @staticmethod
    @safe_audit_log
    def log_workspace_team_action(
        user, workspace, team, action, request=None, **kwargs
    ):
        """Log workspace team operations with rich business context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

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
            **BusinessAuditLogger._extract_request_metadata(request),
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

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=action_mapping[action],
            target_entity=workspace,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_workspace_exchange_rate_action(
        user, exchange_rate, action, request=None, **kwargs
    ):
        """Log workspace exchange rate operations with rich business context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

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
            **BusinessAuditLogger._extract_request_metadata(request),
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

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=action_mapping[action],
            target_entity=exchange_rate,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_operation_failure(user, operation_type, error, request=None, **kwargs):
        """Log failed operations with error context"""
        if user and not user.is_authenticated:
            logger.warning("Cannot log operation failure for unauthenticated user")
            return

        metadata = {
            "operation_type": operation_type,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Add user info if available
        if user:
            metadata.update(
                {
                    "user_id": str(user.user_id),
                    "user_email": user.email,
                }
            )

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.SYSTEM_ERROR,
            metadata=serializable_metadata,
        )
