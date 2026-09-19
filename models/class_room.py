"""
models/class_room.py
=====================
Represents a class / batch / section (e.g. "BSc CS - Year 2 - Section A").

Named ``class_room`` (not ``class``) to avoid clashing with the Python
``class`` keyword and to keep the table name unambiguous.
"""

from __future__ import annotations

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db


class ClassRoom(db.Model, TimestampMixin, SerializerMixin):
    """A class / batch that groups students and subjects together."""

    __tablename__ = "class_rooms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    department = db.Column(db.String(100), nullable=True)          # e.g. "B.Tech", "BCA"
    name = db.Column(db.String(100), nullable=False)          # e.g. "BSc Computer Science"
    section = db.Column(db.String(20), nullable=True)          # e.g. "A"
    academic_year = db.Column(db.String(20), nullable=True)    # e.g. "2025-2026"
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # --- Relationships ---
    students = db.relationship("Student", back_populates="class_room", lazy="dynamic")
    subjects = db.relationship("Subject", back_populates="class_room", lazy="dynamic")

    def display_name(self) -> str:
        """Human-friendly label used throughout the UI, e.g. 'B.Tech — CS Year 2 (Section A)'."""
        parts = []
        if self.department:
            parts.append(self.department)
        label = self.name + (f" ({self.section})" if self.section else "")
        parts.append(label)
        return " — ".join(parts)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ClassRoom id={self.id} name={self.name!r} section={self.section!r}>"
