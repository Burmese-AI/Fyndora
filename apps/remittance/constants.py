from django.db import models


class RemittanceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PARTIAL = "partial", "Partially Paid"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    CANCELED = "canceled", "Canceled"
