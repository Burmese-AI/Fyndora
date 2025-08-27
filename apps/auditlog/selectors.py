from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django.utils import timezone

from .config import AuditConfig
from .constants import AuditActionType, is_critical_action
from .models import AuditTrail
from .utils import is_security_related

User = get_user_model()


class AuditLogSelector:
    """
    Advanced selector class for audit log queries with filtering, pagination, and search capabilities.
    """

    @staticmethod
    def _apply_search_filters(search_query):
        """
        Apply search filters to audit logs based on search query.
        """
        search_conditions = Q()
        search_conditions |= Q(metadata__icontains=search_query)
        search_conditions |= Q(user__username__icontains=search_query)
        search_conditions |= Q(user__email__icontains=search_query)

        # Search in action type display names by checking each action type
        matching_action_types = []
        for action_type, display_name in AuditActionType.choices:
            if search_query.lower() in display_name.lower():
                matching_action_types.append(action_type)

        if matching_action_types:
            search_conditions |= Q(action_type__in=matching_action_types)

        return search_conditions

    @staticmethod
    def _get_related_entity_logs(
        entity_id: str, entity_type: str, base_qs: QuerySet
    ) -> QuerySet[AuditTrail]:
        """
        Get audit logs for entities related to the target entity.
        """
        related_conditions = Q()

        # 1. Find logs that reference this entity in their metadata
        related_conditions |= Q(
            metadata__contains={f"related_{entity_type.lower()}_id": entity_id}
        )
        related_conditions |= Q(
            metadata__contains={f"parent_{entity_type.lower()}_id": entity_id}
        )
        related_conditions |= Q(
            metadata__contains={f"child_{entity_type.lower()}_id": entity_id}
        )

        # 2. For workspace-scoped entities, include workspace-level changes
        if entity_type.lower() in ["entry", "organization", "team"]:
            # Get workspace_id from the original entity's metadata
            workspace_logs = (
                base_qs.filter(metadata__has_key="workspace_id")
                .values_list("metadata__workspace_id", flat=True)
                .distinct()
            )

            for workspace_id in workspace_logs:
                if workspace_id:
                    # Include workspace-level changes that might affect this entity
                    related_conditions |= Q(
                        metadata__workspace_id=workspace_id,
                        action_type__in=[
                            AuditActionType.WORKSPACE_STATUS_CHANGED,
                            AuditActionType.WORKSPACE_UPDATED,
                            AuditActionType.ORGANIZATION_STATUS_CHANGED,
                            AuditActionType.ORGANIZATION_UPDATED,
                        ],
                    )

        # 3. Entity-specific relationships
        if entity_type.lower() == "entry":
            # For entries, include related remittance and attachment changes
            related_conditions |= Q(metadata__contains={"entry_id": entity_id})
            related_conditions |= Q(
                target_entity_type__model__in=["remittance", "attachment"],
                metadata__contains={"related_entry_id": entity_id},
            )

        elif entity_type.lower() == "organization":
            # For organizations, include related workspace and team changes
            related_conditions |= Q(metadata__contains={"organization_id": entity_id})

        elif entity_type.lower() == "workspace":
            # For workspaces, include all entity changes within the workspace
            related_conditions |= Q(metadata__workspace_id=entity_id)

        elif entity_type.lower() == "user" or entity_type.lower() == "customuser":
            # For users, include invitation and team membership changes
            related_conditions |= Q(metadata__contains={"user_id": entity_id})
            related_conditions |= Q(metadata__contains={"invited_user_id": entity_id})
            # Also include logs where this user is the actor
            related_conditions |= Q(user_id=entity_id)

        # 4. Bulk operations that might have affected this entity
        related_conditions |= Q(
            action_type=AuditActionType.BULK_OPERATION,
            metadata__contains={f"affected_{entity_type.lower()}_ids": [entity_id]},
        )

        # Execute the query for related logs
        related_qs = AuditTrail.objects.filter(related_conditions)

        # Also include direct logs for this entity
        try:
            content_type = ContentType.objects.get(model=entity_type.lower())
            direct_conditions = Q(
                target_entity_id=entity_id, target_entity_type=content_type
            )
            # Combine both conditions with OR
            combined_conditions = related_conditions | direct_conditions
            related_qs = AuditTrail.objects.filter(combined_conditions)
        except ContentType.DoesNotExist:
            related_qs = AuditTrail.objects.filter(related_conditions)

        return related_qs.select_related("user", "target_entity_type")

    @staticmethod
    def get_audit_logs_with_filters(
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        action_types: Optional[List[str]] = None,
        start_date: Optional[Union[datetime, date]] = None,
        end_date: Optional[Union[datetime, date]] = None,
        target_entity_id: Optional[str] = None,
        target_entity_type: Optional[str] = None,
        target_entity_types: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        security_related_only: bool = False,
        critical_actions_only: bool = False,
        exclude_system_actions: bool = False,
        order_by: str = "-timestamp",
    ) -> QuerySet[AuditTrail]:
        """
        Get audit logs with comprehensive filtering options.
        """
        qs = AuditTrail.objects.select_related("user", "target_entity_type").all()

        # Workspace filtering
        if workspace_id:
            qs = qs.filter(metadata__workspace_id=workspace_id)

        # User filtering
        if user_id:
            qs = qs.filter(user_id=user_id)

        # Action type filtering
        if action_type:
            qs = qs.filter(action_type=action_type)
        elif action_types:
            qs = qs.filter(action_type__in=action_types)

        # Date range filtering
        if start_date:
            qs = qs.filter(timestamp__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__lte=end_date)

        # Target entity filtering
        if target_entity_id:
            qs = qs.filter(target_entity_id=target_entity_id)

        if target_entity_type:
            try:
                content_type = ContentType.objects.get(model=target_entity_type.lower())
                qs = qs.filter(target_entity_type=content_type)
            except ContentType.DoesNotExist:
                qs = qs.none()
        elif target_entity_types:
            content_types = ContentType.objects.filter(
                model__in=[t.lower() for t in target_entity_types]
            )
            qs = qs.filter(target_entity_type__in=content_types)

        # Advanced search
        if search_query:
            qs = qs.filter(AuditLogSelector._apply_search_filters(search_query))

        # Special filtering
        if security_related_only:
            security_actions = [
                action
                for action in AuditActionType.values
                if is_security_related(action)
            ]
            qs = qs.filter(action_type__in=security_actions)

        if critical_actions_only:
            critical_actions = [
                action
                for action in AuditActionType.values
                if is_critical_action(action)
            ]
            qs = qs.filter(action_type__in=critical_actions)

        if exclude_system_actions:
            qs = qs.exclude(user__isnull=True)

        return qs.order_by(order_by)


