"""
Performance tests for Remittance selectors.
"""

import pytest
from django.db import connection
from django.test.utils import override_settings

from apps.remittance import selectors
from apps.remittance.constants import RemittanceStatus
from tests.factories import (
    OrganizationFactory,
    PaidRemittanceFactory,
    PendingRemittanceFactory,
    RemittanceFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.django_db
class TestRemittanceSelectorsPerformance:
    """Test performance aspects of remittance selectors."""

    def test_large_dataset_performance(self):
        """Test selector performance with larger dataset."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        teams = [TeamFactory(organization=organization) for _ in range(10)]

        # Create multiple workspace teams and remittances
        for team in teams:
            workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
            # Only create one remittance per workspace_team due to OneToOneField constraint
            RemittanceFactory(workspace_team=workspace_team)

        # Reset queries
        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = list(
                selectors.get_remittances_with_filters(
                    workspace_id=workspace.workspace_id
                )
            )

            assert len(result) == 10  # One remittance per team
            # Should be efficient with select_related
            assert len(connection.queries) <= 3

    def test_filtered_query_performance(self):
        """Test performance of filtered queries."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        teams = [TeamFactory(organization=organization) for _ in range(5)]

        # Create remittances with different statuses
        for i, team in enumerate(teams):
            workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
            if i % 2 == 0:
                # Create paid remittances (indices 0, 2, 4 = 3 remittances)

                PaidRemittanceFactory(workspace_team=workspace_team)
            else:
                # Create pending remittances (indices 1, 3 = 2 remittances)

                PendingRemittanceFactory(workspace_team=workspace_team)

        # Reset queries
        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = list(
                selectors.get_remittances_with_filters(
                    workspace_id=workspace.workspace_id,
                    status=RemittanceStatus.PAID,
                    search="Fundraising",  # All teams have "Fundraising" in their title
                )
            )

            # Should find paid remittances (3 out of 5)
            assert len(result) == 3
            assert all(r.status == RemittanceStatus.PAID for r in result)
            # Should be efficient even with multiple filters
            assert len(connection.queries) <= 3

    def test_get_remittances_select_related_optimization(self):
        """Test that select_related optimization works correctly."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        team = TeamFactory(organization=organization)
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)
        RemittanceFactory(workspace_team=workspace_team)

        # Reset queries
        connection.queries_log.clear()

        with override_settings(DEBUG=True):
            result = list(
                selectors.get_remittances_with_filters(
                    workspace_id=workspace.workspace_id
                )
            )

            # Access related fields to ensure they're prefetched
            for remittance in result:
                _ = remittance.workspace_team.team.title
                _ = remittance.workspace_team.workspace.title
                if remittance.confirmed_by:
                    _ = remittance.confirmed_by.user.email

            # Should be a small number of queries due to select_related
            assert (
                len(connection.queries) <= 3
            )  # Allow some flexibility for setup queries
