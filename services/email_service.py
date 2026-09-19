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
from utils.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    """Sends transactional emails (password resets, etc.) when SMTP is configured."""

    def is_configured(self) -> bool:
        """True only if email notifications are enabled AND credentials are present."""
        return bool(
            current_app.config.get("ENABLE_EMAIL_NOTIFICATIONS")
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