def get_retention_summary() -> Dict[str, int]:
    """
    Get a summary of audit logs by retention category.
    Read-only operation for retention statistics.
    """
    now = timezone.now()
    summary = {
        "total_logs": AuditTrail.objects.count(),
        "authentication_logs": 0,
        "critical_logs": 0,
        "default_logs": 0,
        "expired_logs": 0,
    }

    # Count by retention categories
    auth_actions = [
        AuditActionType.LOGIN_SUCCESS,
        AuditActionType.LOGIN_FAILED,
        AuditActionType.LOGOUT,
    ]

    # Count authentication logs
    summary["authentication_logs"] = AuditTrail.objects.filter(
        action_type__in=auth_actions
    ).count()

    # Count critical logs
    all_action_types = AuditTrail.objects.values_list(
        "action_type", flat=True
    ).distinct()
    critical_actions = [
        action for action in all_action_types if is_critical_action(action)
    ]
    summary["critical_logs"] = AuditTrail.objects.filter(
        action_type__in=critical_actions
    ).count()

    # Count default logs (non-auth, non-critical)
    summary["default_logs"] = (
        AuditTrail.objects.exclude(action_type__in=auth_actions)
        .exclude(action_type__in=critical_actions)
        .count()
    )

    # Count expired logs by category
    auth_cutoff = now - timedelta(days=AuditConfig.AUTHENTICATION_RETENTION_DAYS)
    critical_cutoff = now - timedelta(days=AuditConfig.CRITICAL_RETENTION_DAYS)
    default_cutoff = now - timedelta(days=AuditConfig.DEFAULT_RETENTION_DAYS)

    expired_auth = AuditTrail.objects.filter(
        action_type__in=auth_actions, timestamp__lt=auth_cutoff
    ).count()

    expired_critical = AuditTrail.objects.filter(
        action_type__in=critical_actions, timestamp__lt=critical_cutoff
    ).count()

    expired_default = (
        AuditTrail.objects.exclude(action_type__in=auth_actions)
        .exclude(action_type__in=critical_actions)
        .filter(timestamp__lt=default_cutoff)
        .count()
    )

    summary["expired_logs"] = expired_auth + expired_critical + expired_default

    return summary


