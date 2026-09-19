"""
controllers/auth_controller.py
===============================
Translates HTTP requests for login/logout/JWT into AuthService calls
and shapes the responses (session cookie for the dashboard, JSON+JWT
for the API).
"""

from __future__ import annotations

from flask import session

from services.auth_service import AuthService


class AuthController:
    """Coordinates login/logout flows for both session and JWT auth."""

    def __init__(self) -> None:
        self.auth_service = AuthService()

    def login(self, identifier: str, password: str, allowed_roles=None) -> tuple[bool, str]:
        """
        Attempt a session-based login (used by the HTML dashboard).

        Args:
            allowed_roles: Optional tuple restricting which account roles
                may log in via this call — used to keep the Admin and
                Teacher login panels separate.

        Returns:
            (success, message)
        """
        admin, error = self.auth_service.authenticate(identifier, password, allowed_roles=allowed_roles)
        if error:
            return False, error

        session.permanent = True
        session["admin_id"] = admin.id
        session["username"] = admin.username
        session["full_name"] = admin.full_name
        session["role"] = admin.role
        session["login_panel"] = "teacher" if admin.role == "teacher" else "admin"
        # None = unrestricted (admin/superadmin); a list = teacher's scope.
        session["accessible_class_ids"] = self.auth_service.get_accessible_class_ids(admin)
        session["accessible_subject_ids"] = self.auth_service.get_accessible_subject_ids(admin)
        return True, "Login successful."

    def login_for_api(self, identifier: str, password: str):
        """
        Attempt a JWT-based login (used by the REST API).

        Returns:
            (token | None, error_message | None)
        """
        admin, error = self.auth_service.authenticate(identifier, password)
        if error:
            return None, error
        return self.auth_service.issue_jwt(admin), None

    def logout(self) -> None:
        """Clear the current session."""
        session.clear()

    def change_password(self, current_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
        """
        Change the currently logged-in admin's password.

        Returns:
            (success, message)
        """
        from models import Admin

        if new_password != confirm_password:
            return False, "New password and confirmation do not match."

        admin_id = session.get("admin_id")
        admin = Admin.query.get(admin_id) if admin_id else None
        if admin is None:
            return False, "Session expired. Please log in again."

        error = self.auth_service.change_password(admin, current_password, new_password)
        if error:
            return False, error
        return True, "Password changed successfully."

    def request_password_reset(self, identifier: str, login_panel: str = "admin") -> str:
        """
        Handle a "forgot password" request. Always returns the same
        generic message regardless of whether the account exists, so
        this can't be used to enumerate valid usernames/emails.
        """
        from models import Admin
        from services.email_service import EmailService

        generic_message = (
            "If an account matches that username/email, a password reset link has been sent to it. "
            "The link expires in 30 minutes."
        )

        token = self.auth_service.generate_password_reset_token(identifier)
        if not token:
            return generic_message

        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.email == identifier)
        ).first()
        if admin is None:
            return generic_message

        email_service = EmailService()
        sent = email_service.send_password_reset_email(admin.email, admin.full_name, token, login_panel)
        if not sent:
            return (
                "Email isn't configured on this server, so we can't send a reset link automatically. "
                "Please contact your super admin to have your password reset directly."
            )
        return generic_message

    def reset_password_with_token(self, token: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
        """Complete a self-service password reset from the emailed link."""
        if new_password != confirm_password:
            return False, "New password and confirmation do not match."

        success, error = self.auth_service.reset_password_with_token(token, new_password)
        if not success:
            return False, error
        return True, "Password reset successfully. You can now log in."
