import logging

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from guardian.shortcuts import assign_perm

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.core.roles import get_permissions_for_role
from apps.core.utils import model_update
from apps.currencies.models import Currency
from apps.organizations.exceptions import (
    OrganizationCreationError,
    OrganizationUpdateError,
)
from apps.organizations.models import Organization, OrganizationMember

from .models import OrganizationExchangeRate
from .utils import (
    extract_organization_context,
    extract_organization_exchange_rate_context,
    extract_organization_member_context,
    extract_request_metadata,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def create_organization_with_owner(*, form, user) -> Organization:
    """
    Creates a new organization and sets up the owner.

    Args:
        form: OrganizationForm instance
        user: User instance who will be the owner

    Returns:
        Organization: The created organization instance

    Raises:
        OrganizationCreationError: If organization creation fails
    """
    try:
        # Create the organization
        organization = form.save(commit=False)
        organization.save()

        # Create organization member for the owner
        owner_member = OrganizationMember.objects.create(
            organization=organization, user=user, is_active=True
        )

        # Set the owner using model_update from core.utils
        organization = model_update(
            instance=organization, data={"owner": owner_member}, update_fields=["owner"]
        )
        org_owner_group, _ = Group.objects.get_or_create(
            name=f"Org Owner - {organization.organization_id}"
        )

        # getting the permissions for the org owner
        org_owner_permissions = get_permissions_for_role("ORG_OWNER")

        # Assign permissions to the org owner group
        for perm in org_owner_permissions:
            if "workspace_currency" not in perm:
                assign_perm(perm, org_owner_group, organization)

        # Assign the org owner group to the user
        org_owner_group.user_set.add(user)

        # Audit logging: Log organization creation with owner assignment
        try:
            BusinessAuditLogger.log_permission_change(
                user=user,
                target_user=user,
                permission="organization.owner",
                action="grant",
                request=None,  # No request context available in service layer
                organization_id=str(organization.organization_id),
                organization_title=organization.title,
                role="owner",
                operation_type="organization_creation_with_owner",
                business_context=extract_organization_context(organization),
                member_context=extract_organization_member_context(owner_member),
            )
        except Exception as audit_error:
            # Log audit failure but don't break the main operation
            logger.error(
                f"Audit logging failed for organization creation: {audit_error}",
                exc_info=True,
            )

        # Get all permissions assigned to the org owner group
        return organization
    except Exception as e:
        # Audit logging: Log failed organization creation
        try:
            BusinessAuditLogger.log_operation_failure(
                user=user,
                operation_type="organization_creation_with_owner_failed",
                error=e,
                request=None,
                title=getattr(form.instance, "title", "unknown"),
                owner_id=str(user.user_id),
                owner_email=user.email,
                **extract_request_metadata(),
            )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for organization creation error: {audit_error}",
                exc_info=True,
            )

        raise OrganizationCreationError(f"Failed to create organization: {str(e)}")


def update_organization_from_form(*, form, organization, user) -> Organization:
    """
    Updates an organization from a form.
    """
    try:
        # Validate the form first
        if not form.is_valid():
            raise OrganizationUpdateError(f"Form validation failed: {form.errors}")

        # Capture original status for audit logging
        original_status = getattr(organization, "status", None)

        organization = model_update(organization, form.cleaned_data)

        # Audit logging: Log organization update
        try:
            if user:
                # Log status change if status was modified
                if (
                    "status" in form.cleaned_data
                    and original_status != organization.status
                ):
                    BusinessAuditLogger.log_status_change(
                        user=user,
                        entity=organization,
                        old_status=original_status,
                        new_status=organization.status,
                        request=None,
                        organization_id=str(organization.organization_id),
                        change_reason="Organization status updated via form",
                        operation_type="organization_status_change",
                        business_context=extract_organization_context(organization),
                    )

                # Log general update operation
                BusinessAuditLogger.log_organization_action(
                    user=user,
                    organization=organization,
                    action="update",
                    request=None,
                    operation_type="organization_form_update",
                    updated_fields=list(form.cleaned_data.keys()),
                    business_context=extract_organization_context(organization),
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for organization update: {audit_error}",
                exc_info=True,
            )

        return organization
    except Exception as e:
        # Audit logging: Log failed update
        try:
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="organization_form_update_failed",
                    error=e,
                    request=None,
                    organization_id=str(organization.organization_id),
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for organization update error: {audit_error}",
                exc_info=True,
            )

        raise OrganizationUpdateError(f"Failed to update organization: {str(e)}")


