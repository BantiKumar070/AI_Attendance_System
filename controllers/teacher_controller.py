"""
controllers/teacher_controller.py
==================================
HTTP-facing coordination layer for superadmin-only teacher account
management: creating teacher logins and assigning them to classes.
"""

from __future__ import annotations

from models import AdminRole
from services.auth_service import AuthService
from utils.helpers import safe_int


class TeacherController:
    """Coordinates teacher account creation, listing, and class assignment."""

    def __init__(self) -> None:
        self.auth_service = AuthService()

    def list_teachers(self):
        return self.auth_service.list_teachers()

    def create_teacher(self, form):
        subject_ids = [safe_int(sid) for sid in form.getlist("subject_ids")]
        subject_ids = [sid for sid in subject_ids if sid is not None]

        return self.auth_service.create_admin(
            username=form.get("username", ""),
            email=form.get("email", ""),
            full_name=form.get("full_name", ""),
            password=form.get("password", ""),
            role=AdminRole.TEACHER,
            subject_ids=subject_ids,
        )

    def update_assignments(self, admin_id: int, form):
        subject_ids = [safe_int(sid) for sid in form.getlist("subject_ids")]
        subject_ids = [sid for sid in subject_ids if sid is not None]
        return self.auth_service.assign_subjects(admin_id, subject_ids)

    def deactivate(self, admin_id: int):
        return self.auth_service.deactivate_admin(admin_id)

    def unlock(self, admin_id: int):
        return self.auth_service.unlock_admin(admin_id)

    def reset_password(self, admin_id: int, form):
        new_password = form.get("new_password", "")
        confirm_password = form.get("confirm_password", "")
        if new_password != confirm_password:
            return False, "New password and confirmation do not match."
        return self.auth_service.reset_password_direct(admin_id, new_password)
