"""
routes/subject_routes.py
=========================
Subject/course management pages (create, edit, delete, list).
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from controllers.class_controller import ClassController
from controllers.subject_controller import SubjectController
from utils.decorators import get_session_subject_filter, login_required, roles_required

subject_bp = Blueprint("subject", __name__, url_prefix="/subjects")
subject_controller = SubjectController()
class_controller = ClassController()


@subject_bp.route("/")
@login_required
def list_subjects():
    """List all subjects with quick create/edit/delete actions (filtered to a teacher's own subjects)."""
    subjects = subject_controller.list_all()
    subject_filter = get_session_subject_filter()
    if subject_filter is not None:
        subjects = [s for s in subjects if s.id in subject_filter]
    classes = class_controller.list_all()
    return render_template("admin/subjects.html", subjects=subjects, classes=classes)


@subject_bp.route("/create", methods=["POST"])
@roles_required("admin", "superadmin")
def create():
    """Create a new subject from the modal form on the subjects page."""
    _, error = subject_controller.create(request.form)
    flash(error if error else "Subject created successfully.", "danger" if error else "success")
    return redirect(url_for("subject.list_subjects"))


@subject_bp.route("/<int:subject_id>/update", methods=["POST"])
@roles_required("admin", "superadmin")
def update(subject_id: int):
    """Update an existing subject."""
    _, error = subject_controller.update(subject_id, request.form)
    flash(error if error else "Subject updated successfully.", "danger" if error else "success")
    return redirect(url_for("subject.list_subjects"))


@subject_bp.route("/<int:subject_id>/delete", methods=["POST"])
@roles_required("admin", "superadmin")
def delete(subject_id: int):
    """Delete a subject."""
    _, error = subject_controller.delete(subject_id)
    flash(error if error else "Subject deleted.", "danger" if error else "info")
    return redirect(url_for("subject.list_subjects"))
