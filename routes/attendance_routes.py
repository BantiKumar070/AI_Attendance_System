"""
routes/attendance_routes.py
============================
Attendance history browsing, search/filtering, manual marking, and
export to Excel/PDF.
"""

from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for

from controllers.attendance_controller import AttendanceController
from controllers.class_controller import ClassController
from controllers.subject_controller import SubjectController
from utils.decorators import get_session_class_filter, login_required
from utils.helpers import safe_int

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")
attendance_controller = AttendanceController()
class_controller = ClassController()
subject_controller = SubjectController()


@attendance_bp.route("/")
@login_required
def history():
    """Attendance history page with filters (date range, class, subject, status, search)."""
    class_filter = get_session_class_filter()
    pagination = attendance_controller.history(request.args, accessible_class_ids=class_filter)
    classes = class_controller.list_all(accessible_class_ids=class_filter)
    subjects = subject_controller.list_all()
    return render_template(
        "admin/attendance_history.html", pagination=pagination, classes=classes, subjects=subjects, args=request.args
    )


@attendance_bp.route("/mark-manual", methods=["POST"])
@login_required
def mark_manual():
    """Manually mark a student present (fallback for when the camera can't recognize them)."""
    student_id = safe_int(request.form.get("student_id"))
    subject_id = safe_int(request.form.get("subject_id"))

    if not student_id:
        return jsonify(success=False, message="student_id is required."), 400

    class_filter = get_session_class_filter()
    if class_filter is not None:
        from models import Student

        target = Student.query.get(student_id)
        if target is None or target.class_id not in class_filter:
            return jsonify(success=False, message="You do not have permission to mark this student."), 403

    record, created, error = attendance_controller.mark_manual(student_id, subject_id, session.get("username", "admin"))
    if error:
        return jsonify(success=False, message=error), 400

    message = "Attendance marked successfully." if created else "Student was already marked present today."
    return jsonify(success=True, message=message, created=created)


@attendance_bp.route("/export")
@login_required
def export():
    """Export the currently filtered attendance history to Excel or PDF."""
    file_format = request.args.get("format", "xlsx")
    if file_format not in ("xlsx", "pdf"):
        file_format = "xlsx"

    filepath = attendance_controller.export(request.args, file_format=file_format, accessible_class_ids=get_session_class_filter())
    return send_file(filepath, as_attachment=True)
