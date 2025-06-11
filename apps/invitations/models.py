from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.core.models import baseModel
from apps.organizations.models import Organization, OrganizationMember
from django.utils import timezone
from uuid import uuid4

class Invitation(baseModel):
    invitation_id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(max_length=255)
    invited_by = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invitations_sent",
    )
    token = models.UUIDField(default=uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    expired_at = models.DateTimeField()
    
    @property
    def is_expired(self):
        return self.expired_at < timezone.now()

    @property
    def is_valid(self):
        return self.is_active and not self.is_used and not self.is_expired

    def __str__(self):
        return f"{self.pk} - {self.organization.title} - {self.email} - {self.token} - {self.is_active}"

    class Meta:
        ordering = ["-created_at"]