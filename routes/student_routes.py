"""
routes/student_routes.py
=========================
Student management pages: list/search, registration, the webcam
capture wizard, encoding generation, edit, and delete.
"""

from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from controllers.class_controller import ClassController
from controllers.student_controller import StudentController
from utils.decorators import get_session_class_filter, login_required

student_bp = Blueprint("student", __name__, url_prefix="/students")
student_controller = StudentController()
class_controller = ClassController()


@student_bp.route("/")
@login_required
def list_students():
    """Searchable, paginated student directory."""
    class_filter = get_session_class_filter()
    pagination = student_controller.list_students(request.args, accessible_class_ids=class_filter)
    classes = class_controller.list_all(accessible_class_ids=class_filter)
    return render_template("admin/students_list.html", pagination=pagination, classes=classes)


@student_bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    """Step 1: register the student's basic details (before face capture)."""
    if request.method == "POST":
        student, error = student_controller.register(request.form)
        if error:
            flash(error, "danger")
            return redirect(url_for("student.register"))

        flash(f"Student '{student.name}' registered. Now capture their face images.", "success")
        return redirect(url_for("student.capture", student_id=student.id))

    classes = class_controller.list_all(accessible_class_ids=get_session_class_filter())
    return render_template("admin/student_form.html", classes=classes, student=None)


@student_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit(student_id: int):
    """Edit an existing student's details."""
    student = student_controller.student_service.get_by_id(student_id)
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("student.list_students"))

    if request.method == "POST":
        _, error = student_controller.update(student_id, request.form)
        if error:
            flash(error, "danger")
        else:
            flash("Student updated successfully.", "success")
            return redirect(url_for("student.list_students"))

    classes = class_controller.list_all(accessible_class_ids=get_session_class_filter())
    return render_template("admin/student_form.html", classes=classes, student=student)


@student_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def delete(student_id: int):
    """Delete a student and all associated encodings/attendance history."""
    success, error = student_controller.delete(student_id)
    flash(error if error else "Student deleted.", "danger" if error else "info")
    return redirect(url_for("student.list_students"))


@student_bp.route("/<int:student_id>/capture", methods=["GET"])
@login_required
def capture(student_id: int):
    """Step 2: webcam capture wizard page (captures FACE_DATASET_SAMPLES images)."""
    student = student_controller.student_service.get_by_id(student_id)
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("student.list_students"))
    progress = student_controller.capture_progress(student_id)
    return render_template("admin/student_capture.html", student=student, progress=progress)


@student_bp.route("/<int:student_id>/capture/frame", methods=["POST"])
@login_required
def capture_frame(student_id: int):
    """AJAX endpoint: receive one webcam frame (base64) and save it to the dataset."""
    image_base64 = request.json.get("image") if request.is_json else None
    if not image_base64:
        return jsonify(success=False, message="No image data received."), 400

    count, error = student_controller.capture_frame(student_id, image_base64)
    if error and count is None:
        return jsonify(success=False, message=error), 404

    return jsonify(success=error is None, count=count, message=error)


@student_bp.route("/<int:student_id>/encode", methods=["POST"])
@login_required
def generate_encodings(student_id: int):
    """Step 3: process captured images into face encodings and store them."""
    count, error = student_controller.generate_encodings(student_id)
    if error:
        return jsonify(success=False, message=error), 400
    return jsonify(success=True, message=f"{count} face encodings generated successfully.", count=count)
