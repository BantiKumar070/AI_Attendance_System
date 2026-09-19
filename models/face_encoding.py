"""
models/face_encoding.py
========================
Stores the numeric face-encoding vectors produced by the
``face_recognition`` library for each student.

Each encoding is a 128-dimensional float64 numpy array. We persist it as
raw bytes (``numpy.ndarray.tobytes()``) inside a LargeBinary column,
which keeps the database engine-agnostic (works identically on SQLite
and MySQL) and avoids bloating the DB with base64 text.

A student typically has several rows here (one per good-quality frame
captured during enrollment), which the recognition service compares
against using majority voting for higher accuracy than a single
reference encoding.
"""

from __future__ import annotations

import numpy as np

from models.base import TimestampMixin
from utils.extensions import db

# face_recognition always returns 128-dimensional encodings
ENCODING_DIMENSIONS = 128


class FaceEncoding(db.Model, TimestampMixin):
    """A single 128-d face encoding vector belonging to a student."""

    __tablename__ = "face_encodings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    encoding = db.Column(db.LargeBinary, nullable=False)
    source_image = db.Column(db.String(255), nullable=True)  # dataset image this came from

    # --- Relationships ---
    student = db.relationship("Student", back_populates="face_encodings")

    def set_vector(self, vector: np.ndarray) -> None:
        """Serialize a numpy float64 vector into the binary column."""
        self.encoding = vector.astype(np.float64).tobytes()

    def get_vector(self) -> np.ndarray:
        """Deserialize the stored bytes back into a numpy float64 vector."""
        return np.frombuffer(self.encoding, dtype=np.float64)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FaceEncoding id={self.id} student_id={self.student_id}>"
