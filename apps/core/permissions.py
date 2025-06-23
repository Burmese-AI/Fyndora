class Permissions:
    """
    Permission constants for role-based access control.
    """

    # Workspace permissions
    CREATE_WORKSPACE = "create_workspace"
    ASSIGN_TEAMS = "assign_teams"
    CONFIG_DEADLINES = "config_deadlines"
    VIEW_WORKSPACE = "view_workspace"
    SUBMIT_ENTRIES = "submit_entries"
    UPLOAD_ATTACHMENTS = "upload_attachments"
    EDIT_ENTRIES = "edit_entries"
    REVIEW_ENTRIES = "review_entries"
    FLAG_ENTRIES = "flag_entries"
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    LOCK_WORKSPACE = "lock_workspace"

    # Organization permissions
    EDIT_ORGANIZATION = "edit_organization"
    DELETE_ORGANIZATION = "delete_organization"