@transaction.atomic
def create_organization_exchange_rate(
    *, organization, organization_member, currency_code, rate, note, effective_date
):
    """
    Creates an exchange rate for an organization.
    """
    try:
        currency, _ = Currency.objects.get_or_create(code=currency_code)
        exchange_rate = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=rate,
            effective_date=effective_date,
            added_by=organization_member,
            note=note,
        )

        # Audit logging: Log exchange rate creation
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_organization_exchange_rate_action(
                    user=user,
                    exchange_rate=exchange_rate,
                    action="create",
                    request=None,
                    organization_id=str(organization.organization_id),
                    organization_title=organization.title,
                    currency_code=currency_code,
                    rate=str(rate),
                    effective_date=effective_date.isoformat()
                    if effective_date
                    else None,
                    note=note,
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate creation: {audit_error}",
                exc_info=True,
            )

    except IntegrityError as e:
        # Audit logging: Log failed exchange rate creation
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="organization_exchange_rate_creation_failed",
                    error=e,
                    request=None,
                    organization_id=str(organization.organization_id),
                    currency_code=currency_code,
                    rate=str(rate),
                    error_type="IntegrityError",
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate creation error: {audit_error}",
                exc_info=True,
            )

        raise ValidationError(f"IntegrityError: {str(e)}")

    except Exception as err:
        # Audit logging: Log failed exchange rate creation
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="organization_exchange_rate_creation_failed",
                    error=err,
                    request=None,
                    organization_id=str(organization.organization_id),
                    currency_code=currency_code,
                    rate=str(rate),
                    error_type=type(err).__name__,
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate creation error: {audit_error}",
                exc_info=True,
            )

        raise ValidationError(
            f"Failed to create organization exchange rate: {str(err)}"
        )


def update_organization_exchange_rate(
    *, organization, organization_member, org_exchange_rate, note
):
    try:
        # Capture original note for audit logging
        original_note = org_exchange_rate.note

        org_exchange_rate = model_update(
            instance=org_exchange_rate,
            data={"note": note},
            update_fields=["note"],
        )

        # Audit logging: Log exchange rate update
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_organization_exchange_rate_action(
                    user=user,
                    exchange_rate=org_exchange_rate,
                    action="update",
                    request=None,
                    organization_id=str(organization.organization_id),
                    organization_title=organization.title,
                    currency_code=org_exchange_rate.currency.code,
                    rate=str(org_exchange_rate.rate),
                    original_note=original_note,
                    new_note=note,
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate update: {audit_error}",
                exc_info=True,
            )

        return org_exchange_rate
    except Exception as err:
        # Audit logging: Log failed exchange rate update
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="organization_exchange_rate_update_failed",
                    error=err,
                    request=None,
                    organization_id=str(organization.organization_id),
                    exchange_rate_id=str(org_exchange_rate.id),
                    error_type=type(err).__name__,
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate update error: {audit_error}",
                exc_info=True,
            )

        raise ValidationError(
            f"Failed to update organization exchange rate: {str(err)}"
        )


def delete_organization_exchange_rate(
    *, organization, organization_member, org_exchange_rate
):
    try:
        # Capture exchange rate data for audit logging before deletion
        exchange_rate_context = extract_organization_exchange_rate_context(
            org_exchange_rate
        )

        org_exchange_rate.delete()

        # Audit logging: Log exchange rate deletion
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_organization_exchange_rate_action(
                    user=user,
                    exchange_rate=None,  # Entity is deleted
                    action="delete",
                    request=None,
                    organization_id=str(organization.organization_id),
                    organization_title=organization.title,
                    deleted_exchange_rate_context=exchange_rate_context,
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate deletion: {audit_error}",
                exc_info=True,
            )

        return True
    except Exception as err:
        # Audit logging: Log failed exchange rate deletion
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="organization_exchange_rate_deletion_failed",
                    error=err,
                    request=None,
                    organization_id=str(organization.organization_id),
                    exchange_rate_id=str(org_exchange_rate.id),
                    error_type=type(err).__name__,
                    **extract_request_metadata(),
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for exchange rate deletion error: {audit_error}",
                exc_info=True,
            )

        raise ValidationError(
            f"Failed to delete organization exchange rate: {str(err)}"
        )
