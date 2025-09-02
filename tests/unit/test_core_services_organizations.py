"""
Unit tests for apps.core.services.organizations
"""

import pytest

from apps.core.services.organizations import get_organization_by_id
from tests.factories import OrganizationWithOwnerFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestCoreServicesOrganizations:
    def test_get_organization_by_id_success(self):
        organization = OrganizationWithOwnerFactory()
        found = get_organization_by_id(organization.organization_id)
        assert found == organization

    def test_get_organization_by_id_not_found_returns_none(self):
        assert (
            get_organization_by_id("00000000-0000-0000-0000-000000000000") is None
        )

    def test_get_organization_by_id_exception_returns_none(self, monkeypatch):
        from apps.organizations import models as org_models

        def boom(**kwargs):
            raise Exception("boom")

        monkeypatch.setattr(org_models.Organization.objects, "get", boom)
        assert get_organization_by_id("any") is None


