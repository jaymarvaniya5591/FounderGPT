"""
Admin Authentication Module
Simple password-based authentication for admin operations.
"""

import os
import sys
from functools import wraps

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings


def verify_admin_password(password: str) -> bool:
    """
    Verify if the provided password matches the admin password.
    Returns True if valid, False otherwise.
    """
    if not password:
        return False
    return password == settings.ADMIN_PASSWORD


def require_admin(password: str):
    """
    Decorator-style check for admin password.
    Raises ValueError if password is invalid.
    """
    if not verify_admin_password(password):
        raise ValueError("Invalid admin password")
