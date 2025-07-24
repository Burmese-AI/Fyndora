"""
Management command to clean up old audit logs based on retention policies.
"""

from django.core.management.base import BaseCommand

from apps.auditlog.config import AuditConfig
from apps.auditlog.services import audit_cleanup_expired_logs


class Command(BaseCommand):
    help = "Clean up old audit logs based on retention policies"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--days",
            type=int,
            help="Override default retention period (in days)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=AuditConfig.CLEANUP_BATCH_SIZE,
            help=f"Number of records to delete in each batch (default: {AuditConfig.CLEANUP_BATCH_SIZE})",
        )
        parser.add_argument(
            "--action-type",
            type=str,
            help="Clean up only specific action type",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"] or AuditConfig.CLEANUP_DRY_RUN
        batch_size = options["batch_size"]
        override_days = options["days"]
        specific_action = options["action_type"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No records will be deleted")
            )

        # Perform cleanup
        if specific_action:
            self.stdout.write(f"Cleaning up logs for action type: {specific_action}")

        stats = audit_cleanup_expired_logs(
            dry_run=dry_run, batch_size=batch_size, action_type=specific_action, override_days=override_days
        )

        total_deleted = stats.get("total_deleted", 0)

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN SUMMARY: Would delete {total_deleted} total records"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nCLEANUP COMPLETE: Deleted {total_deleted} total records"
                )
            )

        # Show current retention settings
        self.stdout.write("\nCurrent retention settings:")
        self.stdout.write(f"  Default: {AuditConfig.DEFAULT_RETENTION_DAYS} days")
        self.stdout.write(
            f"  Authentication: {AuditConfig.AUTHENTICATION_RETENTION_DAYS} days"
        )
        self.stdout.write(
            f"  Critical actions: {AuditConfig.CRITICAL_RETENTION_DAYS} days"
        )
