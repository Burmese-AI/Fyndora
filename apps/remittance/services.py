from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.core.utils import model_update
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember


def remittance_confirm_payment(*, remittance, user):
    """
    Confirms a remittance payment.
    """
    team = remittance.workspace_team.team

    try:
        # TODO: Use selectors if available
        team_member = TeamMember.objects.get(team=team, organization_member__user=user)

        allowed_roles = [
            TeamMemberRole.WORKSPACE_ADMIN,
            TeamMemberRole.OPERATIONS_REVIEWER,
        ]

        if team_member.role not in allowed_roles:
            raise PermissionDenied(
                "You do not have permission to confirm this remittance."
            )

    except TeamMember.DoesNotExist:
        raise PermissionDenied(
            "You are not a member of the team associated with this remittance."
        )

    if remittance.paid_amount < remittance.due_amount:
        raise ValidationError(
            "Cannot confirm payment: The due amount has not been fully paid."
        )

    updated_remittance, _ = model_update(
        instance=remittance,
        fields=["confirmed_by", "confirmed_at"],
        data={
            "confirmed_by": user,
            "confirmed_at": timezone.now(),
        },
    )

    return updated_remittance
