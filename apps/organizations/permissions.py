from django.db import models


class OrganizationPermissions(models.TextChoices):
    """
    Permissions for the Organization model.
    """

    CHANGE_ORGANIZATION = "change_organization"
    DELETE_ORGANIZATION = "delete_organization"
    VIEW_ORGANIZATION = "view_organization"

    ADD_WORKSPACE = "add_workspace" #can add workspace to organization
