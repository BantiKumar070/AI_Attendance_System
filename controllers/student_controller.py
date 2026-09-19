"""
controllers/student_controller.py
==================================
HTTP-facing coordination layer for student registration/management and
the face-capture wizard. Delegates actual logic to StudentService and
FaceService.
"""

from __future__ import annotations

from typing import Optional

from models import Student
from services.face_service import FaceService
from services.student_service import StudentService
from utils.helpers import safe_int


class StudentController:
    """Coordinates student CRUD requests and the capture/enrollment wizard."""

    def __init__(self) -> None:
        self.student_service = StudentService()
        self.face_service = FaceService()

    def register(self, form) -> tuple[Optional[Student], Optional[str]]:
        """Register a new student from a Flask form/multidict."""
        return self.student_service.create_student(
            roll_number=form.get("roll_number", ""),
            name=form.get("name", ""),
            email=form.get("email") or None,
            phone=form.get("phone") or None,
            gender=form.get("gender") or None,
            class_id=safe_int(form.get("class_id")),
        )

    def update(self, student_id: int, form):
        return self.student_service.update_student(
            student_id,
            name=form.get("name"),
            email=form.get("email"),
            phone=form.get("phone"),
            gender=form.get("gender"),
            class_id=safe_int(form.get("class_id")),
            is_active=form.get("is_active") == "on" if "is_active" in form else None,
        )

    def delete(self, student_id: int):
        return self.student_service.delete_student(student_id)

    def list_students(self, args, accessible_class_ids=None):
        return self.student_service.search(
            query=args.get("q"),
            class_id=safe_int(args.get("class_id")),
            face_registered=(
                args.get("face_registered") == "true" if args.get("face_registered") in ("true", "false") else None
            ),
            page=safe_int(args.get("page"), 1),
            per_page=safe_int(args.get("per_page"), 25),
            accessible_class_ids=accessible_class_ids,
        )

    def capture_frame(self, student_id: int, image_base64: str):
        student = self.student_service.get_by_id(student_id)
        if student is None:
            return None, "Student not found."
        return self.face_service.save_capture_frame(student, image_base64)

    def capture_progress(self, student_id: int):
        student = self.student_service.get_by_id(student_id)
        if student is None:
            return None
        return self.face_service.capture_progress(student)

    def generate_encodings(self, student_id: int):
        student = self.student_service.get_by_id(student_id)
        if student is None:
            return 0, "Student not found."
        return self.face_service.generate_encodings_for_student(student)
