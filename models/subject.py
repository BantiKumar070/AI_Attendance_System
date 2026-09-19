"""
models/subject.py
==================
Represents a subject / course taught to a particular class. Attendance
sessions are optionally tied to a subject (e.g. "Data Structures - 9AM
lecture") so a student can be marked present per-subject, per-day.
"""

from __future__ import annotations

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db


class Subject(db.Model, TimestampMixin, SerializerMixin):
    """A subject/course offered to a class."""

    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), nullable=False, unique=True, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_rooms.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # --- Relationships ---
    class_room = db.relationship("ClassRoom", back_populates="subjects")
    attendance_records = db.relationship("Attendance", back_populates="subject", lazy="dynamic")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Subject id={self.id} code={self.code!r} name={self.name!r}>"
