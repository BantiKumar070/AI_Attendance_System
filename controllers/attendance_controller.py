"""
controllers/attendance_controller.py
=====================================
HTTP-facing coordination layer for attendance marking, history/search,
and export.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from services.attendance_service import AttendanceService
from services.export_service import ExportService
from utils.helpers import safe_int


class AttendanceController:
    """Coordinates attendance history/search/export requests."""

    def __init__(self) -> None:
        self.attendance_service = AttendanceService()
        self.export_service = ExportService()

    def history(self, args, accessible_class_ids=None):
        return self.attendance_service.get_history(
            start_date=self._parse_date(args.get("start_date")),
            end_date=self._parse_date(args.get("end_date")),
            student_id=safe_int(args.get("student_id")),
            class_id=safe_int(args.get("class_id")),
            subject_id=safe_int(args.get("subject_id")),
            status=args.get("status") or None,
            query=args.get("q") or None,
            page=safe_int(args.get("page"), 1),
            per_page=safe_int(args.get("per_page"), 25),
            accessible_class_ids=accessible_class_ids,
        )

    def export(self, args, file_format: str = "xlsx", accessible_class_ids=None) -> str:
        """Run the same filters as history() but return ALL matching rows for export."""
        pagination = self.attendance_service.get_history(
            start_date=self._parse_date(args.get("start_date")),
            end_date=self._parse_date(args.get("end_date")),
            student_id=safe_int(args.get("student_id")),
            class_id=safe_int(args.get("class_id")),
            subject_id=safe_int(args.get("subject_id")),
            status=args.get("status") or None,
            query=args.get("q") or None,
            page=1,
            per_page=100000,  # effectively "all" for export purposes
            accessible_class_ids=accessible_class_ids,
        )
        records = pagination.items
        if file_format == "pdf":
            return self.export_service.export_to_pdf(records)
        return self.export_service.export_to_excel(records)

    def mark_manual(self, student_id: int, subject_id: Optional[int], admin_username: str):
        return self.attendance_service.mark_manual(student_id, subject_id, admin_username)

    @staticmethod
    def _parse_date(value: Optional[str]):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
