
"""
services/email_service.py
==========================
Thin wrapper around Flask-Mail for the optional "forgot password" email
and any other notifications. Designed to fail gracefully: if email
isn't configured (no MAIL_USERNAME/PASSWORD in .env, or
ENABLE_EMAIL_NOTIFICATIONS is off), every method here simply returns
False instead of raising — callers should fall back to telling the
user to contact their admin.
"""

from __future__ import annotations

from flask import current_app, url_for
from flask_mail import Message

from utils.extensions import mail
from services.settings_service import SettingsService
from utils.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    """Sends transactional emails (password resets, etc.) when SMTP is configured."""

    def is_configured(self) -> bool:
        """True only if email notifications are enabled AND credentials are present."""
        settings_enabled = SettingsService().get("enable_email_notifications", "false") == "true"
        return bool(
            settings_enabled
            and current_app.config.get("ENABLE_EMAIL_NOTIFICATIONS")
            and current_app.config.get("MAIL_USERNAME")
            and current_app.config.get("MAIL_PASSWORD")
        )

    def send_password_reset_email(self, to_email: str, full_name: str, token: str, login_panel: str = "admin") -> bool:
        """
        Email a password-reset link to the given address.

        Returns:
            True if the email was sent, False if email isn't configured
            (the caller should show a "contact your admin" fallback message).
        """
        if not self.is_configured():
            logger.warning("Password reset requested for %s but email is not configured.", to_email)
            return False

        reset_url = url_for("auth.reset_password_page", token=token, panel=login_panel, _external=True)

        try:
            message = Message(
                subject="Reset your Attendance System password",
                recipients=[to_email],
                body=(
                    f"Hi {full_name},\n\n"
                    f"We received a request to reset your password. This link is valid for 30 minutes:\n\n"
                    f"{reset_url}\n\n"
                    f"If you didn't request this, you can safely ignore this email.\n"
                ),
            )
            mail.send(message)
            return True
        except Exception:  # pragma: no cover - network/SMTP errors shouldn't crash the request
            logger.exception("Failed to send password reset email to %s", to_email)
            return False
    def send_attendance_notification(
        self,
        to_email: str,
        student_name: str,
        roll_number: str,
        attendance_date: str,
        time_in: str,
        status: str,
        subject_name: str = "Attendance",
        subject_code: str = "",
    ) -> bool:
        """Send a confirmation email after attendance is successfully marked."""
        if not to_email or not self.is_configured():
            logger.warning(
                "Attendance email skipped for %s: email is not configured or student has no email.",
                roll_number,
            )
            return False

        status_label = status.replace("_", " ").title()
        subject_label = f"{subject_name} ({subject_code})" if subject_code else subject_name

        try:
            message = Message(
                subject=f"Attendance Marked - {subject_label}",
                recipients=[to_email],
                body=(
                    f"Hi {student_name},\n\n"
                    f"Your attendance has been recorded successfully.\n\n"
                    f"Student: {student_name}\n"
                    f"Roll Number: {roll_number}\n"
                    f"Subject: {subject_label}\n"
                    f"Date: {attendance_date}\n"
                    f"Time: {time_in}\n"
                    f"Status: {status_label}\n\n"
                    f"This is an automated message from the AI-Powered Automatic Attendance System.\n"
                ),
            )
            mail.send(message)
            logger.info("Attendance email sent to %s for student %s.", to_email, roll_number)
            return True
        except Exception:
            logger.exception("Failed to send attendance email to %s", to_email)
            return False

