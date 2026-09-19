"""
routes/api_routes.py
=====================
Pure JSON REST API, protected by JWT bearer tokens (see
utils/decorators.token_required). Intended for external integrations
or a future mobile app, separate from the server-rendered dashboard.

Base path: /api/v1  (set via url_prefix in app.py's register_blueprint)
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from controllers.attendance_controller import AttendanceController
from controllers.auth_controller import AuthController
from controllers.student_controller import StudentController
from utils.decorators import token_required
from utils.helpers import safe_int

api_bp = Blueprint("api", __name__)

auth_controller = AuthController()
student_controller = StudentController()
attendance_controller = AttendanceController()


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    """POST {username, password} -> {token} JWT for use in Authorization: Bearer <token>."""
    payload = request.get_json(silent=True) or {}
    token, error = auth_controller.login_for_api(payload.get("username", ""), payload.get("password", ""))
    if error:
        return jsonify(success=False, message=error), 401
    return jsonify(success=True, token=token)


@api_bp.route("/students", methods=["GET"])
@token_required
def api_list_students():
    """GET /api/v1/students?q=&class_id=&page=&per_page= -> paginated student list."""
    pagination = student_controller.list_students(request.args)
    return jsonify(
        success=True,
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
        items=[s.to_dict() for s in pagination.items],
    )


@api_bp.route("/students/<int:student_id>", methods=["GET"])
@token_required
def api_get_student(student_id: int):
    """GET /api/v1/students/<id> -> a single student's details."""
    student = student_controller.student_service.get_by_id(student_id)
    if student is None:
        return jsonify(success=False, message="Student not found."), 404
    return jsonify(success=True, item=student.to_dict())


@api_bp.route("/students", methods=["POST"])
@token_required
def api_create_student():
    """POST /api/v1/students -> create a student from JSON body."""
    payload = request.get_json(silent=True) or {}
    student, error = student_controller.student_service.create_student(
        roll_number=payload.get("roll_number", ""),
        name=payload.get("name", ""),
        email=payload.get("email"),
        phone=payload.get("phone"),
        gender=payload.get("gender"),
        class_id=safe_int(payload.get("class_id")),
    )
    if error:
        return jsonify(success=False, message=error), 400
    return jsonify(success=True, item=student.to_dict()), 201


@api_bp.route("/attendance", methods=["GET"])
@token_required
def api_attendance_history():
    """GET /api/v1/attendance?start_date=&end_date=&student_id=&... -> paginated history."""
    pagination = attendance_controller.history(request.args)
    return jsonify(
        success=True,
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
        items=[a.to_dict() for a in pagination.items],
    )


@api_bp.route("/attendance/mark", methods=["POST"])
@token_required
def api_mark_attendance():
    """POST {student_id, subject_id?} -> mark attendance via the API (e.g. from a kiosk device)."""
    payload = request.get_json(silent=True) or {}
    student_id = safe_int(payload.get("student_id"))
    subject_id = safe_int(payload.get("subject_id"))

    if not student_id:
        return jsonify(success=False, message="student_id is required."), 400

    record, created, error = attendance_controller.attendance_service.mark_attendance(student_id, subject_id)
    if error:
        return jsonify(success=False, message=error), 400
    return jsonify(success=True, created=created, item=record.to_dict() if record else None)


@api_bp.route("/health", methods=["GET"])
def api_health():
    """Simple unauthenticated health-check endpoint for uptime monitoring."""
    return jsonify(success=True, message="Attendance System API is running.")
