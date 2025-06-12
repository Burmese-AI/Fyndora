"""
Global pytest configuration and fixtures for Fyndora testing.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model


@pytest.fixture
def user_model():
    """
    Return the user model for convenience.
    """
    return get_user_model()


@pytest.fixture
def test_case():
    """
    Provide a TestCase instance for use in tests that need it.
    """
    return TestCase()
