"""
routes/class_routes.py
=======================
Class/batch management pages (create, edit, delete, list).
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from controllers.class_controller import ClassController
from utils.decorators import get_session_class_filter, login_required, roles_required

class_bp = Blueprint("class_room", __name__, url_prefix="/classes")
class_controller = ClassController()


@class_bp.route("/")
@login_required
def list_classes():
    """List all classes with quick create/edit/delete actions (admin/superadmin only)."""
    classes = class_controller.list_all(accessible_class_ids=get_session_class_filter())
    return render_template("admin/classes.html", classes=classes)


@class_bp.route("/create", methods=["POST"])
@roles_required("admin", "superadmin")
def create():
    """Create a new class from the modal form on the classes page."""
    _, error = class_controller.create(request.form)
    flash(error if error else "Class created successfully.", "danger" if error else "success")
    return redirect(url_for("class_room.list_classes"))


@class_bp.route("/<int:class_id>/update", methods=["POST"])
@roles_required("admin", "superadmin")
def update(class_id: int):
    """Update an existing class."""
    _, error = class_controller.update(class_id, request.form)
    flash(error if error else "Class updated successfully.", "danger" if error else "success")
    return redirect(url_for("class_room.list_classes"))


@class_bp.route("/<int:class_id>/delete", methods=["POST"])
@roles_required("admin", "superadmin")
def delete(class_id: int):
    """Delete a class (only allowed if it has no students assigned)."""
    _, error = class_controller.delete(class_id)
    flash(error if error else "Class deleted.", "danger" if error else "info")
    return redirect(url_for("class_room.list_classes"))
