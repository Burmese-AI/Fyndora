from django.db import transaction
from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.exceptions import OrganizationCreationError
from apps.core.utils import model_update


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

        return organization
    except Exception as e:
        raise OrganizationCreationError(f"Failed to create organization: {str(e)}")
