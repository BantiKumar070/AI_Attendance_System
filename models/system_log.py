"""
models/system_log.py
=====================
Persistent audit log of significant system events (logins, student
registrations, attendance marks, errors, settings changes, etc).

This is separate from the rotating file logs written via Python's
``logging`` module (see utils/logger.py) — those are for developers /
ops, this table is for the in-app "Logs" screen that admins can browse
and filter.
"""

from __future__ import annotations

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db


class LogLevel:
    """Severity levels shown in the Logs panel."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class SystemLog(db.Model, TimestampMixin, SerializerMixin):
    """A single audit-log entry."""

    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    actor = db.Column(db.String(120), nullable=True)     # username / "system"
    action = db.Column(db.String(100), nullable=False)   # e.g. "STUDENT_REGISTERED"
    description = db.Column(db.Text, nullable=True)
    level = db.Column(db.String(20), nullable=False, default=LogLevel.INFO)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SystemLog id={self.id} action={self.action!r} level={self.level!r}>"
