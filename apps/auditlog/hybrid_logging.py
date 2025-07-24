"""
Hybrid audit logging approach for Fyndora.

This module provides a clean entry point for the audit logging system,
importing all necessary components from the modular structure.
"""

# Import all components to maintain backward compatibility
from .config import AuditConfig
from .utils_audit import (
    AuditSignalMixin,
    safe_audit_log,
    truncate_metadata,
    should_log_model,
)
from .business_logger import BusinessAuditLogger

# Import signal handlers to ensure they are registered
from . import signal_handlers  # noqa: F401
from . import auth_signals  # noqa: F401

# Re-export for backward compatibility
__all__ = [
    'AuditConfig',
    'AuditSignalMixin', 
    'BusinessAuditLogger',
    'safe_audit_log',
    'truncate_metadata',
    'should_log_model',
]