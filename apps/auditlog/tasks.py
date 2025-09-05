"""
Simplified Celery tasks for asynchronous audit logging.

This module provides basic async wrappers for audit_create functions.
"""

import logging
from typing import Any, Dict, Optional

from celery import shared_task
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from .services import (
    audit_create,
    audit_create_authentication_event,
    audit_create_security_event,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 2},
)
def audit_create_async(
    self,
    user_id: Optional[str],
    action_type: str,
    target_entity: Optional[Dict[str, Any]] = None,
    workspace: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Asynchronous wrapper for audit_create function matching service signature."""
    try:
        # Resolve user
        user = None
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
            except ObjectDoesNotExist:
                logger.warning(f"User with ID {user_id} not found for audit logging")
                user = None

        # Resolve target entity
        entity_instance = None
        if target_entity:
            try:
                # Handle both model instances and dictionaries
                if hasattr(target_entity, "_meta"):  # It's a model instance
                    entity_instance = target_entity
                else:  # It's a dictionary
                    model_path = target_entity["model"]
                    entity_pk = target_entity["pk"]

                    # Import the model class from the string path
                    from django.apps import apps

                    # model_path format: 'apps.workspaces.models.Team'
                    # Extract app_label and model_name
                    path_parts = model_path.split(".")
                    app_label = path_parts[
                        1
                    ]  # 'workspaces' from 'apps.workspaces.models.Team'
                    model_name = path_parts[
                        -1
                    ]  # 'Team' from 'apps.workspaces.models.Team'
                    model_class = apps.get_model(app_label, model_name)

                    entity_instance = model_class.objects.get(pk=entity_pk)
            except (KeyError, ObjectDoesNotExist, LookupError, AttributeError) as e:
                logger.warning(f"Target entity not found: {e}")
                entity_instance = None

        # Resolve workspace
        workspace_instance = None
        if workspace:
            try:
                # Handle both model instances and dictionaries
                if hasattr(workspace, "_meta"):  # It's a model instance
                    workspace_instance = workspace
                else:  # It's a dictionary
                    from apps.workspaces.models import Workspace

                    workspace_instance = Workspace.objects.get(pk=workspace["pk"])
                    # i added this validation error for testing purposes
            except (KeyError, ObjectDoesNotExist, AttributeError, ValidationError) as e:
                logger.warning(f"Workspace not found: {e}")
                workspace_instance = None

        # Create audit log using service function signature
        audit = audit_create(
            user=user,
            action_type=action_type,
            target_entity=entity_instance,
            workspace=workspace_instance,
            metadata=metadata or {},
        )

        if audit:
            logger.debug(f"Async audit created: {audit.audit_id}")
            return str(audit.audit_id)
        else:
            logger.warning("Audit creation returned None")
            return None

    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        return None


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 2},
)
def audit_create_security_event_async(
    self,
    user_id: Optional[str],
    action_type: str,
    target_entity: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Asynchronous wrapper for audit_create_security_event function matching service signature."""
    try:
        # Resolve user
        user = None
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
            except ObjectDoesNotExist:
                logger.warning(f"User with ID {user_id} not found for security audit")
                user = None

        # Resolve target entity
        entity_instance = None
        if target_entity:
            try:
                # Handle both model instances and dictionaries
                if hasattr(target_entity, "_meta"):  # It's a model instance
                    entity_instance = target_entity
                else:  # It's a dictionary
                    model_path = target_entity["model"]
                    entity_pk = target_entity["pk"]

                    # Import the model class from the string path
                    from django.apps import apps

                    # model_path format: 'apps.workspaces.models.Team'
                    # Extract app_label and model_name
                    path_parts = model_path.split(".")
                    app_label = path_parts[
                        1
                    ]  # 'workspaces' from 'apps.workspaces.models.Team'
                    model_name = path_parts[
                        -1
                    ]  # 'Team' from 'apps.workspaces.models.Team'
                    model_class = apps.get_model(app_label, model_name)

                    entity_instance = model_class.objects.get(pk=entity_pk)
            except (KeyError, ObjectDoesNotExist, LookupError, AttributeError) as e:
                logger.warning(f"Target entity not found: {e}")
                entity_instance = None

        # Create security audit log using service function signature
        audit = audit_create_security_event(
            user=user,
            action_type=action_type,
            target_entity=entity_instance,
            metadata=metadata or {},
        )

        if audit:
            logger.debug(f"Async security audit created: {audit.audit_id}")
            return str(audit.audit_id)
        else:
            logger.warning("Security audit creation returned None")
            return None

    except Exception as e:
        logger.error(f"Failed to create security audit log: {e}")
        return None


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 2},
)
def audit_create_authentication_event_async(
    self,
    user_id: Optional[str],
    action_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Asynchronous wrapper for audit_create_authentication_event function matching service signature."""
    try:
        # Resolve user
        user = None
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
            except ObjectDoesNotExist:
                logger.warning(f"User with ID {user_id} not found for auth audit")
                user = None

        # Create authentication audit log using service function signature
        audit = audit_create_authentication_event(
            user=user,
            action_type=action_type,
            metadata=metadata or {},
        )

        if audit:
            logger.debug(f"Async auth audit created: {audit.audit_id}")
            return str(audit.audit_id)
        else:
            logger.warning("Authentication audit creation returned None")
            return None

    except Exception as e:
        logger.error(f"Failed to create authentication audit log: {e}")
        return None


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 2},
)
def audit_create_bulk_async(
    self, audit_entries: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """Simplified asynchronous bulk audit creation for batch operations."""
    success_count = 0
    failed_count = 0
    audit_ids = []

    for entry in audit_entries:
        try:
            audit_id = audit_create_async.apply_async(kwargs=entry).get(timeout=30)

            if audit_id:
                audit_ids.append(audit_id)
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Failed to process bulk audit entry: {e}")
            failed_count += 1

    result = {
        "success_count": success_count,
        "failed_count": failed_count,
        "audit_ids": audit_ids,
        "total_processed": len(audit_entries),
    }

    logger.info(f"Bulk audit processing completed: {result}")
    return result
