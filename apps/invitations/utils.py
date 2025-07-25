from django.urls import reverse
from .models import Invitation


def get_invitation_url(
    request=None, invitation: Invitation = None, domain_override: str = None
) -> str:
    """
    Description: Build absolute invitation URL using request or domain override
    Used for sending invitation links via email or rendering in templates
    """

    # Check if invitation is provided
    if invitation is None:
        raise ValueError("invitation is required")

    # Get the relative path ("/invitations/<invitation_token>")
    relative_path = reverse(
        "accept_invitation", kwargs={"invitation_token": invitation.token}
    )

    # Use request to build absolute URI (best for views/templates)
    if request:
        return request.build_absolute_uri(relative_path)

    # if Domain is provieded
    if domain_override:
        return f"https://{domain_override}{relative_path}"

    raise ValueError("Either request or domain_override is required")
