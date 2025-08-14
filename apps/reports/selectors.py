from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, When
from django.utils import timezone

from apps.remittance.models import Remittance
from apps.remittance.constants import RemittanceStatus
from apps.entries.models import Entry
from apps.entries.constants import EntryStatus


class RemittanceSelectors:
    """Selectors for remittance-related statistics and calculations."""
    
    @staticmethod
    def get_total_due_amount(organization_id, workspace_id=None):
        """
        Calculate the total due amount across all remittances for an organization.
        """
        queryset = Remittance.objects.filter(
            workspace_team__workspace__organization_id=organization_id
        ).exclude(status=RemittanceStatus.CANCELED)

        if workspace_id:
            queryset = queryset.filter(workspace_team__workspace_id=workspace_id)

        result = queryset.aggregate(total_due=Sum("due_amount"))
        return result["total_due"] or Decimal("0.00")

    @staticmethod
    def get_total_paid_amount(organization_id, workspace_id=None):
        """
        Calculate the total paid amount across all remittances for an organization.
        """
        queryset = Remittance.objects.filter(
            workspace_team__workspace__organization_id=organization_id
        ).exclude(status=RemittanceStatus.CANCELED)

        if workspace_id:
            queryset = queryset.filter(workspace_team__workspace_id=workspace_id)

        result = queryset.aggregate(total_paid=Sum("paid_amount"))
        return result["total_paid"] or Decimal("0.00")

    @staticmethod
    def get_overdue_amount(organization_id, workspace_id=None):
        """
        Calculate the total overdue amount across all remittances for an organization.
        This includes remittances that are past their due date and not fully paid.
        """
        current_date = timezone.now().date()

        queryset = Remittance.objects.filter(
            workspace_team__workspace__organization_id=organization_id,
            workspace_team__workspace__end_date__lt=current_date,
            status__in=[
                RemittanceStatus.PENDING,
                RemittanceStatus.PARTIAL,
                RemittanceStatus.OVERDUE,
            ],
        )

        if workspace_id:
            queryset = queryset.filter(workspace_team__workspace_id=workspace_id)

        # Calculate overdue amount as the sum of (due_amount - paid_amount) for overdue remittances
        result = queryset.aggregate(
            overdue_amount=Sum(
                Case(
                    When(
                        due_amount__gt=F("paid_amount"),
                        then=F("due_amount") - F("paid_amount"),
                    ),
                    default=Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )
        )
        return result["overdue_amount"] or Decimal("0.00")

    @staticmethod
    def get_remaining_due_amount(organization_id, workspace_id=None):
        """
        Calculate the total remaining due amount across all remittances for an organization.
        This is the total amount still owed (due_amount - paid_amount) for all active remittances.
        """
        queryset = Remittance.objects.filter(
            workspace_team__workspace__organization_id=organization_id
        ).exclude(status__in=[RemittanceStatus.PAID, RemittanceStatus.CANCELED])

        if workspace_id:
            queryset = queryset.filter(workspace_team__workspace_id=workspace_id)

        # Calculate remaining amount as the sum of (due_amount - paid_amount) for unpaid remittances
        result = queryset.aggregate(
            remaining_amount=Sum(
                Case(
                    When(
                        due_amount__gt=F("paid_amount"),
                        then=F("due_amount") - F("paid_amount"),
                    ),
                    default=Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )
        )
        return result["remaining_amount"] or Decimal("0.00")

    @classmethod
    def get_summary_stats(cls, organization_id, workspace_id=None):
        """
        Get all remittance summary statistics in one call.
        """
        return {
            'total_due': cls.get_total_due_amount(organization_id, workspace_id),
            'total_paid': cls.get_total_paid_amount(organization_id, workspace_id),
            'overdue_amount': cls.get_overdue_amount(organization_id, workspace_id),
            'remaining_due': cls.get_remaining_due_amount(organization_id, workspace_id),
        }


class EntrySelectors:
    """Selectors for entry-related statistics and calculations."""
    
    @staticmethod
    def get_total_count(organization_id, workspace_id=None):
        """
        Get the total count of all entries for an organization.
        """
        queryset = Entry.objects.filter(
            organization_id=organization_id
        )
        
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        
        return queryset.count()

    @staticmethod
    def get_pending_count(organization_id, workspace_id=None):
        """
        Get the count of pending entries for an organization.
        """
        queryset = Entry.objects.filter(
            organization_id=organization_id,
            status=EntryStatus.PENDING
        )
        
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        
        return queryset.count()

    @staticmethod
    def get_approved_count(organization_id, workspace_id=None):
        """
        Get the count of approved entries for an organization.
        """
        queryset = Entry.objects.filter(
            organization_id=organization_id,
            status=EntryStatus.APPROVED
        )
        
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        
        return queryset.count()

    @staticmethod
    def get_rejected_count(organization_id, workspace_id=None):
        """
        Get the count of rejected entries for an organization.
        """
        queryset = Entry.objects.filter(
            organization_id=organization_id,
            status=EntryStatus.REJECTED
        )
        
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        
        return queryset.count()

    @classmethod
    def get_summary_stats(cls, organization_id, workspace_id=None):
        """
        Get all entry summary statistics in one call.
        """
        return {
            'total_entries': cls.get_total_count(organization_id, workspace_id),
            'pending_entries': cls.get_pending_count(organization_id, workspace_id),
            'approved_entries': cls.get_approved_count(organization_id, workspace_id),
            'rejected_entries': cls.get_rejected_count(organization_id, workspace_id),
        }