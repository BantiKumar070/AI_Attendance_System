"""
models/student.py
==================
Represents a registered student whose face has been (or is being)
enrolled into the recognition system.

Design notes:
    * ``roll_number`` is the human-friendly unique identifier used
      throughout the UI and dataset folder names
      (dataset/<roll_number>_<name>/img_0001.jpg).
    * The actual face encodings live in the ``FaceEncoding`` table
      (one-to-many) so a student can have multiple encodings captured
      from different angles/lighting, improving recognition accuracy.
    * ``face_registered`` is a denormalized flag kept in sync by the
      face-encoding service, so listing pages don't need an expensive
      join just to show enrollment status.
"""

from __future__ import annotations

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db


class Student(db.Model, TimestampMixin, SerializerMixin):
    """A student enrolled in the attendance system."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    roll_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_rooms.id"), nullable=True)

    dataset_path = db.Column(db.String(255), nullable=True)   # folder with captured images
    photo_path = db.Column(db.String(255), nullable=True)     # profile picture for UI
    face_registered = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # --- Relationships ---
    class_room = db.relationship("ClassRoom", back_populates="students")
    face_encodings = db.relationship(
        "FaceEncoding", back_populates="student", cascade="all, delete-orphan", lazy="dynamic"
    )
    attendance_records = db.relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, exclude: tuple = ()) -> dict:
        """Serialize the student, adding a friendly class name for the UI."""
        data = super().to_dict(exclude=exclude)
        data["class_name"] = self.class_room.display_name() if self.class_room else None
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Student id={self.id} roll_number={self.roll_number!r} name={self.name!r}>"
