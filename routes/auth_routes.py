"""
routes/auth_routes.py
======================
Login/logout pages for the server-rendered admin dashboard.
"""

from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from controllers.auth_controller import AuthController
from models import AdminRole
from utils.decorators import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_controller = AuthController()


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Render and process the Admin/Staff login form (superadmin + admin roles only)."""
    if session.get("admin_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("username", "")
        password = request.form.get("password", "")

        success, message = auth_controller.login(identifier, password, allowed_roles=AdminRole.UNRESTRICTED)
        if success:
            flash(message, "success")
            next_url = request.args.get("next") or url_for("dashboard.index")
            return redirect(next_url)

        flash(message, "danger")

    return render_template("auth/login.html")


@auth_bp.route("/teacher-login", methods=["GET", "POST"])
def teacher_login_page():
    """Render and process the Teacher-only login form."""
    if session.get("admin_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("username", "")
        password = request.form.get("password", "")

        success, message = auth_controller.login(identifier, password, allowed_roles=(AdminRole.TEACHER,))
        if success:
            flash(message, "success")
            next_url = request.args.get("next") or url_for("dashboard.index")
            return redirect(next_url)

        flash(message, "danger")

    return render_template("auth/teacher_login.html")


@auth_bp.route("/logout")
def logout():
    """Log the current admin/teacher out and return to the correct login page."""
    login_panel = session.get("login_panel", "admin")
    auth_controller.logout()
    flash("You have been logged out.", "info")
    if login_panel == "teacher":
        return redirect(url_for("auth.teacher_login_page"))
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Let the logged-in admin/teacher change their own password."""
    if request.method == "POST":
        success, message = auth_controller.change_password(
            current_password=request.form.get("current_password", ""),
            new_password=request.form.get("new_password", ""),
            confirm_password=request.form.get("confirm_password", ""),
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html")


@auth_bp.route("/session-ping", methods=["POST"])
def session_ping():
    """
    Lightweight AJAX endpoint hit by the "Extend Session" button and by
    normal background activity. Because SESSION_REFRESH_EACH_REQUEST is
    enabled, simply handling any authenticated request resets the
    5-minute inactivity countdown — this endpoint just gives the
    frontend a cheap, side-effect-free way to do that.
    """
    if not session.get("admin_id"):
        return jsonify(success=False, message="Session already expired."), 401
    return jsonify(success=True)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_page():
    """
    Self-service 'forgot password' request form, shared by both login
    panels. ?panel=teacher or ?panel=admin controls the branding/link-back
    and which login page the emailed reset link ultimately returns to.
    """
    login_panel = request.args.get("panel", "admin")

    if request.method == "POST":
        login_panel = request.form.get("login_panel", "admin")
        identifier = request.form.get("username", "")
        message = auth_controller.request_password_reset(identifier, login_panel=login_panel)
        flash(message, "info")
        return redirect(url_for("auth.teacher_login_page" if login_panel == "teacher" else "auth.login_page"))

    return render_template("auth/forgot_password.html", login_panel=login_panel)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_page(token: str):
    """Set a new password from an emailed reset link."""
    login_panel = request.args.get("panel", "admin")

    if request.method == "POST":
        success, message = auth_controller.reset_password_with_token(
            token=token,
            new_password=request.form.get("new_password", ""),
            confirm_password=request.form.get("confirm_password", ""),
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("auth.teacher_login_page" if login_panel == "teacher" else "auth.login_page"))

    return render_template("auth/reset_password.html", token=token, login_panel=login_panel)
