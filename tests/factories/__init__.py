"""
Test factories for Fyndora models.

Import all factories here for easy access in tests.
"""

from .auditlog_factories import (
    AuditTrailFactory,
    AuditWithComplexMetadataFactory,
    BulkAuditTrailFactory,
    EntryCreatedAuditFactory,
    FileUploadedAuditFactory,
    FlaggedAuditFactory,
    StatusChangedAuditFactory,
    SystemAuditFactory,
)
from .entry_factories import (
    ApprovedEntryFactory,
    DisbursementEntryFactory,
    EntryFactory,
    EntryWithReviewFactory,
    FlaggedEntryFactory,
    IncomeEntryFactory,
    LargeAmountEntryFactory,
    PendingEntryFactory,
    RejectedEntryFactory,
    RemittanceEntryFactory,
    SmallAmountEntryFactory,
)
from .organization_factories import (
    ArchivedOrganizationFactory,
    InactiveOrganizationMemberFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    OrganizationWithOwnerFactory,
)
from .team_factories import (
    AuditorMemberFactory,
    TeamFactory,
    TeamMemberFactory,
    TeamWithCoordinatorFactory,
)
from .user_factories import (
    CustomUserFactory,
    StaffUserFactory,
    SuperUserFactory,
    SuspendedUserFactory,
)
from .workspace_factories import (
    ActiveWorkspaceFactory,
    ArchivedWorkspaceFactory,
    ClosedWorkspaceFactory,
    CustomRateWorkspaceFactory,
    WorkspaceAdminMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceWithAdminFactory,
    WorkspaceWithTeamsFactory,
)

__all__ = [
    # User factories
    "CustomUserFactory",
    "StaffUserFactory",
    "SuperUserFactory",
    "SuspendedUserFactory",
    # Organization factories
    "OrganizationFactory",
    "OrganizationWithOwnerFactory",
    "OrganizationMemberFactory",
    "InactiveOrganizationMemberFactory",
    "ArchivedOrganizationFactory",
    # Team factories
    "TeamFactory",
    "TeamWithCoordinatorFactory",
    "TeamMemberFactory",
    "AuditorMemberFactory",
    # Workspace factories
    "WorkspaceFactory",
    "WorkspaceWithAdminFactory",
    "WorkspaceAdminMemberFactory",
    "ActiveWorkspaceFactory",
    "ArchivedWorkspaceFactory",
    "ClosedWorkspaceFactory",
    "WorkspaceTeamFactory",
    "WorkspaceWithTeamsFactory",
    "CustomRateWorkspaceFactory",
    # Entry factories
    "EntryFactory",
    "IncomeEntryFactory",
    "DisbursementEntryFactory",
    "RemittanceEntryFactory",
    "PendingEntryFactory",
    "ApprovedEntryFactory",
    "RejectedEntryFactory",
    "FlaggedEntryFactory",
    "LargeAmountEntryFactory",
    "SmallAmountEntryFactory",
    "EntryWithReviewFactory",
    # Auditlog factories
    "AuditTrailFactory",
    "EntryCreatedAuditFactory",
    "StatusChangedAuditFactory",
    "FlaggedAuditFactory",
    "FileUploadedAuditFactory",
    "SystemAuditFactory",
    "AuditWithComplexMetadataFactory",
    "BulkAuditTrailFactory",
]
