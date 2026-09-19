"""
services/auth_service.py
=========================
Business logic for admin authentication: login verification, admin
creation, and JWT issuance for the REST API.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from models import Admin, AdminRole, Subject, SystemLog, LogLevel
from utils.extensions import db
from utils.jwt_utils import decode_token, generate_token
from utils.logger import get_logger
from utils.validators import is_strong_password, is_valid_email

logger = get_logger(__name__)


class AuthService:
    """Encapsulates all admin-authentication related operations."""

    def authenticate(
        self, username_or_email: str, password: str, allowed_roles: Optional[Tuple[str, ...]] = None
    ) -> Tuple[Optional[Admin], Optional[str]]:
        """
        Verify admin credentials.

        Args:
            allowed_roles: If given, restricts login to accounts whose role
                is in this set — used so the Teacher login panel only
                accepts teacher accounts, and the Admin panel only accepts
                admin/superadmin accounts, even with a correct password.

        Returns:
            (Admin, None) on success, (None, error_message) on failure.
        """
        identifier = (username_or_email or "").strip()
        if not identifier or not password:
            return None, "Username/email and password are required."

        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.email == identifier)
        ).first()

        if admin is None:
            self._log(None, "LOGIN_FAILED", f"Failed login attempt for unknown user '{identifier}'", LogLevel.WARNING)
            return None, "Invalid username or password."

        if admin.is_locked():
            remaining = admin.locked_until - datetime.utcnow()
            hours_left = max(int(remaining.total_seconds() // 3600) + 1, 1)
            self._log(admin.username, "LOGIN_BLOCKED", "Login attempt on a locked account.", LogLevel.WARNING)
            return None, (
                f"This account is locked due to too many failed login attempts. "
                f"Try again in about {hours_left} hour(s), or ask a super admin to unlock it."
            )

        if not admin.check_password(password):
            just_locked = admin.register_failed_attempt()
            db.session.commit()
            if just_locked:
                self._log(
                    admin.username, "ACCOUNT_LOCKED",
                    f"'{admin.username}' locked for {24} hours after 3 failed login attempts.", LogLevel.ERROR,
                )
                return None, "Too many failed attempts. This account is now locked for 24 hours."

            self._log(admin.username, "LOGIN_FAILED", f"Failed login attempt for '{identifier}'", LogLevel.WARNING)
            return None, "Invalid username or password."

        if not admin.is_active:
            return None, "This account has been deactivated. Contact the super admin."

        if allowed_roles is not None and admin.role not in allowed_roles:
            self._log(
                admin.username, "LOGIN_WRONG_PANEL",
                f"'{admin.username}' ({admin.role}) tried logging in on the wrong login panel.", LogLevel.INFO,
            )
            if admin.role == AdminRole.TEACHER:
                return None, "This is a teacher account. Please use the Teacher Login page instead."
            return None, "This is an admin/staff account. Please use the Admin Login page instead."

        admin.reset_lockout()
        admin.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
        self._log(admin.username, "LOGIN_SUCCESS", f"Admin '{admin.username}' logged in.", LogLevel.SUCCESS)
        return admin, None

    def issue_jwt(self, admin: Admin) -> str:
        """Issue a signed JWT for the given admin (used by the REST API)."""
        return generate_token({"admin_id": admin.id, "username": admin.username, "role": admin.role})

    def create_admin(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str,
        role: str = AdminRole.ADMIN,
        subject_ids: Optional[List[int]] = None,
    ) -> Tuple[Optional[Admin], Optional[str]]:
        """
        Create a new admin/teacher account with validation.

        Args:
            role: One of AdminRole.SUPERADMIN / ADMIN / TEACHER.
            subject_ids: Only meaningful when role == 'teacher' — the
                list of Subject IDs this teacher should be allowed to
                teach/take attendance for. Each subject already carries
                its own class, so this also determines which class(es)
                and department(s) the teacher can see.

        Returns:
            (Admin, None) on success, (None, error_message) on failure.
        """
        username = (username or "").strip()
        email = (email or "").strip()
        full_name = (full_name or "").strip()

        if not username or not email or not full_name:
            return None, "Username, email, and full name are all required."
        if not is_valid_email(email):
            return None, "Invalid email address."
        if not is_strong_password(password):
            return None, "Password must be at least 8 characters and include a letter and a number."
        if role not in AdminRole.ALL:
            return None, "Invalid role."
        if Admin.query.filter_by(username=username).first():
            return None, f"Username '{username}' is already taken."
        if Admin.query.filter_by(email=email).first():
            return None, f"Email '{email}' is already registered."

        admin = Admin(username=username, email=email, full_name=full_name, role=role)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        if role == AdminRole.TEACHER and subject_ids:
            self.assign_subjects(admin.id, subject_ids)

        self._log("system", "ADMIN_CREATED", f"{role.title()} account '{username}' created.", LogLevel.INFO)
        logger.info("New %s account created: %s", role, username)
        return admin, None

    def assign_subjects(self, admin_id: int, subject_ids: List[int]) -> Tuple[bool, Optional[str]]:
        """Replace a teacher's assigned subjects with the given list of Subject IDs."""
        admin = Admin.query.get(admin_id)
        if admin is None:
            return False, "Admin not found."

        subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
        admin.assigned_subjects = subjects
        db.session.commit()

        self._log("system", "TEACHER_SUBJECTS_ASSIGNED", f"'{admin.username}' assigned to {len(subjects)} subject(s).")
        return True, None

    @staticmethod
    def get_accessible_class_ids(admin: Admin) -> Optional[List[int]]:
        """
        Return the list of ClassRoom IDs the given admin may view/manage.

        Returns:
            None  -> unrestricted (admin/superadmin — sees every class)
            [...] -> restricted to exactly these class IDs (teacher, derived
                     from the classes their assigned subjects belong to)
        """
        if admin is None or admin.can_access_all_classes():
            return None
        return admin.assigned_class_ids()

    @staticmethod
    def get_accessible_subject_ids(admin: Admin) -> Optional[List[int]]:
        """
        Return the list of Subject IDs the given admin may take attendance
        for / view.

        Returns:
            None  -> unrestricted (admin/superadmin — sees every subject)
            [...] -> restricted to exactly these subject IDs (teacher)
        """
        if admin is None or admin.can_access_all_classes():
            return None
        return admin.assigned_subject_ids()

    def list_teachers(self):
        """Return all teacher-role accounts, most recently created first."""
        return Admin.query.filter_by(role=AdminRole.TEACHER).order_by(Admin.created_at.desc()).all()

    def deactivate_admin(self, admin_id: int) -> Tuple[bool, Optional[str]]:
        """Deactivate (soft-disable) an admin/teacher account without deleting it."""
        admin = Admin.query.get(admin_id)
        if admin is None:
            return False, "Admin not found."
        admin.is_active = False
        db.session.commit()
        self._log("system", "ADMIN_DEACTIVATED", f"Account '{admin.username}' deactivated.", LogLevel.WARNING)
        return True, None

    def unlock_admin(self, admin_id: int) -> Tuple[bool, Optional[str]]:
        """Superadmin action: immediately clear a lockout, before the 24h expires on its own."""
        admin = Admin.query.get(admin_id)
        if admin is None:
            return False, "Admin not found."
        admin.reset_lockout()
        db.session.commit()
        self._log("system", "ACCOUNT_UNLOCKED", f"Account '{admin.username}' unlocked by a super admin.", LogLevel.INFO)
        return True, None

    def reset_password_direct(self, admin_id: int, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Superadmin action: set a brand-new password for another account
        with NO knowledge of the old one — this is how a teacher who
        forgot their password gets back in (they ask their super admin,
        who resets it here and shares the new password with them).
        """
        admin = Admin.query.get(admin_id)
        if admin is None:
            return False, "Admin not found."
        if not is_strong_password(new_password):
            return False, "New password must be at least 8 characters and include a letter and a number."

        admin.set_password(new_password)
        admin.reset_lockout()
        db.session.commit()
        self._log("system", "PASSWORD_RESET_BY_ADMIN", f"Password for '{admin.username}' was reset by a super admin.", LogLevel.WARNING)
        return True, None

    def generate_password_reset_token(self, identifier: str) -> Optional[str]:
        """
        Self-service "forgot password" step 1: look up the account by
        username/email and issue a short-lived signed token for it.

        Returns None if no matching account exists — callers should show
        the same generic "check your email" message either way, so this
        can't be used to discover which usernames/emails are registered.
        """
        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.email == identifier)
        ).first()
        if admin is None or not admin.is_active:
            return None

        token = generate_token(
            {"admin_id": admin.id, "purpose": "password_reset"}, expires_delta=timedelta(minutes=30)
        )
        self._log(admin.username, "PASSWORD_RESET_REQUESTED", "A password reset link was requested.", LogLevel.INFO)
        return token

    def reset_password_with_token(self, token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Self-service "forgot password" step 2: verify the token and set the new password."""
        payload, error = decode_token(token)
        if error:
            return False, "This reset link is invalid or has expired. Please request a new one."
        if payload.get("purpose") != "password_reset":
            return False, "This reset link is invalid."

        admin = Admin.query.get(payload.get("admin_id"))
        if admin is None:
            return False, "Account not found."
        if not is_strong_password(new_password):
            return False, "New password must be at least 8 characters and include a letter and a number."

        admin.set_password(new_password)
        admin.reset_lockout()
        db.session.commit()
        self._log(admin.username, "PASSWORD_RESET_SELF_SERVICE", "Password reset via emailed link.", LogLevel.INFO)
        return True, None

    def change_password(self, admin: Admin, current_password: str, new_password: str) -> Optional[str]:
        """Change an admin's password after verifying the current one. Returns error message or None."""
        if not admin.check_password(current_password):
            return "Current password is incorrect."
        if not is_strong_password(new_password):
            return "New password must be at least 8 characters and include a letter and a number."

        admin.set_password(new_password)
        db.session.commit()
        self._log(admin.username, "PASSWORD_CHANGED", "Admin changed their password.", LogLevel.INFO)
        return None

    @staticmethod
    def _log(actor: Optional[str], action: str, description: str, level: str) -> None:
        """Persist an entry to the system_logs table (best-effort, never raises)."""
        try:
            db.session.add(SystemLog(actor=actor or "system", action=action, description=description, level=level))
            db.session.commit()
        except Exception:  # pragma: no cover - logging must never break auth
            db.session.rollback()
            logger.exception("Failed to write system log for action=%s", action)
