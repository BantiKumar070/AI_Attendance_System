
"""
services/attendance_service.py
===============================
Business logic for marking attendance (from face recognition or
manually) and for querying attendance history / search / analytics.

Duplicate prevention strategy (defense in depth):
    1. FaceService cooldown — skip re-processing a face seen < 8s ago.
    2. Explicit pre-check here — skip if today's row already exists.
    3. Database UNIQUE constraint (student_id, subject_id, attendance_date)
       — the authoritative guard even under concurrent requests.
"""

from __future__ import annotations

from datetime import date, datetime, time as dt_time
from typing import Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from models import Attendance, AttendanceStatus, MarkedBy, Student, SystemLog, LogLevel
from services.settings_service import SettingsService
from services.email_service import EmailService
from utils.extensions import db
from utils.logger import get_logger

logger = get_logger(__name__)


class AttendanceService:
    """Encapsulates attendance marking and reporting logic."""

    def __init__(self) -> None:
        self.settings_service = SettingsService()
        self.email_service = EmailService()

    def _get_late_cutoff_hour(self) -> Optional[int]:
        """
        Read the configurable late-cutoff hour from Settings.

        Returns:
            An hour (0-23) after which a mark counts as "late", or None
            if the feature is disabled (every mark simply counts as
            "present", which is the sensible default outside a strict
            school-bell schedule).
        """
        raw = self.settings_service.get("late_cutoff_hour", "")
        if not raw or not raw.strip():
            return None
        try:
            hour = int(raw)
            return hour if 0 <= hour <= 23 else None
        except ValueError:
            return None

    def mark_attendance(
        self,
        student_id: int,
        subject_id: Optional[int] = None,
        confidence: Optional[float] = None,
        marked_by: str = MarkedBy.FACE_RECOGNITION,
    ) -> Tuple[Optional[Attendance], bool, Optional[str]]:
        """
        Mark a student present for today (optionally for a specific
        subject session).

        Returns:
            (Attendance | None, was_newly_created: bool, error_message | None)
        """
        student = Student.query.get(student_id)
        if student is None:
            return None, False, "Student not found."

        today = date.today()
        now = datetime.now().time()

        existing = Attendance.query.filter_by(
            student_id=student_id, subject_id=subject_id, attendance_date=today
        ).first()
        if existing is not None:
            return existing, False, None  # Already marked — not an error, just a no-op.

        status = AttendanceStatus.PRESENT
        late_cutoff_hour = self._get_late_cutoff_hour()
        if late_cutoff_hour is not None and now.hour >= late_cutoff_hour:
            status = AttendanceStatus.LATE

        record = Attendance(
            student_id=student_id,
            subject_id=subject_id,
            class_id=student.class_id,
            attendance_date=today,
            time_in=now.replace(microsecond=0),
            status=status,
            marked_by=marked_by,
            confidence_score=confidence,
        )

        try:
            db.session.add(record)
            db.session.commit()
        except IntegrityError:
            # Race condition: another request marked it in the split second
            # between our SELECT and INSERT. The UNIQUE constraint saved us.
            db.session.rollback()
            existing = Attendance.query.filter_by(
                student_id=student_id, subject_id=subject_id, attendance_date=today
            ).first()
            return existing, False, None

        self._log(
            "ATTENDANCE_MARKED",
            f"Attendance marked for '{student.name}' ({student.roll_number}) via {marked_by}.",
        )

        # Email notification is intentionally best-effort: attendance must
        # remain successful even if SMTP is unavailable or misconfigured.
        if student.email:
            subject_name = "Attendance"
            subject_code = ""
            if subject_id:
                from models import Subject

                subject = Subject.query.get(subject_id)
                if subject:
                    subject_name = subject.name
                    subject_code = subject.code

            self.email_service.send_attendance_notification(
                to_email=student.email,
                student_name=student.name,
                roll_number=student.roll_number,
                attendance_date=record.attendance_date.isoformat(),
                time_in=record.time_in.strftime("%H:%M:%S"),
                status=record.status,
                subject_name=subject_name,
                subject_code=subject_code,
            )

        logger.info("Attendance marked: student_id=%s subject_id=%s status=%s", student_id, subject_id, status)
        return record, True, None

    def mark_manual(
        self, student_id: int, subject_id: Optional[int], admin_username: str
    ) -> Tuple[Optional[Attendance], bool, Optional[str]]:
        """Manually mark a student present (used from the admin UI as a fallback)."""
        record, created, error = self.mark_attendance(student_id, subject_id, marked_by=MarkedBy.MANUAL)
        if created:
            self._log("ATTENDANCE_MANUAL", f"'{admin_username}' manually marked attendance for student_id={student_id}.")
        return record, created, error

    def get_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        student_id: Optional[int] = None,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
        accessible_class_ids: Optional[List[int]] = None,
    ):
        """
        Paginated, filterable attendance history for the History/Search pages.

        Args:
            accessible_class_ids: If not None, restricts results to these
                ClassRoom IDs — used to enforce a teacher's class restriction.
        """
        stmt = Attendance.query.join(Student)

        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                stmt = stmt.filter(db.false())
            else:
                stmt = stmt.filter(Attendance.class_id.in_(accessible_class_ids))

        if start_date:
            stmt = stmt.filter(Attendance.attendance_date >= start_date)
        if end_date:
            stmt = stmt.filter(Attendance.attendance_date <= end_date)
        if student_id:
            stmt = stmt.filter(Attendance.student_id == student_id)
        if class_id:
            stmt = stmt.filter(Attendance.class_id == class_id)
        if subject_id:
            stmt = stmt.filter(Attendance.subject_id == subject_id)
        if status:
            stmt = stmt.filter(Attendance.status == status)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.filter(db.or_(Student.name.ilike(like), Student.roll_number.ilike(like)))

        stmt = stmt.order_by(Attendance.attendance_date.desc(), Attendance.time_in.desc())
        return stmt.paginate(page=page, per_page=per_page, error_out=False)

    def get_today_summary(self, class_id: Optional[int] = None, accessible_class_ids: Optional[List[int]] = None) -> Dict[str, int]:
        """Quick stats for the dashboard: total students vs present today."""
        today = date.today()

        student_stmt = Student.query.filter_by(is_active=True)
        present_stmt = Attendance.query.filter(Attendance.attendance_date == today)

        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                student_stmt = student_stmt.filter(db.false())
                present_stmt = present_stmt.filter(db.false())
            else:
                student_stmt = student_stmt.filter(Student.class_id.in_(accessible_class_ids))
                present_stmt = present_stmt.filter(Attendance.class_id.in_(accessible_class_ids))

        if class_id:
            student_stmt = student_stmt.filter_by(class_id=class_id)
            present_stmt = present_stmt.filter(Attendance.class_id == class_id)

        total_students = student_stmt.count()
        present_count = present_stmt.distinct(Attendance.student_id).count()

        absent_count = max(total_students - present_count, 0)
        percentage = round((present_count / total_students) * 100, 1) if total_students else 0.0

        return {
            "total_students": total_students,
            "present_today": present_count,
            "absent_today": absent_count,
            "attendance_percentage": percentage,
        }

    def get_weekly_trend(self, days: int = 7, accessible_class_ids: Optional[List[int]] = None) -> List[Dict]:
        from datetime import timedelta

        results = []
        today = date.today()
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            stmt = Attendance.query.filter(Attendance.attendance_date == day)
            if accessible_class_ids is not None:
                if len(accessible_class_ids) == 0:
                    stmt = stmt.filter(db.false())
                else:
                    stmt = stmt.filter(Attendance.class_id.in_(accessible_class_ids))
            count = stmt.distinct(Attendance.student_id).count()
            results.append({"date": day.isoformat(), "count": count})
        return results

    def get_subject_wise_today(self, accessible_class_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Attendance broken down by subject for today — this is the view
        that actually matches how college attendance works: one row per
        lecture/subject, not one blended daily number.
        """
        from models import Subject

        today = date.today()
        stmt = (
            db.session.query(Subject.id, Subject.name, Subject.code, db.func.count(Attendance.id))
            .join(Attendance, Attendance.subject_id == Subject.id)
            .filter(Attendance.attendance_date == today)
        )

        if accessible_class_ids is not None:
            if len(accessible_class_ids) == 0:
                stmt = stmt.filter(db.false())
            else:
                stmt = stmt.filter(Attendance.class_id.in_(accessible_class_ids))

        stmt = stmt.group_by(Subject.id, Subject.name, Subject.code).order_by(Subject.name.asc())

        return [
            {"subject_id": row[0], "name": row[1], "code": row[2], "present_count": row[3]}
            for row in stmt.all()
        ]

    @staticmethod
    def _log(action: str, description: str, level: str = LogLevel.INFO) -> None:
        try:
            db.session.add(SystemLog(actor="system", action=action, description=description, level=level))
            db.session.commit()
        except Exception:  # pragma: no cover
            db.session.rollback()
            logger.exception("Failed to write system log for action=%s", action)
