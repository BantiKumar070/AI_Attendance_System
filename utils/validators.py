"""
utils/validators.py
====================
Small, dependency-free validation helpers used by services/controllers
before touching the database. Kept framework-agnostic (no Flask imports)
so they are trivially unit-testable.
"""

from __future__ import annotations

import re

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")
ROLL_NUMBER_REGEX = re.compile(r"^[A-Za-z0-9\-_]{2,30}$")


def is_valid_email(value: str) -> bool:
    """Return True if ``value`` looks like a syntactically valid email address."""
    return bool(value) and bool(EMAIL_REGEX.match(value.strip()))


def is_valid_phone(value: str) -> bool:
    """Return True if ``value`` looks like a valid phone number."""
    return bool(value) and bool(PHONE_REGEX.match(value.strip()))


def is_valid_roll_number(value: str) -> bool:
    """Return True if ``value`` is a valid roll number / student ID format."""
    return bool(value) and bool(ROLL_NUMBER_REGEX.match(value.strip()))


def is_strong_password(value: str) -> bool:
    """
    Minimal password strength check: at least 8 characters, one letter
    and one digit. Intentionally simple to avoid frustrating admins while
    still blocking trivially weak passwords like "12345678".
    """
    if not value or len(value) < 8:
        return False
    return bool(re.search(r"[A-Za-z]", value)) and bool(re.search(r"[0-9]", value))


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Trim whitespace and cap length to prevent oversized/garbage input."""
    if value is None:
        return ""
    return value.strip()[:max_length]
