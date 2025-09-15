# Audit Action Types Documentation

This document provides a comprehensive overview of all audit action types available in the Fyndora audit logging system.

## Categories

### Authentication & Authorization
These events track user authentication and authorization activities:

- `LOGIN_SUCCESS` - Successful user login
- `LOGIN_FAILED` - Failed login attempt
- `LOGOUT` - User logout
- `PASSWORD_CHANGED` - User password change
- `PASSWORD_RESET_REQUESTED` - Password reset request initiated
- `PASSWORD_RESET_COMPLETED` - Password reset completed

### User Management
Events related to user account management:

- `USER_CREATED` - New user account created
- `USER_UPDATED` - User account information updated
- `USER_DELETED` - User account deleted
- `USER_PROFILE_UPDATED` - User profile information updated

### Organization Management
Events related to organization lifecycle:

- `ORGANIZATION_CREATED` - New organization created
- `ORGANIZATION_UPDATED` - Organization information updated
- `ORGANIZATION_DELETED` - Organization deleted
- `ORGANIZATION_STATUS_CHANGED` - Organization status changed
- `ORGANIZATION_ARCHIVED` - Organization archived
- `ORGANIZATION_ACTIVATED` - Organization activated
- `ORGANIZATION_CLOSED` - Organization closed

### Organization Member Management
Events related to organization membership:

- `ORGANIZATION_MEMBER_ADDED` - Member added to organization
- `ORGANIZATION_MEMBER_REMOVED` - Member removed from organization
- `ORGANIZATION_MEMBER_ROLE_CHANGED` - Member role changed
- `ORGANIZATION_MEMBER_UPDATED` - Member information updated

### Workspace Management
Events related to workspace operations:

- `WORKSPACE_CREATED` - New workspace created
- `WORKSPACE_UPDATED` - Workspace information updated
- `WORKSPACE_DELETED` - Workspace deleted
- `WORKSPACE_STATUS_CHANGED` - Workspace status changed
- `WORKSPACE_ARCHIVED` - Workspace archived
- `WORKSPACE_ACTIVATED` - Workspace activated
- `WORKSPACE_CLOSED` - Workspace closed
- `WORKSPACE_ADMIN_CHANGED` - Workspace administrator changed
- `WORKSPACE_REVIEWER_ASSIGNED` - Operations reviewer assigned

### Team Management
Events related to team and team member operations:

- `TEAM_CREATED` - New team created
- `TEAM_UPDATED` - Team information updated
- `TEAM_DELETED` - Team deleted
- `TEAM_MEMBER_ADDED` - Member added to team
- `TEAM_MEMBER_REMOVED` - Member removed from team
- `TEAM_MEMBER_ROLE_CHANGED` - Team member role changed
- `WORKSPACE_TEAM_CREATED` - Workspace team association created
- `WORKSPACE_TEAM_UPDATED` - Workspace team association updated
- `WORKSPACE_TEAM_DELETED` - Workspace team association deleted

### Entry Management
Events related to financial entries and their lifecycle:

- `ENTRY_CREATED` - New entry created
- `ENTRY_UPDATED` - Entry information updated
- `ENTRY_DELETED` - Entry deleted
- `ENTRY_STATUS_CHANGED` - Entry status changed
- `ENTRY_SUBMITTED` - Entry submitted for review
- `ENTRY_REVIEWED` - Entry reviewed
- `ENTRY_APPROVED` - Entry approved
- `ENTRY_REJECTED` - Entry rejected
- `ENTRY_FLAGGED` - Entry flagged for attention
- `ENTRY_UNFLAGGED` - Entry unflagged

### File & Attachment Management
Events related to file operations:

- `FILE_UPLOADED` - File uploaded to system
- `FILE_DOWNLOADED` - File downloaded from system
- `FILE_DELETED` - File deleted from system
- `ATTACHMENT_ADDED` - Attachment added to entity
- `ATTACHMENT_REMOVED` - Attachment removed from entity
- `ATTACHMENT_UPDATED` - Attachment information updated

