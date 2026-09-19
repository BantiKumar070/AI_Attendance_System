"""
routes/face_routes.py
======================
The live "Take Attendance" page: streams webcam frames from the
browser to the server, which recognizes faces and automatically marks
attendance in real time.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from controllers.face_controller import FaceController
from controllers.subject_controller import SubjectController
from utils.decorators import get_session_subject_filter, login_required
from utils.helpers import safe_int

face_bp = Blueprint("face", __name__, url_prefix="/recognition")
face_controller = FaceController()
subject_controller = SubjectController()


@face_bp.route("/live")
@login_required
def live():
    """Render the live face-recognition / automatic-attendance page."""
    subject_filter = get_session_subject_filter()
    subjects = subject_controller.list_all(active_only=True)
    if subject_filter is not None:
        subjects = [s for s in subjects if s.id in subject_filter]
    return render_template("admin/live_recognition.html", subjects=subjects)


@face_bp.route("/process-frame", methods=["POST"])
@login_required
def process_frame():
    """
    AJAX endpoint called repeatedly (every ~1s) by the live-recognition
    page. Accepts one webcam frame, returns recognized faces + their
    bounding boxes + attendance-marking status for on-screen overlay.

    A subject_id is required: every attendance mark must be tied to a
    specific lecture/subject, matching how attendance is actually taken
    in a college (per-subject, per-lecture) rather than one generic
    daily mark.
    """
    payload = request.get_json(silent=True) or {}
    image_base64 = payload.get("image")
    subject_id = safe_int(payload.get("subject_id"))

    if not image_base64:
        return jsonify(success=False, message="No image data received."), 400
    if not subject_id:
        return jsonify(success=False, message="A subject must be selected before taking attendance."), 400

    subject_filter = get_session_subject_filter()
    if subject_filter is not None and subject_id not in subject_filter:
        return jsonify(success=False, message="You are not assigned to teach this subject."), 403

    results = face_controller.recognize_and_mark(image_base64, subject_id=subject_id)
    return jsonify(success=True, faces=results)
