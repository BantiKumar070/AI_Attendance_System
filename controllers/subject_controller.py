"""
controllers/subject_controller.py
==================================
HTTP-facing coordination layer for subject/course management.
"""

from __future__ import annotations

from services.subject_service import SubjectService
from utils.helpers import safe_int


class SubjectController:
    """Coordinates subject-management requests."""

    def __init__(self) -> None:
        self.subject_service = SubjectService()

    def create(self, form):
        return self.subject_service.create_subject(
            name=form.get("name", ""),
            code=form.get("code", ""),
            class_id=safe_int(form.get("class_id")),
        )

    def update(self, subject_id: int, form):
        return self.subject_service.update_subject(
            subject_id,
            name=form.get("name"),
            code=form.get("code"),
            class_id=safe_int(form.get("class_id")),
            is_active=form.get("is_active") == "on" if "is_active" in form else None,
        )

    def delete(self, subject_id: int):
        return self.subject_service.delete_subject(subject_id)

    def list_all(self, class_id=None, active_only: bool = False):
        return self.subject_service.get_all(class_id=safe_int(class_id), active_only=active_only)
