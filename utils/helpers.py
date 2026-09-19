"""
utils/helpers.py
=================
Grab-bag of small, generally useful helper functions shared across
services and controllers. Nothing here talks to the database directly.
"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from typing import Optional

from flask import current_app


def allowed_file(filename: str) -> bool:
    """Check a filename's extension against ALLOWED_IMAGE_EXTENSIONS."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def slugify(value: str) -> str:
    """
    Convert a display name into a filesystem-safe slug.
    e.g. "Jôhn Doe" -> "john-doe"
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def student_dataset_folder(roll_number: str, name: str) -> str:
    """
    Build the dataset folder path for a given student, e.g.:
    dataset/CS2024001_john-doe/
    """
    folder_name = f"{roll_number}_{slugify(name)}"
    return os.path.join(current_app.config["DATASET_FOLDER"], folder_name)


def generate_roll_number(class_code: str, sequence: int) -> str:
    """
    Auto-generate a roll number when the admin doesn't supply one, e.g.:
    generate_roll_number("CS", 7) -> "CS-2026-007"
    """
    year = datetime.now().year
    return f"{class_code.upper()}-{year}-{sequence:03d}"


def format_timedelta_minutes(minutes: int) -> str:
    """Human friendly representation of a minute count, e.g. 90 -> '1h 30m'."""
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def safe_int(value, default: Optional[int] = None) -> Optional[int]:
    """Parse an int from arbitrary input (e.g. query params), returning default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
