from functools import wraps
from decimal import Decimal, ROUND_HALF_UP
from typing import Type, Any, Callable

from django.core.paginator import Paginator
from django.contrib import messages
from django.shortcuts import redirect
from django_htmx.http import HttpResponseClientRedirect
from django.contrib.auth.models import Group
from django.db import DatabaseError

from .constants import PAGINATION_SIZE
from .exceptions import BaseServiceError
from .permissions import OrganizationPermissions

def percent_change(current: float, previous: float) -> str:
    if previous == 0:
        return "0% change"
    change = ((current - previous) / previous) * 100
    symbol = "+" if change >= 0 else "-"
    return f"{symbol}{abs(change):.1f}% from last period"


def round_decimal(value, places=2):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_paginated_context(
    *, queryset, context={}, object_name, page_size=PAGINATION_SIZE, page_no=1
):
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_no)
    context.update(
        {
            "page_obj": page_obj,
            "paginator": paginator,
            object_name: page_obj.object_list,
            "is_paginated": paginator.num_pages > 1,
        }
    )
    return context


def model_update(
    instance,
    data,
    update_fields=None,
):
    """
    Generic update function that follows HackSoft Django Styleguide patterns.

    This function:
    1. Updates model instance fields from data dict
    2. Performs full_clean() validation
    3. Saves the instance with specified update_fields
    4. Returns the updated instance

    Args:
        instance: The model instance to update
        data: Dictionary of field names and their new values
        update_fields: List of field names to update in the database.
                      If None, all fields will be saved.

    Returns:
        Updated model instance

    Raises:
        ValidationError: If validation fails

    Example:
        user = model_update(
            instance=user,
            data={
                'email': 'new@example.com',
                'first_name': 'John',
            },
            update_fields=['email', 'first_name']
        )
    """
    # Update fields from data
    for field_name, field_value in data.items():
        setattr(instance, field_name, field_value)

    # Validate the instance
    instance.full_clean()

    # Save the instance with specified fields
    instance.save(update_fields=update_fields)

    return instance


def permission_denied_view(request, message):
    messages.error(request, message)
    if request.headers.get("HX-Request"):
        return HttpResponseClientRedirect("/403")
    else:
        return redirect("permission_denied")


def can_manage_organization(user, organization):
    """
    Returns True if the user has the permission to manage the organization.
    """
    return user.has_perm(OrganizationPermissions.MANAGE_ORGANIZATION, organization)


def revoke_workspace_admin_permission(user, workspace):
    workspace_admins_group_name = f"Workspace Admins - {workspace.workspace_id}"
    workspace_admins_group, _ = Group.objects.get_or_create(
        name=workspace_admins_group_name
    )
    workspace_admins_group.user_set.remove(user)


def revoke_operations_reviewer_permission(user, workspace):
    operations_reviewer_group_name = f"Operations Reviewer - {workspace.workspace_id}"
    operations_reviewer_group, _ = Group.objects.get_or_create(
        name=operations_reviewer_group_name
    )
    operations_reviewer_group.user_set.remove(user)


def revoke_team_coordinator_permission(user, team):
    team_coordinator_group_name = f"Team Coordinator - {team.team_id}"
    team_coordinator_group, _ = Group.objects.get_or_create(
        name=team_coordinator_group_name
    )
    team_coordinator_group.user_set.remove(user)


def revoke_workspace_team_member_permission(user, workspace_team):
    workspace_team_group_name = f"Workspace Team - {workspace_team.workspace_team_id}"
    workspace_team_group, _ = Group.objects.get_or_create(
        name=workspace_team_group_name
    )
    workspace_team_group.user_set.remove(user)


def check_if_member_is_owner(member, organization):
    # Check if organization has an owner first
    # this is a edge case, but it's possible that the organization has no owner but i added this for testing purposes
    if organization.owner is None:
        return False

    if member.user == organization.owner.user:
        return True
    return False


def handle_service_errors(
    error_class: type[BaseServiceError] = BaseServiceError,
    return_value = None,
    context: dict | None = None,
):
    """
    Decorator to automatically catch exceptions and wrap them into service errors.

    Args:
        raise_error (bool): If True, raise the error; otherwise return return_value.
        return_value: Value returned instead of raising when raise_error=False.
        error_class (type): Base error class to use (default BaseServiceError).
        context (dict): Static context to always include.
    """
    
    # Build static context
    final_context = dict(context or {})

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            
            try:
                return func(*args, **kwargs)            
            except BaseServiceError as err:
                if return_value:
                    return return_value
                raise err
            
            except Exception as err:
                if return_value:
                    return return_value
                # Convert into proper service error
                raise error_class.from_exception(
                    err,
                    context=final_context,
                ) 
                
        return wrapper
    return decorator