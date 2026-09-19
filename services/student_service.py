"""
services/student_service.py
============================
Business logic for student management: registration, updates,
listing/search, and soft-deletion. Face dataset capture and encoding
live in ``services/face_service.py`` — this module only manages the
``Student`` record itself.
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import or_

from models import Student, SystemLog, LogLevel
from utils.extensions import db
from utils.logger import get_logger
from utils.validators import is_valid_email, is_valid_phone, is_valid_roll_number, sanitize_string

logger = get_logger(__name__)


class StudentService:
    """Encapsulates CRUD and query operations for students."""

    def create_student(
        self,
        roll_number: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        gender: Optional[str] = None,
        class_id: Optional[int] = None,
    ) -> Tuple[Optional[Student], Optional[str]]:
        """Register a new student. Returns (Student, None) or (None, error)."""
        roll_number = sanitize_string(roll_number, 30)
        name = sanitize_string(name, 120)

        if not is_valid_roll_number(roll_number):
            return None, "Roll number must be 2-30 alphanumeric characters (dashes/underscores allowed)."
        if not name:
            return None, "Student name is required."
        if email and not is_valid_email(email):
            return None, "Invalid email address."
        if phone and not is_valid_phone(phone):
            return None, "Invalid phone number."
        if Student.query.filter_by(roll_number=roll_number).first():
            return None, f"A student with roll number '{roll_number}' already exists."
        if email and Student.query.filter_by(email=email).first():
            return None, f"A student with email '{email}' already exists."

        student = Student(
            roll_number=roll_number,
            name=name,
            email=email or None,
            phone=phone or None,
            gender=gender or None,
            class_id=class_id or None,
        )
        db.session.add(student)
        db.session.commit()

        self._log("STUDENT_REGISTERED", f"Student '{name}' ({roll_number}) registered.")
        logger.info("Student registered: %s (%s)", name, roll_number)
        return student, None

    def update_student(self, student_id: int, **fields) -> Tuple[Optional[Student], Optional[str]]:
        """Update mutable fields on an existing student record."""
        student = Student.query.get(student_id)
        if student is None:
            return None, "Student not found."

        if "email" in fields and fields["email"] and not is_valid_email(fields["email"]):
            return None, "Invalid email address."
        if "phone" in fields and fields["phone"] and not is_valid_phone(fields["phone"]):
            return None, "Invalid phone number."

        for field in ("name", "email", "phone", "gender", "class_id", "is_active"):
            if field in fields and fields[field] is not None:
                setattr(student, field, fields[field])

        db.session.commit()
        self._log("STUDENT_UPDATED", f"Student '{student.name}' ({student.roll_number}) updated.")
        return student, None

    def delete_student(self, student_id: int) -> Tuple[bool, Optional[str]]:
        """Permanently delete a student and their face encodings/attendance history."""
        student = Student.query.get(student_id)
        if student is None:
            return False, "Student not found."

        name, roll = student.name, student.roll_number
        db.session.delete(student)
        db.session.commit()

        self._log("STUDENT_DELETED", f"Student '{name}' ({roll}) deleted.", level=LogLevel.WARNING)
        return True, None

    def get_by_id(self, student_id: int) -> Optional[Student]:
        return Student.query.get(student_id)

    def search(
        self,
        query: Optional[str] = None,
        class_id: Optional[int] = None,
        face_registered: Optional[bool] = None,
        page: int = 1,
        per_page: int = 25,
        accessible_class_ids: Optional[list] = None,
    ):
        """
        Paginated, filterable student search for the listing page / API.

        Args:
            accessible_class_ids: If not None, restricts results to these
                ClassRoom IDs regardless of `class_id` — used to enforce a
                teacher account's assigned-classes restriction. An empty
                list means "no classes assigned" -> zero results.
        """
        stmt = Student.query

        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                stmt = stmt.filter(db.false())
            else:
                stmt = stmt.filter(Student.class_id.in_(accessible_class_ids))

        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.filter(or_(Student.name.ilike(like), Student.roll_number.ilike(like), Student.email.ilike(like)))
        if class_id:
            stmt = stmt.filter(Student.class_id == class_id)
        if face_registered is not None:
            stmt = stmt.filter(Student.face_registered == face_registered)

        stmt = stmt.order_by(Student.name.asc())
        return stmt.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def _log(action: str, description: str, level: str = LogLevel.INFO) -> None:
        try:
            db.session.add(SystemLog(actor="admin", action=action, description=description, level=level))
            db.session.commit()
        except Exception:  # pragma: no cover
            db.session.rollback()
            logger.exception("Failed to write system log for action=%s", action)
