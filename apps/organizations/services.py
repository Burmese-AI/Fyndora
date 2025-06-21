from django.db import transaction
from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.exceptions import (
    OrganizationCreationError,
    OrganizationUpdateError,
)
from apps.core.utils import model_update
from django.contrib.auth.models import Permission
from apps.organizations.exceptions import OrganizationPermissionCreationError
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

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
        assign_perm("edit_organization", user, organization)
        
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
