from datetime import timedelta
from typing import List
from django.db.models import Sum
from django.utils.timezone import now
from .constants import EntryStatus, EntryType
from .selectors import get_entries


class EntryStats:
    """
    A simple stats helper for entries.
    Can be used for any entry types like ORG_EXP, TEAM_EXP, etc.
    Filters by organization, workspace, or workspace_team depending on the type.
    """

    def __init__(
        self,
        *,
        entry_types: List[EntryType],
        organization=None,
        workspace=None,
        workspace_team=None,
        status: EntryStatus = EntryStatus.APPROVED,
    ):
        """
        Initialize and filter queryset based on entry types and context.
        """
        if not entry_types:
            raise ValueError("At least one entry type must be provided.")

        self.queryset = get_entries(
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
            entry_types=entry_types,
            status=status,
        )

    def total(self):
        """
        Total amount from all entries.
        """
        return self._aggregate_total(self.queryset)

    def this_month(self):
        """
        Total amount for this month.
        """
        start_of_month = now().date().replace(day=1)
        return self._aggregate_total(
            self.queryset.filter(created_at__gte=start_of_month)
        )

    def last_month(self):
        """
        Total amount from last month.
        """
        today = now().date()
        start_of_this_month = today.replace(day=1)
        end_of_last_month = start_of_this_month - timedelta(days=1)
        start_of_last_month = end_of_last_month.replace(day=1)

        return self._aggregate_total(
            self.queryset.filter(
                created_at__date__gte=start_of_last_month,
                created_at__date__lte=end_of_last_month,
            )
        )

    def average_monthly(self):
        """
        Average monthly amount based on past 12 months.
        """
        one_year_ago = now().date() - timedelta(days=365)
        past_year_entries = self.queryset.filter(created_at__gte=one_year_ago)
        total = self._aggregate_total(past_year_entries)
        return total / 12

    def to_dict(self):
        """
        Return all stats as a dict (good for APIs).
        """
        return {
            "total": self.total(),
            "this_month": self.this_month(),
            "last_month": self.last_month(),
            "average_monthly": self.average_monthly(),
        }

    def _aggregate_total(self, qs):
        """
        Sum the amount field from given queryset.
        """
        return qs.aggregate(total=Sum("amount"))["total"] or 0
