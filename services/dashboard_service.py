"""
services/dashboard_service.py
==============================
Aggregates data from multiple models into the summary cards, tables,
and Chart.js datasets shown on the admin dashboard.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import func

from models import Attendance, ClassRoom, Student
from services.attendance_service import AttendanceService
from utils.extensions import db


class DashboardService:
    """Read-only aggregation queries for the dashboard view."""

    def __init__(self) -> None:
        self.attendance_service = AttendanceService()

    def get_overview(self, accessible_class_ids: Optional[List[int]] = None) -> Dict:
        """Top-level KPI cards: total students, classes, today's attendance %."""
        student_stmt = Student.query.filter_by(is_active=True)
        class_stmt = ClassRoom.query.filter_by(is_active=True)

        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                student_stmt = student_stmt.filter(db.false())
                class_stmt = class_stmt.filter(db.false())
            else:
                student_stmt = student_stmt.filter(Student.class_id.in_(accessible_class_ids))
                class_stmt = class_stmt.filter(ClassRoom.id.in_(accessible_class_ids))

        total_students = student_stmt.count()
        total_classes = class_stmt.count()
        today_summary = self.attendance_service.get_today_summary(accessible_class_ids=accessible_class_ids)

        return {
            "total_students": total_students,
            "total_classes": total_classes,
            **today_summary,
        }

    def get_weekly_trend_chart(self, accessible_class_ids: Optional[List[int]] = None) -> Dict[str, List]:
        """Data shaped for a Chart.js line chart: labels + present-count series."""
        trend = self.attendance_service.get_weekly_trend(days=7, accessible_class_ids=accessible_class_ids)
        return {
            "labels": [row["date"] for row in trend],
            "values": [row["count"] for row in trend],
        }

    def get_class_distribution_chart(self, accessible_class_ids: Optional[List[int]] = None) -> Dict[str, List]:
        """Data shaped for a Chart.js pie/doughnut chart: students per class."""
        stmt = Student.query.join(ClassRoom, isouter=True)
        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                stmt = stmt.filter(db.false())
            else:
                stmt = stmt.filter(Student.class_id.in_(accessible_class_ids))

        rows = stmt.with_entities(ClassRoom.name, func.count(Student.id)).group_by(ClassRoom.name).all()
        return {
            "labels": [row[0] or "Unassigned" for row in rows],
            "values": [row[1] for row in rows],
        }

    def get_recent_attendance(self, limit: int = 10, accessible_class_ids: Optional[List[int]] = None) -> List[Attendance]:
        """Most recent attendance marks, for the dashboard activity feed."""
        stmt = Attendance.query
        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                stmt = stmt.filter(db.false())
            else:
                stmt = stmt.filter(Attendance.class_id.in_(accessible_class_ids))
        return stmt.order_by(Attendance.created_at.desc()).limit(limit).all()

    def get_subject_breakdown(self, accessible_class_ids: Optional[List[int]] = None) -> List[Dict]:
        """Today's attendance broken down per subject/lecture — see AttendanceService for details."""
        return self.attendance_service.get_subject_wise_today(accessible_class_ids)
