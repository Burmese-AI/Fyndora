from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone

from .config import AuditConfig
from .constants import AuditActionType, is_critical_action
from .models import AuditTrail
from .utils import get_action_category, is_security_related

User = get_user_model()


class AuditLogSelector:
    """
    Advanced selector class for audit log queries with filtering, pagination, and search capabilities.
    """

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

        elif entity_type.lower() == "user":
            # For users, include invitation and team membership changes
            related_conditions |= Q(metadata__contains={"user_id": entity_id})
            related_conditions |= Q(metadata__contains={"invited_user_id": entity_id})

        # 4. Bulk operations that might have affected this entity
        related_conditions |= Q(
            action_type=AuditActionType.BULK_OPERATION,
            metadata__contains={f"affected_{entity_type.lower()}_ids": [entity_id]},
        )

        # Execute the query for related logs, excluding the base entity logs
        related_qs = (
            AuditTrail.objects.filter(related_conditions)
            .exclude(
                target_entity_id=entity_id,
                target_entity_type__model=entity_type.lower(),
            )
            .select_related("user", "target_entity_type")
        )

        return related_qs

    @staticmethod
    def get_audit_logs_with_filters(
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        action_types: Optional[List[str]] = None,
        action_category: Optional[str] = None,
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

        # Action category filtering
        if action_category:
            category_actions = AuditLogSelector._get_actions_by_category(
                action_category
            )
            if category_actions:
                qs = qs.filter(action_type__in=category_actions)

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
            qs = AuditLogSelector._apply_search_filters(qs, search_query)

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

    # ========================================
    # CONVENIENT SPECIALIZED METHODS
    # ========================================

    @staticmethod
    def get_workspace_logs(workspace_id: str, days: int = 30) -> QuerySet[AuditTrail]:
        """Get all audit logs for a specific workspace."""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLogSelector.get_audit_logs_with_filters(
            workspace_id=workspace_id,
            start_date=start_date,
        )

    @staticmethod
    def get_user_logs(user_id: str, days: int = 30) -> QuerySet[AuditTrail]:
        """Get all audit logs for a specific user."""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLogSelector.get_audit_logs_with_filters(
            user_id=user_id,
            start_date=start_date,
            exclude_system_actions=True,
        )

    @staticmethod
    def get_authentication_logs(
        days: int = 7, failed_only: bool = False
    ) -> QuerySet[AuditTrail]:
        """Get authentication-related audit logs."""
        start_date = timezone.now() - timedelta(days=days)

        if failed_only:
            action_types = [AuditActionType.LOGIN_FAILED]
        else:
            action_types = [
                AuditActionType.LOGIN_SUCCESS,
                AuditActionType.LOGIN_FAILED,
                AuditActionType.LOGOUT,
            ]

        return AuditLogSelector.get_audit_logs_with_filters(
            start_date=start_date,
            action_types=action_types,
        )

    @staticmethod
    def get_entity_logs(entity_id: str, entity_type: str) -> QuerySet[AuditTrail]:
        """Get all audit logs for a specific entity (simplified version)."""
        return AuditLogSelector.get_audit_logs_with_filters(
            target_entity_id=entity_id,
            target_entity_type=entity_type,
        )

    @staticmethod
    def get_critical_logs(
        days: int = 7, workspace_id: Optional[str] = None
    ) -> QuerySet[AuditTrail]:
        """Get critical audit logs for monitoring."""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLogSelector.get_audit_logs_with_filters(
            workspace_id=workspace_id,
            start_date=start_date,
            critical_actions_only=True,
        )

    @staticmethod
    def get_security_logs(
        days: int = 7, workspace_id: Optional[str] = None
    ) -> QuerySet[AuditTrail]:
        """Get security-related audit logs for monitoring."""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLogSelector.get_audit_logs_with_filters(
            workspace_id=workspace_id,
            start_date=start_date,
            security_related_only=True,
        )

    @staticmethod
    def get_crud_logs(
        entity_type: str, operation: str = None, days: int = 30
    ) -> QuerySet[AuditTrail]:
        """
        Get CRUD operation logs for a specific entity type.
        """
        start_date = timezone.now() - timedelta(days=days)

        if operation:
            # Build action type based on entity and operation
            action_type = f"{entity_type.lower()}_{operation.lower()}"
            return AuditLogSelector.get_audit_logs_with_filters(
                start_date=start_date,
                action_type=action_type,
                target_entity_type=entity_type,
            )
        else:
            return AuditLogSelector.get_audit_logs_with_filters(
                start_date=start_date,
                target_entity_type=entity_type,
            )

    @staticmethod
    def search_logs(
        query: str, workspace_id: Optional[str] = None, days: int = 30
    ) -> QuerySet[AuditTrail]:
        """Simple search interface for audit logs."""
        start_date = timezone.now() - timedelta(days=days)
        return AuditLogSelector.get_audit_logs_with_filters(
            workspace_id=workspace_id,
            start_date=start_date,
            search_query=query,
        )

    # ========================================
    # PAGINATION AND UTILITY METHODS
    # ========================================

    @staticmethod
    def get_paginated_audit_logs(
        page: int = 1, per_page: int = 25, **filter_kwargs
    ) -> Dict[str, Any]:
        """
        Get paginated audit logs with filtering.
        """
        qs = AuditLogSelector.get_audit_logs_with_filters(**filter_kwargs)
        paginator = Paginator(qs, per_page)

        page_obj = paginator.get_page(page)

        return {
            "audit_logs": page_obj.object_list,
            "page": page_obj.number,
            "per_page": per_page,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "previous_page": page_obj.previous_page_number()
            if page_obj.has_previous()
            else None,
        }

    @staticmethod
    def get_recent_audit_logs(
        limit: int = 10,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> QuerySet[AuditTrail]:
        """Get recent audit logs for dashboard/overview purposes."""
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if workspace_id:
            filters["workspace_id"] = workspace_id

        return AuditLogSelector.get_audit_logs_with_filters(**filters)[:limit]

    @staticmethod
    def get_user_activity_logs(
        user_id: str,
        days: int = 30,
        action_categories: Optional[List[str]] = None,
    ) -> QuerySet[AuditTrail]:
        """Get user activity logs for a specific time period."""
        start_date = timezone.now() - timedelta(days=days)

        filters = {
            "user_id": user_id,
            "start_date": start_date,
            "exclude_system_actions": True,
        }

        if action_categories:
            # Get actions for all specified categories
            all_actions = []
            for category in action_categories:
                all_actions.extend(AuditLogSelector._get_actions_by_category(category))
            filters["action_types"] = all_actions

        return AuditLogSelector.get_audit_logs_with_filters(**filters)

    @staticmethod
    def get_entity_audit_history(
        entity_id: str,
        entity_type: str,
        include_related: bool = False,
    ) -> QuerySet[AuditTrail]:
        """
        Get complete audit history for a specific entity.
        """
        filters = {
            "target_entity_id": entity_id,
            "target_entity_type": entity_type,
        }

        qs = AuditLogSelector.get_audit_logs_with_filters(**filters)

        if include_related:
            # Include related entity changes based on metadata relationships
            related_qs = AuditLogSelector._get_related_entity_logs(
                entity_id, entity_type, qs
            )
            qs = qs.union(related_qs, all=True).order_by("-timestamp")

        return qs

    @staticmethod
    def get_security_audit_logs(
        days: int = 7,
        workspace_id: Optional[str] = None,
    ) -> QuerySet[AuditTrail]:
        """Get security-related audit logs for monitoring."""
        start_date = timezone.now() - timedelta(days=days)

        return AuditLogSelector.get_audit_logs_with_filters(
            workspace_id=workspace_id,
            start_date=start_date,
            security_related_only=True,
        )

    @staticmethod
    def search_audit_logs(
        query: str, search_fields: Optional[List[str]] = None, **filter_kwargs
    ) -> QuerySet[AuditTrail]:
        """
        Advanced search in audit logs.
        """
        if not search_fields:
            search_fields = ["metadata", "action_type", "user__username", "user__email"]

        filters = {"search_query": query, **filter_kwargs}
        return AuditLogSelector.get_audit_logs_with_filters(**filters)

    @staticmethod
    def _apply_search_filters(qs: QuerySet, search_query: str) -> QuerySet:
        """Apply advanced search filters to queryset."""
        search_terms = search_query.split()

        for term in search_terms:
            # Create OR conditions for different search fields
            search_conditions = Q()

            # Search in metadata
            search_conditions |= Q(metadata__icontains=term)

            # Search in action type display names
            for action_type in AuditActionType.choices:
                if term.lower() in action_type[1].lower():
                    search_conditions |= Q(action_type=action_type[0])

            # Search in user information
            search_conditions |= Q(user__username__icontains=term)
            search_conditions |= Q(user__email__icontains=term)

            qs = qs.filter(search_conditions)

        return qs

    @staticmethod
    def _get_actions_by_category(category: str) -> List[str]:
        """Get all action types for a specific category."""
        return [
            action
            for action in AuditActionType.values
            if get_action_category(action) == category
        ]


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


def get_logs_approaching_expiry(*, days_warning: int = 7) -> Dict[str, List]:
    """
    Get logs that will expire within the warning period.
    Read-only operation for retention monitoring.
    """
    now = timezone.now()

    # Calculate warning dates
    auth_warning_date = now - timedelta(
        days=AuditConfig.AUTHENTICATION_RETENTION_DAYS - days_warning
    )
    default_warning_date = now - timedelta(
        days=AuditConfig.DEFAULT_RETENTION_DAYS - days_warning
    )

    auth_actions = [
        AuditActionType.LOGIN_SUCCESS,
        AuditActionType.LOGIN_FAILED,
        AuditActionType.LOGOUT,
    ]

    approaching_expiry = {
        "authentication_logs": list(
            AuditTrail.objects.filter(
                action_type__in=auth_actions,
                timestamp__lt=auth_warning_date,
                timestamp__gte=now
                - timedelta(days=AuditConfig.AUTHENTICATION_RETENTION_DAYS),
            ).values("audit_id", "action_type", "timestamp", "user__username")
        ),
        "default_logs": list(
            AuditTrail.objects.exclude(action_type__in=auth_actions)
            .filter(
                timestamp__lt=default_warning_date,
                timestamp__gte=now - timedelta(days=AuditConfig.DEFAULT_RETENTION_DAYS),
            )
            .values("audit_id", "action_type", "timestamp", "user__username")
        ),
    }

    return approaching_expiry


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


def get_retention_statistics_by_action_type() -> Dict[str, Dict[str, int]]:
    """
    Get detailed retention statistics grouped by action type.
    Read-only operation for detailed retention analysis.
    """
    now = timezone.now()
    stats = {}

    # Get all action types with counts
    action_counts = AuditTrail.objects.values("action_type").annotate(
        total=models.Count("audit_id")
    )

    for item in action_counts:
        action_type = item["action_type"]
        total_count = item["total"]

        # Calculate retention period for this action type
        retention_days = AuditConfig.get_retention_days_for_action(action_type)
        cutoff_date = now - timedelta(days=retention_days)

        # Count expired logs for this action type
        expired_count = AuditTrail.objects.filter(
            action_type=action_type, timestamp__lt=cutoff_date
        ).count()

        stats[action_type] = {
            "total": total_count,
            "expired": expired_count,
            "active": total_count - expired_count,
            "retention_days": retention_days,
        }

    return stats
