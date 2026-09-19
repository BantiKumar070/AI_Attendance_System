"""
models/__init__.py
===================
Aggregates every ORM model so that:

    1. ``from models import db`` works anywhere in the codebase.
    2. Importing this package once is enough to register every model's
       table with SQLAlchemy's metadata (required for
       ``db.create_all()`` and Flask-Migrate autogeneration to see
       every table).

Import order matters only for readability here — SQLAlchemy resolves
relationships lazily via string names, so circular references between
Student <-> ClassRoom <-> Attendance are safe.
"""

from utils.extensions import db  # noqa: F401  (re-exported for convenience)

from models.admin import Admin, AdminRole  # noqa: F401,E402
from models.class_room import ClassRoom  # noqa: F401,E402
from models.subject import Subject  # noqa: F401,E402
from models.student import Student  # noqa: F401,E402
from models.face_encoding import FaceEncoding  # noqa: F401,E402
from models.attendance import Attendance, AttendanceStatus, MarkedBy  # noqa: F401,E402
from models.system_log import SystemLog, LogLevel  # noqa: F401,E402
from models.setting import Setting  # noqa: F401,E402

__all__ = [
    "db",
    "Admin",
    "AdminRole",
    "ClassRoom",
    "Subject",
    "Student",
    "FaceEncoding",
    "Attendance",
    "AttendanceStatus",
    "MarkedBy",
    "SystemLog",
    "LogLevel",
    "Setting",
]
