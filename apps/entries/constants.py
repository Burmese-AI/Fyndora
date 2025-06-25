from django.db import models

CONTEXT_OBJECT_NAME = "entries"
DETAIL_CONTEXT_OBJECT_NAME = "entry"

class EntryType(models.TextChoices):
    INCOME = "income", "Income"
    DISBURSEMENT = "disbursement", "Disbursement"
    REMITTANCE = "remittance", "Remittance"
    WORKSPACE_EXP = "workspace_exp", "Workspace Expense"
    ORG_EXP = "org_exp", "Organization Expense"


class EntryStatus(models.TextChoices):
    PENDING_REVIEW = "pending_review", "Pending Review"
    APPROVED = "approved", "Approved"
    FLAGGED = "flagged", "Flagged"
    REJECTED = "rejected", "Rejected"
