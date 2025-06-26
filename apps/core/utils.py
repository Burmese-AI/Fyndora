from django.core.paginator import Paginator
from .constants import PAGINATION_SIZE


def percent_change(current: float, previous: float) -> str:
    if previous == 0:
        return "0% change"
    change = ((current - previous) / previous) * 100
    symbol = "+" if change >= 0 else "-"
    return f"{symbol}{abs(change):.1f}% from last period"


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
