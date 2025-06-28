from django.db import models


class OrganizationPermissions(models.TextChoices):
    """
    Permissions for the Organization model.
    """

    CHANGE_ORGANIZATION = "organizations.change_organization", "Can change organization"
    DELETE_ORGANIZATION = "organizations.delete_organization", "Can delete organization"
    VIEW_ORGANIZATION = "organizations.view_organization", "Can view organization"
