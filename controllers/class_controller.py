"""
controllers/class_controller.py
================================
HTTP-facing coordination layer for class/batch management.
"""

from __future__ import annotations

from services.class_service import ClassService


class ClassController:
    """Coordinates class-management requests."""

    def __init__(self) -> None:
        self.class_service = ClassService()

    def create(self, form):
        return self.class_service.create_class(
            name=form.get("name", ""),
            section=form.get("section") or None,
            academic_year=form.get("academic_year") or None,
            department=form.get("department") or None,
        )

    def update(self, class_id: int, form):
        return self.class_service.update_class(
            class_id,
            name=form.get("name"),
            section=form.get("section"),
            academic_year=form.get("academic_year"),
            department=form.get("department"),
            is_active=form.get("is_active") == "on" if "is_active" in form else None,
        )

    def delete(self, class_id: int):
        return self.class_service.delete_class(class_id)

    def list_all(self, accessible_class_ids=None):
        classes = self.class_service.get_all()
        if accessible_class_ids is not None:
            classes = [c for c in classes if c.id in accessible_class_ids]
        return classes