### Remittance Management
Events related to remittance processing:

- `REMITTANCE_CREATED` - New remittance created
- `REMITTANCE_UPDATED` - Remittance information updated
- `REMITTANCE_DELETED` - Remittance deleted
- `REMITTANCE_STATUS_CHANGED` - Remittance status changed
- `REMITTANCE_PAID` - Remittance marked as paid
- `REMITTANCE_PARTIALLY_PAID` - Remittance partially paid
- `REMITTANCE_OVERDUE` - Remittance marked as overdue
- `REMITTANCE_CANCELED` - Remittance canceled
- `REMITTANCE_CONFIRMED` - Remittance confirmed

### Invitation Management
Events related to user invitations:

- `INVITATION_SENT` - Invitation sent to user
- `INVITATION_ACCEPTED` - Invitation accepted by user
- `INVITATION_DECLINED` - Invitation declined by user
- `INVITATION_EXPIRED` - Invitation expired
- `INVITATION_CANCELED` - Invitation canceled
- `INVITATION_RESENT` - Invitation resent to user

### Currency & Exchange Rate Management
Events related to currency and exchange rate operations:

- `EXCHANGE_RATE_CREATED` - New exchange rate created
- `EXCHANGE_RATE_UPDATED` - Exchange rate updated
- `EXCHANGE_RATE_DELETED` - Exchange rate deleted
- `CURRENCY_ADDED` - New currency added
- `CURRENCY_UPDATED` - Currency information updated
- `CURRENCY_REMOVED` - Currency removed

### Permission & Access Management
Events related to permissions and access control:

- `PERMISSION_GRANTED` - Permission granted to user
- `PERMISSION_REVOKED` - Permission revoked from user
- `ROLE_ASSIGNED` - Role assigned to user
- `ROLE_REMOVED` - Role removed from user
- `ACCESS_DENIED` - Access denied to resource
- `UNAUTHORIZED_ACCESS_ATTEMPT` - Unauthorized access attempt detected

### Data Export & Import
Events related to data operations:

- `DATA_EXPORTED` - Data exported from system
- `DATA_IMPORTED` - Data imported into system
- `REPORT_GENERATED` - Report generated
- `BULK_OPERATION` - Bulk operation performed

### Email Events
Events related to email and notifications:

- `EMAIL_SENT` - Email sent successfully
- `EMAIL_FAILED` - Email sending failed
- `NOTIFICATION_SENT` - Notification sent to user

## Usage Guidelines

### Choosing the Right Logging Method

#### Use BusinessAuditLogger for Business Operations
For manual business operations that require rich context and standardized metadata, use the `BusinessAuditLogger` class:

- **Entry workflow actions** (submit, approve, reject, flag)
- **Permission changes** (grant, revoke)
- **Data exports** and **bulk operations**
- **Status changes** and **file operations**
- **User-initiated actions** in views and services

#### Use audit_create for System Operations
For low-level system operations and automatic logging, use `audit_create` directly:

- **Signal handlers** (automatic model change tracking)
- **Authentication events** (login, logout)
- **System-generated events**
- **Test cases** and **custom scenarios**

### When to Use Each Action Type

1. **Be Specific**: Use the most specific action type available rather than generic ones
2. **Consistency**: Use consistent action types for similar operations across different entities
3. **Security Focus**: Always log security-related events with appropriate action types
4. **Lifecycle Tracking**: Track complete lifecycle of entities (create, update, delete, status changes)

### Metadata Recommendations

Each audit log entry should include relevant metadata:

- **User Context**: User ID, username, role
- **Request Context**: IP address, user agent, session ID
- **Entity Context**: Entity type, entity ID, previous values (for updates)
- **Business Context**: Workspace, organization, team context
- **Technical Context**: Timestamp, request ID, API endpoint

### Security Considerations

