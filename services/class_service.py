"""
services/class_service.py
==========================
Business logic for class/batch management.
"""

from __future__ import annotations

from typing import Optional, Tuple

from models import ClassRoom
from utils.extensions import db
from utils.logger import get_logger
from utils.validators import sanitize_string

logger = get_logger(__name__)


class ClassService:
    """CRUD operations for ClassRoom."""

    def create_class(
        self, name: str, section: Optional[str] = None, academic_year: Optional[str] = None, department: Optional[str] = None
    ) -> Tuple[Optional[ClassRoom], Optional[str]]:
        name = sanitize_string(name, 100)
        if not name:
            return None, "Class name is required."

        existing = ClassRoom.query.filter_by(name=name, section=section, department=department).first()
        if existing:
            return None, "A class with this department, name, and section already exists."

        class_room = ClassRoom(
            name=name, section=section or None, academic_year=academic_year or None, department=department or None
        )
        db.session.add(class_room)
        db.session.commit()
        logger.info("Class created: %s %s %s", department or "", name, section or "")
        return class_room, None

    def update_class(self, class_id: int, **fields) -> Tuple[Optional[ClassRoom], Optional[str]]:
        class_room = ClassRoom.query.get(class_id)
        if class_room is None:
            return None, "Class not found."

        for field in ("name", "section", "academic_year", "department", "is_active"):
            if field in fields and fields[field] is not None:
                setattr(class_room, field, fields[field])

        db.session.commit()
        return class_room, None

    def delete_class(self, class_id: int) -> Tuple[bool, Optional[str]]:
        class_room = ClassRoom.query.get(class_id)
        if class_room is None:
            return False, "Class not found."
        if class_room.students.count() > 0:
            return False, "Cannot delete a class that still has students assigned to it."

        db.session.delete(class_room)
        db.session.commit()
        return True, None

    def get_all(self, active_only: bool = False):
        stmt = ClassRoom.query
        if active_only:
            stmt = stmt.filter_by(is_active=True)
        return stmt.order_by(ClassRoom.name.asc()).all()

    def get_by_id(self, class_id: int) -> Optional[ClassRoom]:
        return ClassRoom.query.get(class_id)
