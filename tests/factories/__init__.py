"""
Test factories for Fyndora models.

Import all factories here for easy access in tests.
"""

from .user_factories import (
    CustomUserFactory,
    StaffUserFactory,
    SuperUserFactory,
    SuspendedUserFactory,
)

from .organization_factories import (
    OrganizationFactory,
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
    InactiveOrganizationMemberFactory,
    ArchivedOrganizationFactory,
)

from .team_factories import (
    TeamFactory,
    TeamWithCoordinatorFactory,
    TeamMemberFactory,
    TeamCoordinatorFactory,
    OperationsReviewerFactory,
    WorkspaceAdminMemberFactory,
    AuditorMemberFactory,
    TeamWithCustomRateFactory,
)

from .workspace_factories import (
    WorkspaceFactory,
    WorkspaceWithAdminFactory,
    ActiveWorkspaceFactory,
    ArchivedWorkspaceFactory,
    ClosedWorkspaceFactory,
    WorkspaceTeamFactory,
    WorkspaceWithTeamsFactory,
    CustomRateWorkspaceFactory,
)

from .entry_factories import (
    EntryFactory,
    IncomeEntryFactory,
    DisbursementEntryFactory,
    RemittanceEntryFactory,
    PendingEntryFactory,
    ApprovedEntryFactory,
    RejectedEntryFactory,
    FlaggedEntryFactory,
    LargeAmountEntryFactory,
    SmallAmountEntryFactory,
    EntryWithReviewFactory,
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
    "TeamCoordinatorFactory",
    "OperationsReviewerFactory",
    "WorkspaceAdminMemberFactory",
    "AuditorMemberFactory",
    "TeamWithCustomRateFactory",
    # Workspace factories
    "WorkspaceFactory",
    "WorkspaceWithAdminFactory",
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
]
