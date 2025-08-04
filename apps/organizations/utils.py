"""
Utility functions for organization audit logging.
"""


def extract_organization_context(organization):
    """
    Extract business context from Organization instance for audit logging.

    Args:
        organization: Organization instance

    Returns:
        dict: Business context for audit logging
    """
    if not organization:
        return {}

    return {
        "organization_id": str(organization.organization_id),
        "organization_title": organization.title,
        "organization_status": getattr(organization, "status", None),
        "organization_description": getattr(organization, "description", None),
        "owner_id": str(organization.owner.user.user_id)
        if organization.owner and organization.owner.user
        else None,
        "owner_email": organization.owner.user.email
        if organization.owner and organization.owner.user
        else None,
    }


def extract_organization_member_context(member):
    """
    Extract business context from OrganizationMember instance for audit logging.

    Args:
        member: OrganizationMember instance

    Returns:
        dict: Business context for audit logging
    """
    if not member:
        return {}

    return {
        "member_id": str(member.id),
        "organization_id": str(member.organization.organization_id),
        "organization_title": member.organization.title,
        "user_id": str(member.user.user_id),
        "user_email": member.user.email,
        "member_status": getattr(member, "status", "active"),
        "is_active": getattr(member, "is_active", True),
        "role": getattr(member, "role", "member"),
    }


def extract_organization_exchange_rate_context(exchange_rate):
    """
    Extract business context from OrganizationExchangeRate instance for audit logging.

    Args:
        exchange_rate: OrganizationExchangeRate instance

    Returns:
        dict: Business context for audit logging
    """
    if not exchange_rate:
        return {}

    return {
        "exchange_rate_id": str(exchange_rate.id),
        "organization_id": str(exchange_rate.organization.organization_id),
        "organization_title": exchange_rate.organization.title,
        "currency_code": exchange_rate.currency.code,
        "rate": str(exchange_rate.rate),
        "effective_date": exchange_rate.effective_date.isoformat()
        if exchange_rate.effective_date
        else None,
        "added_by_id": str(exchange_rate.added_by.user.user_id)
        if exchange_rate.added_by and exchange_rate.added_by.user
        else None,
        "added_by_email": exchange_rate.added_by.user.email
        if exchange_rate.added_by and exchange_rate.added_by.user
        else None,
        "note": exchange_rate.note,
    }


def get_user_from_request():
    """
    Extract user from current request context.
    This is a placeholder - in real implementation, you might use threading.local
    or pass request context through the call chain.

    Returns:
        User instance or None
    """
    # This would need to be implemented based on your request handling pattern
    # For now, returning None to avoid errors
    return None


def extract_request_metadata():
    """
    Extract metadata from current request context.
    This is a placeholder - in real implementation, you might use threading.local
    or pass request context through the call chain.

    Returns:
        dict: Request metadata
    """
    # This would need to be implemented based on your request handling pattern
    return {
        "ip_address": "unknown",
        "user_agent": "unknown",
        "http_method": "unknown",
        "request_path": "unknown",
        "session_key": None,
        "source": "service_call",
    }
