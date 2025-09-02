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


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrgMembersWithoutOwner:
    def test_excludes_owner_if_present(self):
        org = OrganizationWithOwnerFactory()
        m1 = OrganizationMemberFactory(organization=org)
        m2 = OrganizationMemberFactory(organization=org)

        qs = get_org_members_without_owner(org)
        ids = set(qs.values_list("pk", flat=True))
        assert org.owner.pk not in ids
        assert m1.pk in ids and m2.pk in ids

    def test_returns_all_members_if_no_owner(self):
        org = OrganizationFactory(owner=None)
        m1 = OrganizationMemberFactory(organization=org)
        m2 = OrganizationMemberFactory(organization=org)

        qs = get_org_members_without_owner(org)
        ids = set(qs.values_list("pk", flat=True))
        assert m1.pk in ids and m2.pk in ids


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrganizationById:
    def test_returns_org_when_exists(self):
        org = OrganizationWithOwnerFactory()
        assert get_organization_by_id(org.pk) == org

    def test_returns_none_when_missing(self):
        assert get_organization_by_id("00000000-0000-0000-0000-000000000000") is None


@pytest.mark.unit
@pytest.mark.django_db
class TestWorkspaceQueries:
    def test_get_workspaces_under_organization(self):
        org = OrganizationWithOwnerFactory()
        ws1 = WorkspaceFactory(organization=org)
        ws2 = WorkspaceFactory(organization=org)

        qs = get_workspaces_under_organization(org.pk)
        ids = set(qs.values_list("pk", flat=True))
        assert ws1.pk in ids and ws2.pk in ids

    def test_get_workspace_teams_under_organization(self):
        org = OrganizationWithOwnerFactory()
        ws = WorkspaceFactory(organization=org)
        wt1 = WorkspaceTeamFactory(workspace=ws)
        wt2 = WorkspaceTeamFactory(workspace=ws)

        qs = get_workspace_teams_under_organization(org.pk)
        ids = set(qs.values_list("pk", flat=True))
        assert wt1.pk in ids and wt2.pk in ids


