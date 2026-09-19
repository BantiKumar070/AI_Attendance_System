"""
models/attendance.py
=====================
Represents a single attendance record: one student, marked present (or
late) on a given date, optionally scoped to a subject.

Duplicate prevention:
    A unique constraint on (student_id, subject_id, attendance_date)
    guarantees that, at the database level, a student can only have ONE
    attendance row per subject per day — regardless of how many times
    their face is detected by the camera. The recognition service also
    applies a short in-memory cooldown so the same face isn't even
    re-processed for a few seconds after being marked, but the DB
    constraint is the authoritative guard.
"""

from __future__ import annotations

from datetime import date, time

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db


class AttendanceStatus:
    """Enumeration of valid attendance statuses (kept as plain strings for SQLite compatibility)."""

    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"


class MarkedBy:
    """Enumeration describing how the attendance row was created."""

    FACE_RECOGNITION = "face_recognition"
    MANUAL = "manual"


class Attendance(db.Model, TimestampMixin, SerializerMixin):
    """A single day's attendance entry for one student."""

    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("student_id", "subject_id", "attendance_date", name="uq_attendance_once_per_day"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_rooms.id"), nullable=True, index=True)

    attendance_date: date = db.Column(db.Date, nullable=False, index=True)
    time_in: time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=AttendanceStatus.PRESENT)
    marked_by = db.Column(db.String(30), nullable=False, default=MarkedBy.FACE_RECOGNITION)
    confidence_score = db.Column(db.Float, nullable=True)  # recognition confidence (0-1)

    # --- Relationships ---
    student = db.relationship("Student", back_populates="attendance_records")
    subject = db.relationship("Subject", back_populates="attendance_records")
    class_room = db.relationship("ClassRoom")

    def to_dict(self, exclude: tuple = ()) -> dict:
        """Serialize including a few convenient denormalized fields for the UI."""
        data = super().to_dict(exclude=exclude)
        data["student_name"] = self.student.name if self.student else None
        data["roll_number"] = self.student.roll_number if self.student else None
        data["subject_name"] = self.subject.name if self.subject else None
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Attendance id={self.id} student_id={self.student_id} "
            f"date={self.attendance_date} status={self.status!r}>"
        )
