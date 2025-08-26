"""Organization-specific audit logger for organization and exchange rate operations."""

import logging
from typing import Dict, Optional

from django.contrib.auth.models import User
from django.http import HttpRequest

from apps.auditlog.constants import AuditActionType
from apps.auditlog.utils import safe_audit_log
from apps.organizations.models import Organization, OrganizationExchangeRate

from .base_logger import BaseAuditLogger
from .metadata_builders import (
    EntityMetadataBuilder,
    UserActionMetadataBuilder,
)

logger = logging.getLogger(__name__)


class OrganizationAuditLogger(BaseAuditLogger):
    """Audit logger for organization-related operations."""

    def get_supported_actions(self) -> Dict[str, str]:
        """Return mapping of supported organization actions to audit action types."""
        return {
            "create": AuditActionType.ORGANIZATION_CREATED,
            "update": AuditActionType.ORGANIZATION_UPDATED,
            "delete": AuditActionType.ORGANIZATION_DELETED,
        }

    def get_logger_name(self) -> str:
        """Return the name of this logger for identification."""
        return "organization_logger"

    @safe_audit_log
    def log_organization_action(
        self,
        user: User,
        organization: Organization,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log organization-specific actions with rich business context."""
        action_type = self._handle_action_with_mapping(
            user, organization, action, self.get_supported_actions(), request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = self._build_base_metadata(action, request, **kwargs)

        # Add organization-specific metadata
        metadata.update(EntityMetadataBuilder.build_organization_metadata(organization))

        # Add CRUD action metadata
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
        workspace = getattr(organization, 'workspace', None)
        self._finalize_and_create_audit(user, action_type, metadata, organization, workspace)

    @safe_audit_log
    def log_organization_exchange_rate_action(
        self,
        user: User,
        exchange_rate: OrganizationExchangeRate,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log organization exchange rate actions with rich business context."""
        # Custom action types for exchange rate operations
        action_mapping = {
            "create": AuditActionType.ORGANIZATION_EXCHANGE_RATE_CREATED,
            "update": AuditActionType.ORGANIZATION_EXCHANGE_RATE_UPDATED,
            "delete": AuditActionType.ORGANIZATION_EXCHANGE_RATE_DELETED,
        }

        action_type = self._handle_action_with_mapping(
            user, exchange_rate, action, action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = self._build_base_metadata(action, request, **kwargs)
        metadata["operation_type"] = f"organization_exchange_rate_{action}"

        # Add organization-specific metadata
        organization = getattr(exchange_rate, 'organization', None)
        if organization:
            metadata.update(EntityMetadataBuilder.build_organization_metadata(organization))

        # Add exchange rate-specific metadata
        if exchange_rate:
            metadata.update(
                {
                    "exchange_rate_id": str(exchange_rate.pk),
                    "organization_id": self._safe_get_related_field(
                        exchange_rate, "organization.organization_id", str
                    ),
                    "currency_code": self._safe_get_related_field(
                        exchange_rate, "currency.code"
                    ),
                    "rate": str(exchange_rate.rate),
                    "effective_date": exchange_rate.effective_date.isoformat()
                    if exchange_rate.effective_date
                    else None,
                    "note": getattr(exchange_rate, "note", ""),
                }
            )

        # Add CRUD action metadata
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
        workspace = getattr(exchange_rate, 'workspace', None)
        self._finalize_and_create_audit(user, action_type, metadata, exchange_rate, workspace)
