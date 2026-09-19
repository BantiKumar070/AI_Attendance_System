"""
routes/teacher_routes.py
=========================
Superadmin-only pages for creating teacher accounts and assigning them
to one or more subjects (each subject already implies its class/department).
Teachers themselves cannot access these routes.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from controllers.subject_controller import SubjectController
from controllers.teacher_controller import TeacherController
from utils.decorators import superadmin_required

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teachers")
teacher_controller = TeacherController()
subject_controller = SubjectController()


def _group_subjects_by_class():
    """
    Group every subject by its class (labeled with department) for the
    assignment checkboxes UI, e.g.:
        "B.Tech — Computer Science (Section A)" -> [Math, Physics, ...]
        "BCA — Computer Applications"           -> [Math, DBMS, ...]
    """
    subjects = subject_controller.list_all()
    groups = {}
    for subject in subjects:
        label = subject.class_room.display_name() if subject.class_room else "Unassigned to a class"
        groups.setdefault(label, []).append(subject)
    return [{"label": label, "subjects": subs} for label, subs in sorted(groups.items())]


@teacher_bp.route("/")
@superadmin_required
def list_teachers():
    """List every teacher account with the subjects they've been assigned."""
    teachers = teacher_controller.list_teachers()
    return render_template("admin/manage_teachers.html", teachers=teachers, subjects_by_class=_group_subjects_by_class())


@teacher_bp.route("/create", methods=["POST"])
@superadmin_required
def create():
    """Create a new teacher account and assign it to one or more subjects."""
    _, error = teacher_controller.create_teacher(request.form)
    flash(error if error else "Teacher account created successfully.", "danger" if error else "success")
    return redirect(url_for("teacher.list_teachers"))


@teacher_bp.route("/<int:admin_id>/assign", methods=["POST"])
@superadmin_required
def assign(admin_id: int):
    """Update which subjects a teacher is assigned to teach."""
    _, error = teacher_controller.update_assignments(admin_id, request.form)
    flash(error if error else "Subject assignments updated.", "danger" if error else "success")
    return redirect(url_for("teacher.list_teachers"))


@teacher_bp.route("/<int:admin_id>/deactivate", methods=["POST"])
@superadmin_required
def deactivate(admin_id: int):
    """Deactivate a teacher account (soft-disable, does not delete history)."""
    _, error = teacher_controller.deactivate(admin_id)
    flash(error if error else "Teacher account deactivated.", "danger" if error else "info")
    return redirect(url_for("teacher.list_teachers"))


@teacher_bp.route("/<int:admin_id>/unlock", methods=["POST"])
@superadmin_required
def unlock(admin_id: int):
    """Immediately clear a login lockout for this teacher (before the 24h expires)."""
    _, error = teacher_controller.unlock(admin_id)
    flash(error if error else "Account unlocked successfully.", "danger" if error else "success")
    return redirect(url_for("teacher.list_teachers"))


@teacher_bp.route("/<int:admin_id>/reset-password", methods=["POST"])
@superadmin_required
def reset_password(admin_id: int):
    """
    Directly set a new password for a teacher who forgot theirs — no
    email required. Share the new password with them out of band.
    """
    success, error = teacher_controller.reset_password(admin_id, request.form)
    flash(error if error else "Password reset successfully. Share the new password with the teacher.", "danger" if error else "success")
    return redirect(url_for("teacher.list_teachers"))
