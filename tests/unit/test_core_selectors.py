"""
Unit tests for apps.core.selectors
"""

import pytest

from apps.core.selectors import (
    get_user_by_email,
    get_org_members_without_owner,
    get_organization_by_id,
    get_workspaces_under_organization,
    get_workspace_teams_under_organization,
    User as SelectorUser,
)
from tests.factories import (
    OrganizationWithOwnerFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
    CustomUserFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestGetUserByEmail:
    def test_returns_user_when_single_match(self):
        user = CustomUserFactory(email="alpha@example.com")
        assert get_user_by_email("alpha@example.com") == user

    def test_returns_none_when_not_found(self):
        assert get_user_by_email("missing@example.com") is None

    def test_returns_first_when_multiple(self, monkeypatch):
        # DB enforces unique email, so simulate MultipleObjectsReturned via patching
        user = CustomUserFactory(email="dup@example.com")

        def fake_get(email):
            raise SelectorUser.MultipleObjectsReturned()

        class FakeQS:
            def __init__(self, u):
                self._u = u

            def first(self):
                return self._u

        def fake_filter(email):
            return FakeQS(user)

        monkeypatch.setattr(SelectorUser.objects, "get", fake_get)
        monkeypatch.setattr(SelectorUser.objects, "filter", fake_filter)

        found = get_user_by_email("dup@example.com")
        assert found is not None
        assert found.email == "dup@example.com"

    def test_generic_exception_returns_none(self, monkeypatch):
        def boom(email):
            raise Exception("boom")

        monkeypatch.setattr(SelectorUser.objects, "get", boom)
        assert get_user_by_email("any@example.com") is None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrgMembersWithoutOwner:
    def test_excludes_owner_if_present(self):
        organization = OrganizationWithOwnerFactory()
        org_member_one = OrganizationMemberFactory(organization=organization)
        org_member_two = OrganizationMemberFactory(organization=organization)

        queryset = get_org_members_without_owner(organization)
        member_ids = set(queryset.values_list("pk", flat=True))
        assert organization.owner.pk not in member_ids
        assert org_member_one.pk in member_ids and org_member_two.pk in member_ids

    def test_returns_all_members_if_no_owner(self):
        organization = OrganizationFactory(owner=None)
        org_member_one = OrganizationMemberFactory(organization=organization)
        org_member_two = OrganizationMemberFactory(organization=organization)

        queryset = get_org_members_without_owner(organization)
        member_ids = set(queryset.values_list("pk", flat=True))
        assert org_member_one.pk in member_ids and org_member_two.pk in member_ids

    def test_exception_returns_none(self, monkeypatch):
        organization = OrganizationWithOwnerFactory()

        # Patch the symbol actually used inside core.selectors
        import apps.core.selectors as core_selectors

        def boom_filter(*args, **kwargs):
            raise Exception("db fail")

        monkeypatch.setattr(
            core_selectors.OrganizationMember.objects, "filter", boom_filter
        )
        assert get_org_members_without_owner(organization) is None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrganizationById:
    def test_returns_org_when_exists(self):
        organization = OrganizationWithOwnerFactory()
        assert get_organization_by_id(organization.pk) == organization

    def test_returns_none_when_missing(self):
        assert get_organization_by_id("00000000-0000-0000-0000-000000000000") is None

    def test_generic_exception_returns_none(self, monkeypatch):
        from apps.organizations import models as org_models

        def boom(pk):
            raise Exception("boom")

        monkeypatch.setattr(org_models.Organization.objects, "get", boom)
        assert get_organization_by_id("any") is None


@pytest.mark.unit
@pytest.mark.django_db
class TestWorkspaceQueries:
    def test_get_workspaces_under_organization(self):
        organization = OrganizationWithOwnerFactory()
        workspace_one = WorkspaceFactory(organization=organization)
        workspace_two = WorkspaceFactory(organization=organization)

        queryset = get_workspaces_under_organization(organization.pk)
        workspace_ids = set(queryset.values_list("pk", flat=True))
        assert workspace_one.pk in workspace_ids and workspace_two.pk in workspace_ids

    def test_get_workspace_teams_under_organization(self):
        organization = OrganizationWithOwnerFactory()
        workspace = WorkspaceFactory(organization=organization)
        workspace_team_one = WorkspaceTeamFactory(workspace=workspace)
        workspace_team_two = WorkspaceTeamFactory(workspace=workspace)

        queryset = get_workspace_teams_under_organization(organization.pk)
        workspace_team_ids = set(queryset.values_list("pk", flat=True))
        assert workspace_team_one.pk in workspace_team_ids and workspace_team_two.pk in workspace_team_ids

    def test_get_workspaces_under_organization_exception(self, monkeypatch):
        from apps.workspaces import models as ws_models

        def boom(**kwargs):
            raise Exception("boom")

        monkeypatch.setattr(ws_models.Workspace.objects, "filter", boom)
        assert get_workspaces_under_organization("orgid") is None

    def test_get_workspace_teams_under_organization_exception(self, monkeypatch):
        from apps.workspaces import models as ws_models

        def boom(**kwargs):
            raise Exception("boom")

        monkeypatch.setattr(ws_models.WorkspaceTeam.objects, "filter", boom)
        assert get_workspace_teams_under_organization("orgid") is None


