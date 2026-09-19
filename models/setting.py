"""
models/setting.py
==================
A simple key-value store backing the "Settings" panel in the admin
dashboard (e.g. recognition tolerance, cooldown minutes, email toggle).

Kept as a generic key/value table (rather than dedicated columns on some
config table) so new settings can be added from the UI without a schema
migration.
"""

from __future__ import annotations

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db


class Setting(db.Model, TimestampMixin, SerializerMixin):
    """A single configurable system setting."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Setting key={self.key!r} value={self.value!r}>"
