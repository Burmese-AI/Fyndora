from django.db import transaction
from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.exceptions import (
    OrganizationCreationError,
    OrganizationUpdateError,
)
from guardian.shortcuts import assign_perm
from .permissions import OrganizationPermissions
from apps.core.utils import model_update
from apps.currencies.models import Currency
from .models import OrganizationExchangeRate
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from apps.core.roles import get_permissions_for_role


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
        print(org_owner_permissions)

        # Assign permissions to the org owner group
        for perm in org_owner_permissions:
            assign_perm(perm, org_owner_group, organization)

        # Assign the org owner group to the user
        org_owner_group.user_set.add(user)

        return organization
    except Exception as e:
        raise OrganizationCreationError(f"Failed to create organization: {str(e)}")


def update_organization_from_form(*, form, organization) -> Organization:
    """
    Updates an organization from a form.
    """
    try:
        organization = model_update(organization, form.cleaned_data)
        return organization
    except Exception as e:
        raise OrganizationUpdateError(f"Failed to update organization: {str(e)}")


def create_organization_exchange_rate(*, organization, organization_member, currency_code, rate, note, effective_date):
    """
    Creates an exchange rate for an organization.
    """
    try:
        currency = Currency.objects.get_or_create(code=currency_code)
        OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=rate,
            effective_date=effective_date,
            added_by=organization_member,
            note=note,
        )

    except IntegrityError as e:
        raise ValidationError(f"IntegrityError: {str(e)}")

    except Exception as err:
        raise ValidationError(f"Failed to create organization exchange rate: {str(err)}")