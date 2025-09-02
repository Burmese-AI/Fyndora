"""
Unit tests for apps.entries.utils helpers.
"""

from unittest.mock import patch

import pytest

from apps.entries.utils import (
    can_view_org_expense,
    can_add_org_expense,
    can_update_org_expense,
    can_delete_org_expense,
    can_add_workspace_expense,
    can_update_workspace_expense,
    can_delete_workspace_expense,
    can_view_workspace_team_entry,
    can_add_workspace_team_entry,
    can_update_workspace_team_entry,
    can_delete_workspace_team_entry,
    can_update_other_submitters_entry,
    extract_entry_business_context,
    own_higher_admin_role,
)
from apps.core.permissions import (
    OrganizationPermissions,
    WorkspacePermissions,
    WorkspaceTeamPermissions,
    EntryPermissions,
)
from apps.entries.constants import EntryType, EntryStatus
from tests.factories import (
    EntryFactory,
    OrganizationWithOwnerFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
    OrganizationMemberFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestPermissionHelpers:
    def setup_method(self):
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)

        # Use a simple mock-ish user that has a has_perm method we can patch
        class DummyUser:
            def has_perm(self, perm, obj=None):
                return False

        self.user = DummyUser()

    def test_org_permission_helpers_delegate_to_has_perm(self, monkeypatch):
        calls = []

        def fake_has_perm(perm, obj=None):
            calls.append((perm, obj))
            return True

        monkeypatch.setattr(self.user, "has_perm", fake_has_perm)

        assert can_view_org_expense(self.user, self.organization) is True
        assert can_add_org_expense(self.user, self.organization) is True
        assert can_update_org_expense(self.user, self.organization) is True
        assert can_delete_org_expense(self.user, self.organization) is True

        expected = {
            (OrganizationPermissions.VIEW_ORG_ENTRY, self.organization),
            (OrganizationPermissions.ADD_ORG_ENTRY, self.organization),
            (OrganizationPermissions.CHANGE_ORG_ENTRY, self.organization),
            (OrganizationPermissions.DELETE_ORG_ENTRY, self.organization),
        }
        assert set(calls) == expected

    def test_workspace_permission_helpers_delegate_to_has_perm(self, monkeypatch):
        calls = []

        def fake_has_perm(perm, obj=None):
            calls.append((perm, obj))
            return True

        monkeypatch.setattr(self.user, "has_perm", fake_has_perm)

        assert can_add_workspace_expense(self.user, self.workspace) is True
        assert can_update_workspace_expense(self.user, self.workspace) is True
        assert can_delete_workspace_expense(self.user, self.workspace) is True

        expected = {
            (WorkspacePermissions.ADD_WORKSPACE_ENTRY, self.workspace),
            (WorkspacePermissions.CHANGE_WORKSPACE_ENTRY, self.workspace),
            (WorkspacePermissions.DELETE_WORKSPACE_ENTRY, self.workspace),
        }
        assert set(calls) == expected

    def test_workspace_team_permission_helpers_delegate_to_has_perm(self, monkeypatch):
        calls = []

        def fake_has_perm(perm, obj=None):
            calls.append((perm, obj))
            return True

        monkeypatch.setattr(self.user, "has_perm", fake_has_perm)

        assert can_view_workspace_team_entry(self.user, self.workspace_team) is True
        assert can_add_workspace_team_entry(self.user, self.workspace_team) is True
        assert can_update_workspace_team_entry(self.user, self.workspace_team) is True
        assert can_delete_workspace_team_entry(self.user, self.workspace_team) is True

        expected = {
            (WorkspaceTeamPermissions.VIEW_WORKSPACE_TEAM, self.workspace_team),
            (WorkspaceTeamPermissions.ADD_WORKSPACE_TEAM_ENTRY, self.workspace_team),
            (WorkspaceTeamPermissions.CHANGE_WORKSPACE_TEAM_ENTRY, self.workspace_team),
            (WorkspaceTeamPermissions.DELETE_WORKSPACE_TEAM_ENTRY, self.workspace_team),
        }
        assert set(calls) == expected


