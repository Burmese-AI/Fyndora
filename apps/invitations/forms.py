from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Invitation
from apps.organizations.models import OrganizationMember


class InvitationCreateForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["email", "expired_at"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter invitee email",
                }
            ),
            "expired_at": forms.DateInput(
                attrs={"type": "datetime-local", "class": "input input-bordered w-full"}
            ),
        }

    def __init__(self, *args, organization=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")

        # Check if organization and user are provided
        if not self.organization and self.user:
            raise forms.ValidationError("Organization ID and User are required.")

        # Check if the inviter is the actual organization member based on the user obj and its provided organization ID
        if not OrganizationMember.objects.filter(
            user=self.user, organization=self.organization
        ).exists():
            raise forms.ValidationError(
                "You must be a member of the organization to send an invitation."
            )

        # Check if email belongs to someone existing in the provied organization
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if (
            user
            and OrganizationMember.objects.filter(
                organization=self.organization, user=user
            ).exists()
        ):
            raise forms.ValidationError(
                "User with this email is already a member of the organization."
            )

        return cleaned_data

    def clean_expired_at(self):
        expired_at = self.cleaned_data.get("expired_at")
        if expired_at and expired_at < timezone.now():
            raise forms.ValidationError("Expiration date must be in the future.")
        return expired_at