def get_expired_logs_queryset(
    *, action_type: Optional[str] = None, override_days: Optional[int] = None
) -> QuerySet[AuditTrail]:
    """
    Get queryset of expired audit logs.
    Read-only operation for identifying expired logs.
    """
    now = timezone.now()

    # Authentication logs
    auth_actions = [
        AuditActionType.LOGIN_SUCCESS,
        AuditActionType.LOGIN_FAILED,
        AuditActionType.LOGOUT,
    ]

    # Critical actions
    critical_actions = [
        action for action in AuditActionType.values if is_critical_action(action)
    ]

    if override_days is not None:
        # Use override days for all logs
        cutoff = now - timedelta(days=override_days)
        if action_type:
            return AuditTrail.objects.filter(
                action_type=action_type, timestamp__lt=cutoff
            )
        else:
            return AuditTrail.objects.filter(timestamp__lt=cutoff)

    if action_type and action_type in auth_actions:
        # Only authentication logs of specific type
        auth_cutoff = now - timedelta(days=AuditConfig.AUTHENTICATION_RETENTION_DAYS)
        return AuditTrail.objects.filter(
            action_type=action_type, timestamp__lt=auth_cutoff
        )
    elif action_type and action_type in critical_actions:
        # Only critical logs of specific type
        critical_cutoff = now - timedelta(days=AuditConfig.CRITICAL_RETENTION_DAYS)
        return AuditTrail.objects.filter(
            action_type=action_type, timestamp__lt=critical_cutoff
        )
    elif (
        action_type
        and action_type not in auth_actions
        and action_type not in critical_actions
    ):
        # Only default logs of specific type
        default_cutoff = now - timedelta(days=AuditConfig.DEFAULT_RETENTION_DAYS)
        return AuditTrail.objects.filter(
            action_type=action_type, timestamp__lt=default_cutoff
        )
    else:
        # All expired logs
        auth_cutoff = now - timedelta(days=AuditConfig.AUTHENTICATION_RETENTION_DAYS)
        critical_cutoff = now - timedelta(days=AuditConfig.CRITICAL_RETENTION_DAYS)
        default_cutoff = now - timedelta(days=AuditConfig.DEFAULT_RETENTION_DAYS)

        expired_auth = Q(action_type__in=auth_actions, timestamp__lt=auth_cutoff)
        expired_critical = Q(
            action_type__in=critical_actions, timestamp__lt=critical_cutoff
        )
        expired_default = (
            Q(timestamp__lt=default_cutoff)
            & ~Q(action_type__in=auth_actions)
            & ~Q(action_type__in=critical_actions)
        )

        return AuditTrail.objects.filter(
            expired_auth | expired_critical | expired_default
        )
