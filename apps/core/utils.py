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
