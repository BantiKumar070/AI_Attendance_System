"""
services/subject_service.py
============================
Business logic for subject/course management.
"""

from __future__ import annotations

from typing import Optional, Tuple

from models import Subject
from utils.extensions import db
from utils.logger import get_logger
from utils.validators import sanitize_string

logger = get_logger(__name__)


class SubjectService:
    """CRUD operations for Subject."""

    def create_subject(
        self, name: str, code: str, class_id: Optional[int] = None
    ) -> Tuple[Optional[Subject], Optional[str]]:
        name = sanitize_string(name, 120)
        code = sanitize_string(code, 30).upper()

        if not name or not code:
            return None, "Subject name and code are both required."
        if Subject.query.filter_by(code=code).first():
            return None, f"Subject code '{code}' is already in use."

        subject = Subject(name=name, code=code, class_id=class_id or None)
        db.session.add(subject)
        db.session.commit()
        logger.info("Subject created: %s (%s)", name, code)
        return subject, None

    def update_subject(self, subject_id: int, **fields) -> Tuple[Optional[Subject], Optional[str]]:
        subject = Subject.query.get(subject_id)
        if subject is None:
            return None, "Subject not found."

        for field in ("name", "code", "class_id", "is_active"):
            if field in fields and fields[field] is not None:
                setattr(subject, field, fields[field])

        db.session.commit()
        return subject, None

    def delete_subject(self, subject_id: int) -> Tuple[bool, Optional[str]]:
        subject = Subject.query.get(subject_id)
        if subject is None:
            return False, "Subject not found."

        db.session.delete(subject)
        db.session.commit()
        return True, None

    def get_all(self, class_id: Optional[int] = None, active_only: bool = False):
        stmt = Subject.query
        if class_id:
            stmt = stmt.filter_by(class_id=class_id)
        if active_only:
            stmt = stmt.filter_by(is_active=True)
        return stmt.order_by(Subject.name.asc()).all()

    def get_by_id(self, subject_id: int) -> Optional[Subject]:
        return Subject.query.get(subject_id)
