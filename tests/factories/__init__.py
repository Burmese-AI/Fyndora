"""
Test factories for Fyndora models.

Import all factories here for easy access in tests.
"""

from .attachment_factories import (
    AttachmentFactory,
    AttachmentWithEntryFactory,
    ImageAttachmentFactory,
    MultipleAttachmentsFactory,
    OtherAttachmentFactory,
    PDFAttachmentFactory,
    SpreadsheetAttachmentFactory,
)
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
from .invitation_factories import (
    InvitationFactory,
    ExpiredInvitationFactory,
    UsedInvitationFactory,
    InactiveInvitationFactory,
    InvitationWithSpecificEmailFactory,
    InvitationForOrganizationFactory,
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
    # Attachment factories
    "AttachmentFactory",
    "ImageAttachmentFactory",
    "PDFAttachmentFactory",
    "SpreadsheetAttachmentFactory",
    "OtherAttachmentFactory",
    "AttachmentWithEntryFactory",
    "MultipleAttachmentsFactory",
    # Auditlog factories
    "AuditTrailFactory",
    "EntryCreatedAuditFactory",
    "StatusChangedAuditFactory",
    "FlaggedAuditFactory",
    "FileUploadedAuditFactory",
    "SystemAuditFactory",
    "AuditWithComplexMetadataFactory",
    "BulkAuditTrailFactory",
    # Invitation factories
    "InvitationFactory",
    "ExpiredInvitationFactory",
    "UsedInvitationFactory",
    "InactiveInvitationFactory",
    "InvitationWithSpecificEmailFactory",
    "InvitationForOrganizationFactory",
]
