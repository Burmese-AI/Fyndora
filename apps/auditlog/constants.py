from django.db import models


class AuditActionType(models.TextChoices):
    # Authentication & Authorization
    LOGIN_SUCCESS = "login_success", "Login Success"
    LOGIN_FAILED = "login_failed", "Login Failed"
    LOGOUT = "logout", "Logout"
    PASSWORD_CHANGED = "password_changed", "Password Changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password Reset Requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed", "Password Reset Completed"

    # User Management
    USER_CREATED = "user_created", "User Created"
    USER_UPDATED = "user_updated", "User Updated"
    USER_DELETED = "user_deleted", "User Deleted"
    USER_PROFILE_UPDATED = "user_profile_updated", "User Profile Updated"

    # Organization Management
    ORGANIZATION_CREATED = "organization_created", "Organization Created"
    ORGANIZATION_UPDATED = "organization_updated", "Organization Updated"
    ORGANIZATION_DELETED = "organization_deleted", "Organization Deleted"
    ORGANIZATION_STATUS_CHANGED = (
        "organization_status_changed",
        "Organization Status Changed",
    )
    ORGANIZATION_ARCHIVED = "organization_archived", "Organization Archived"
    ORGANIZATION_ACTIVATED = "organization_activated", "Organization Activated"
    ORGANIZATION_CLOSED = "organization_closed", "Organization Closed"

    # Organization Member Management
    ORGANIZATION_MEMBER_ADDED = "organization_member_added", "Organization Member Added"
    ORGANIZATION_MEMBER_REMOVED = (
        "organization_member_removed",
        "Organization Member Removed",
    )
    ORGANIZATION_MEMBER_ROLE_CHANGED = (
        "organization_member_role_changed",
        "Organization Member Role Changed",
    )
    ORGANIZATION_MEMBER_UPDATED = (
        "organization_member_updated",
        "Organization Member Updated",
    )

    # Workspace Management
    WORKSPACE_CREATED = "workspace_created", "Workspace Created"
    WORKSPACE_UPDATED = "workspace_updated", "Workspace Updated"
    WORKSPACE_DELETED = "workspace_deleted", "Workspace Deleted"
    WORKSPACE_STATUS_CHANGED = "workspace_status_changed", "Workspace Status Changed"
    WORKSPACE_ARCHIVED = "workspace_archived", "Workspace Archived"
    WORKSPACE_ACTIVATED = "workspace_activated", "Workspace Activated"
    WORKSPACE_CLOSED = "workspace_closed", "Workspace Closed"
    WORKSPACE_ADMIN_CHANGED = "workspace_admin_changed", "Workspace Admin Changed"
    WORKSPACE_REVIEWER_ASSIGNED = (
        "workspace_reviewer_assigned",
        "Workspace Reviewer Assigned",
    )

    # Team Management
    TEAM_CREATED = "team_created", "Team Created"
    TEAM_UPDATED = "team_updated", "Team Updated"
    TEAM_DELETED = "team_deleted", "Team Deleted"
    TEAM_MEMBER_ADDED = "team_member_added", "Team Member Added"
    TEAM_MEMBER_REMOVED = "team_member_removed", "Team Member Removed"
    TEAM_MEMBER_ROLE_CHANGED = "team_member_role_changed", "Team Member Role Changed"
    WORKSPACE_TEAM_CREATED = "workspace_team_created", "Workspace Team Created"
    WORKSPACE_TEAM_UPDATED = "workspace_team_updated", "Workspace Team Updated"
    WORKSPACE_TEAM_DELETED = "workspace_team_deleted", "Workspace Team Deleted"

    # Entry Management
    ENTRY_CREATED = "entry_created", "Entry Created"
    ENTRY_UPDATED = "entry_updated", "Entry Updated"
    ENTRY_DELETED = "entry_deleted", "Entry Deleted"
    ENTRY_STATUS_CHANGED = "entry_status_changed", "Entry Status Changed"
    ENTRY_SUBMITTED = "entry_submitted", "Entry Submitted"
    ENTRY_REVIEWED = "entry_reviewed", "Entry Reviewed"
    ENTRY_APPROVED = "entry_approved", "Entry Approved"
    ENTRY_REJECTED = "entry_rejected", "Entry Rejected"
    ENTRY_FLAGGED = "entry_flagged", "Entry Flagged"
    ENTRY_UNFLAGGED = "entry_unflagged", "Entry Unflagged"

    # File & Attachment Management
    FILE_UPLOADED = "file_uploaded", "File Uploaded"
    FILE_DOWNLOADED = "file_downloaded", "File Downloaded"
    FILE_DELETED = "file_deleted", "File Deleted"
    ATTACHMENT_ADDED = "attachment_added", "Attachment Added"
    ATTACHMENT_REMOVED = "attachment_removed", "Attachment Removed"
    ATTACHMENT_UPDATED = "attachment_updated", "Attachment Updated"

    # Remittance Management
    REMITTANCE_CREATED = "remittance_created", "Remittance Created"
    REMITTANCE_UPDATED = "remittance_updated", "Remittance Updated"
    REMITTANCE_DELETED = "remittance_deleted", "Remittance Deleted"
    REMITTANCE_STATUS_CHANGED = "remittance_status_changed", "Remittance Status Changed"
    REMITTANCE_PAID = "remittance_paid", "Remittance Paid"
    REMITTANCE_PARTIALLY_PAID = "remittance_partially_paid", "Remittance Partially Paid"
    REMITTANCE_OVERDUE = "remittance_overdue", "Remittance Overdue"
    REMITTANCE_CANCELED = "remittance_canceled", "Remittance Canceled"

    # Invitation Management
    INVITATION_SENT = "invitation_sent", "Invitation Sent"
    INVITATION_ACCEPTED = "invitation_accepted", "Invitation Accepted"
    INVITATION_DECLINED = "invitation_declined", "Invitation Declined"
    INVITATION_EXPIRED = "invitation_expired", "Invitation Expired"
    INVITATION_CANCELED = "invitation_canceled", "Invitation Canceled"
    INVITATION_RESENT = "invitation_resent", "Invitation Resent"

    # Currency & Exchange Rate Management
    EXCHANGE_RATE_CREATED = "exchange_rate_created", "Exchange Rate Created"
    EXCHANGE_RATE_UPDATED = "exchange_rate_updated", "Exchange Rate Updated"
    EXCHANGE_RATE_DELETED = "exchange_rate_deleted", "Exchange Rate Deleted"
    CURRENCY_ADDED = "currency_added", "Currency Added"
    CURRENCY_UPDATED = "currency_updated", "Currency Updated"
    CURRENCY_REMOVED = "currency_removed", "Currency Removed"

    # Permission & Access Management
    PERMISSION_GRANTED = "permission_granted", "Permission Granted"
    PERMISSION_REVOKED = "permission_revoked", "Permission Revoked"
    ROLE_ASSIGNED = "role_assigned", "Role Assigned"
    ROLE_REMOVED = "role_removed", "Role Removed"
    ACCESS_DENIED = "access_denied", "Access Denied"
    UNAUTHORIZED_ACCESS_ATTEMPT = (
        "unauthorized_access_attempt",
        "Unauthorized Access Attempt",
    )

    # Data Export & Import
    DATA_EXPORTED = "data_exported", "Data Exported"
    DATA_IMPORTED = "data_imported", "Data Imported"
    REPORT_GENERATED = "report_generated", "Report Generated"
    BULK_OPERATION = "bulk_operation", "Bulk Operation"

    # Email Events
    EMAIL_SENT = "email_sent", "Email Sent"
    EMAIL_FAILED = "email_failed", "Email Failed"
    NOTIFICATION_SENT = "notification_sent", "Notification Sent"
