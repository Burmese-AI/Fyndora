from django.db import models


class WorkspacePermissions(models.TextChoices):
    """
    Permissions for the Workspace model.
    Permissions that are tied with workspace ID Object
    """

    CHANGE_WORKSPACE = (
        "change_workspace",
        "Can change workspace by WA and Org Owner",
    )
    DELETE_WORKSPACE = (
        "delete_workspace",
        "Can delete workspace by WA and Org Owner",
    )
    VIEW_WORKSPACE = (
        "view_workspace",
        "Can view workspace by WA and Org Owner",
    )
    ASSIGN_TEAMS = (
        "assign_teams",
        "Can assign teams to workspace by WA and Org Owner",
    )
    ADD_WORKSPACE_ENTRY = (
        "add_workspace_entry",
        "Can add workspace entry by WA and Org Owner",
    )
    CHANGE_WORKSPACE_ENTRY = (
        "change_workspace_entry",
        "Can change workspace entry by WA and Org Owner",
    )
    DELETE_WORKSPACE_ENTRY = (
        "delete_workspace_entry",
        "Can delete workspace entry by WA and Org Owner",
    )
    VIEW_WORKSPACE_ENTRY = (
        "view_workspace_entry",
        "Can view workspace entry by WA and Org Owner",
    )
    VIEW_WORKSPACE_CURRENCY = (
        "view_workspace_currency",
        "Can view workspace currency by WA and Org Owner",
    )
    ADD_WORKSPACE_CURRENCY = (
        "add_workspace_currency",
        "Can add workspace currency by WA and Org Owner",
    )
    CHANGE_WORKSPACE_CURRENCY = (
        "change_workspace_currency",
        "Can change workspace currency by WA and Org Owner",
    )
    DELETE_WORKSPACE_CURRENCY = (
        "delete_workspace_currency",
        "Can delete workspace currency by WA and Org Owner",
    )
    VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE = (
        "view_workspace_teams_under_workspace",
        "Can view workspace teams under workspace by WA ,OR,TC and Org Owner",
    )


class OrganizationPermissions(models.TextChoices):
    """
    Permissions for the Organization model.
    Permissions that are tied with organization ID Object
    """

    MANAGE_ORGANIZATION = (
        "manage_organization",
        "Can manage organization by higher level roles (Org Owner, WA, OR, TC)",
    )  # permission to enter into organization management page

    CHANGE_ORGANIZATION = (
        "change_organization",
        "Can change organization by Org Owner",
    )
    DELETE_ORGANIZATION = "delete_organization", "Can delete organization by Org Owner"
    VIEW_ORGANIZATION = "view_organization", "Can view organization by Org Owner"

    CHANGE_WORKSPACE_ADMIN = (
        "edit_workspace_admin",
        "Can edit workspace admin by Org Owner",  # can edit workspace admin
    )
    CHANGE_TEAM_COORDINATOR = (
        "change_team_coordinator",
        "Can change team coordinator by Org Owner",
    )

    ADD_WORKSPACE = (
        "add_workspace",
        "Can add workspace to organization by Org Owner",
    )  # can add workspace to organization # implemented
    ADD_TEAM = (
        "add_team",
        "Can add team to organization by Org Owner",
    )  # can add team to organization # implemented

    INVITE_ORG_MEMBER = (
        "invite_org_member",
        "Can invite org member to organization by Org Owner",  # can invite org member to organization # implemented
    )
    ADD_ORG_ENTRY = (
        "add_org_entry",
        "Can add org entry to organization by Org Owner",
    )  # can add org entry to organization # implemented
    VIEW_ORG_ENTRY = (
        "view_org_entry",
        "Can view org entry to organization by Org Owner",  # can view org entry to organization # implemented
    )
    CHANGE_ORG_ENTRY = (
        "change_org_entry",
        "Can change org entry to organization by Org Owner",  # can change org entry to organization # implemented
    )
    DELETE_ORG_ENTRY = (
        "delete_org_entry",
        "Can delete org entry to organization by Org Owner",  # can delete org entry to organization # implemented
    )
    ADD_ORG_CURRENCY = (
        "add_org_currency",
        "Can add org currency to organization only by Org Owner",
    )
    CHANGE_ORG_CURRENCY = (
        "change_org_currency",
        "Can change org currency to organization only by Org Owner",
    )
    DELETE_ORG_CURRENCY = (
        "delete_org_currency",
        "Can delete org currency to organization only by Org Owner",
    )
    VIEW_REPORT_PAGE = (
        "view_report_page",
        "Can view report page by Org Owner",
    )


class TeamPermissions(models.TextChoices):
    """
    Permissions for the Team model.
    Permissions that are tied with team ID Object
    """

    CHANGE_TEAM = (
        "change_team",
        "Can change team by Team Admin and Org Owner",
    )  # can change team # implemented
    DELETE_TEAM = "delete_team", "Can delete team by Team Admin and Org Owner"
    VIEW_TEAM = "view_team", "Can view team by Team Admin and Org Owner"
    ADD_TEAM_MEMBER = (
        "add_team_member",
        "Can add team member by Team Admin and Org Owner",
    )


class WorkspaceTeamPermissions(models.TextChoices):
    """
    Permissions for the WorkspaceTeam model.
    Permissions that are tied with workspace team ID Object
    """

    VIEW_WORKSPACE_TEAM = (
        "view_workspace_team",
        "Can view workspace team by Assigned WA and Org Owner",
    )
    ADD_WORKSPACE_TEAM_ENTRY = (
        "add_workspace_team_entry",
        "Can add workspace team entry by Submitter and Org Owner",
    )
    CHANGE_WORKSPACE_TEAM_ENTRY = (
        "change_workspace_team_entry",
        "Can change workspace team entry by Submitter and Org Owner",
    )
    DELETE_WORKSPACE_TEAM_ENTRY = (
        "delete_workspace_team_entry",
        "Can delete workspace team entry by Submitter and Org Owner",
    )


class EntryPermissions(models.TextChoices):
    """
    Permissions for the Entry model.
    Permissions that are tied with entry ID Object
    """

    CHANGE_OTHER_SUBMITTERS_ENTRY = (
        "change_other_submitters_entry",
        "Can change other submitters entry",
    )
