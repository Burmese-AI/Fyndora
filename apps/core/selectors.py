from typing import Optional
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    return User.objects.filter(email=email).first()
