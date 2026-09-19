"""
routes/settings_routes.py
==========================
Admin Settings panel: recognition tuning, cooldown, notification toggles.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from controllers.settings_controller import SettingsController
from utils.decorators import roles_required

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")
settings_controller = SettingsController()


@settings_bp.route("/", methods=["GET", "POST"])
@roles_required("admin", "superadmin")
def index():
    """View and update system settings."""
    if request.method == "POST":
        settings_controller.update(request.form)
        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings.index"))

    settings = settings_controller.get_all()
    return render_template("admin/settings.html", settings=settings)