@pytest.mark.unit
@pytest.mark.django_db
class TestCanUpdateOtherSubmittersEntry:
    def setup_method(self):
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        self.entry = EntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
            entry_type=EntryType.INCOME,
        )

        # Dummy user with patchable has_perm
        class DummyUser:
            def has_perm(self, perm, obj=None):
                return False

        self.user = DummyUser()
        # OrganizationMember to pass into helper (matches function expectations)
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    def test_returns_true_if_user_has_direct_permission(self, monkeypatch):
        def fake_has_perm(perm, obj=None):
            assert perm == EntryPermissions.CHANGE_OTHER_SUBMITTERS_ENTRY
            assert obj == self.entry
            return True

        monkeypatch.setattr(self.user, "has_perm", fake_has_perm)
        # own_higher_admin_role should not be needed; force False to ensure it's ignored
        with patch("apps.entries.utils.own_higher_admin_role", return_value=False):
            assert can_update_other_submitters_entry(
                self.user, self.org_member, self.entry, self.workspace_team
            )

    def test_returns_true_if_no_direct_permission_but_has_higher_role(self):
        with patch("apps.entries.utils.own_higher_admin_role", return_value=True):
            assert can_update_other_submitters_entry(
                self.user, self.org_member, self.entry, self.workspace_team
            )

    def test_returns_false_if_no_perm_and_no_higher_role(self):
        with patch("apps.entries.utils.own_higher_admin_role", return_value=False):
            assert (
                can_update_other_submitters_entry(
                    self.user, self.org_member, self.entry, self.workspace_team
                )
                is False
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestExtractEntryBusinessContext:
    def test_returns_empty_dict_when_entry_is_none(self):
        assert extract_entry_business_context(None) == {}

    def test_returns_expected_keys_from_entry(self):
        org = OrganizationWithOwnerFactory()
        ws = WorkspaceFactory(organization=org)
        wt = WorkspaceTeamFactory(workspace=ws)
        entry = EntryFactory(organization=org, workspace=ws, workspace_team=wt)

        context = extract_entry_business_context(entry)

        assert set(context.keys()) == {
            "entry_id",
            "entry_type",
            "workspace_id",
            "workspace_name",
            "organization_id",
        }
        assert context["entry_id"] == str(entry.entry_id)
        assert context["entry_type"] == entry.entry_type
        assert context["workspace_id"] == str(ws.workspace_id)
        assert context["workspace_name"] == ws.title
        assert context["organization_id"] == str(ws.organization.organization_id)


@pytest.mark.unit
@pytest.mark.django_db
class TestOwnHigherAdminRole:
    def setup_method(self):
        self.organization = OrganizationWithOwnerFactory()
        self.workspace_admin = OrganizationMemberFactory(organization=self.organization)
        self.operations_reviewer = OrganizationMemberFactory(
            organization=self.organization
        )
        self.team_coordinator = OrganizationMemberFactory(
            organization=self.organization
        )

        # Attach roles
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            workspace_admin=self.workspace_admin,
            operations_reviewer=self.operations_reviewer,
        )
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace,
            team__team_coordinator=self.team_coordinator,
        )

    def test_true_for_team_coordinator(self):
        assert own_higher_admin_role(self.team_coordinator, self.workspace_team) is True

    def test_true_for_workspace_admin(self):
        assert own_higher_admin_role(self.workspace_admin, self.workspace_team) is True

    def test_true_for_operations_reviewer(self):
        assert (
            own_higher_admin_role(self.operations_reviewer, self.workspace_team) is True
        )

    def test_true_for_org_owner(self):
        assert (
            own_higher_admin_role(self.organization.owner, self.workspace_team) is True
        )

    def test_false_for_regular_member(self):
        random_member = OrganizationMemberFactory(organization=self.organization)
        assert own_higher_admin_role(random_member, self.workspace_team) is False