- **Sensitive Data**: Never log sensitive data like passwords or tokens in metadata
- **PII Protection**: Be careful with personally identifiable information
- **Retention**: Consider data retention policies for different action types
- **Access Control**: Ensure audit logs themselves are properly protected

## Implementation Examples

### BusinessAuditLogger Examples (Recommended for Business Operations)

```python
from apps.auditlog.business_logger import BusinessAuditLogger

# Entry workflow actions
BusinessAuditLogger.log_entry_action(
    user=request.user,
    entry=entry,
    action="approve",  # or "reject", "submit", "flag", "unflag"
    request=request,
    notes="Entry meets all requirements",
    level="standard"
)

# Permission changes
BusinessAuditLogger.log_permission_change(
    user=request.user,
    target_user=target_user,
    permission="workspace.change_entry",
    action="grant",  # or "revoke"
    request=request,
    reason="Promoted to reviewer role"
)

# Data export operations
BusinessAuditLogger.log_data_export(
    user=request.user,
    export_type="entries",
    filters={"status": "approved", "date_range": "2024-01"},
    result_count=150,
    request=request,
    format="csv",
    reason="Monthly financial report"
)

# Bulk operations
BusinessAuditLogger.log_bulk_operation(
    user=request.user,
    operation_type="bulk_approve",
    affected_objects=entries_queryset,
    request=request,
    criteria="auto_approval_eligible"
)

# Status changes
BusinessAuditLogger.log_status_change(
    user=request.user,
    entity=workspace,
    old_status="active",
    new_status="archived",
    request=request,
    reason="End of fiscal year"
)

# File operations
BusinessAuditLogger.log_file_operation(
    user=request.user,
    file_obj=uploaded_file,
    operation="upload",  # or "download", "delete"
    request=request,
    file_category="receipt",
    purpose="Expense documentation"
)
```

### Direct audit_create Examples (For System Operations)

```python
from apps.auditlog.services import audit_create
from apps.auditlog.constants import AuditActionType

# Authentication events (typically in signal handlers)
audit_create(
    user=user,
    action_type=AuditActionType.LOGIN_SUCCESS,
    target_entity=user,
    metadata={
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT'),
        'login_method': 'email'
    }
)

# System-generated events
audit_create(
    user=system_user,
    action_type=AuditActionType.INVITATION_EXPIRED,
    target_entity=invitation,
    metadata={
        'invitation_type': 'organization_member',
        'expired_after_days': 7,
        'auto_cleanup': True
    }
)

# Model change tracking (in signal handlers)
audit_create(
    user=request.user,
    action_type=AuditActionType.ORGANIZATION_UPDATED,
    target_entity=organization,
    metadata={
        'changed_fields': ['name', 'description'],
        'previous_values': {'name': 'Old Name'},
        'source': 'admin_interface'
    }
)
```

### Migration from audit_create to BusinessAuditLogger

If you're currently using `audit_create` for business operations, consider migrating:

```python
# OLD: Direct audit_create usage
audit_create(
    user=reviewer.user,
    action_type=AuditActionType.ENTRY_APPROVED,
    target_entity=entry,
    metadata={"notes": notes}
)

# NEW: BusinessAuditLogger usage (recommended)
BusinessAuditLogger.log_entry_action(
    user=reviewer.user,
    entry=entry,
    action="approve",
    request=request,
    notes=notes
)
```

### Available BusinessAuditLogger Methods

- `log_entry_action()` - Entry workflow actions (submit, approve, reject, flag, unflag)
- `log_permission_change()` - Permission grants and revocations
- `log_data_export()` - Data export operations with filters and context
- `log_bulk_operation()` - Bulk operations with smart object sampling
- `log_status_change()` - Generic status changes for any entity
- `log_file_operation()` - File upload, download, and delete operations

## Migration Notes

This expanded set of action types replaces the previous limited set. Existing audit logs with old action types will continue to work, but new implementations should use the specific action types defined here.