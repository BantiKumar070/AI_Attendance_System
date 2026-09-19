"""
models/admin.py
================
Represents an administrative / staff user who can log into the dashboard,
register students, and manage the system.

Passwords are never stored in plain text — only a bcrypt hash is
persisted, and the model exposes ``set_password`` / ``check_password``
helpers so the rest of the codebase never touches raw hashes directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.orm import Mapped

from models.base import SerializerMixin, TimestampMixin
from utils.extensions import db

# Lockout policy: after this many consecutive failed logins, the account
# is locked for LOCKOUT_DURATION_HOURS. Only a superadmin can unlock it
# early (see AuthService.unlock_admin).
MAX_FAILED_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION_HOURS = 24

# Many-to-many join table: which SUBJECTS a teacher-role Admin teaches.
# A subject already belongs to exactly one class (Subject.class_id), so
# assigning a teacher to a subject automatically scopes both "what they
# teach" and "which class/department it's for" — this is what lets the
# same teacher (e.g. teaching Math to both B.Tech and BCA) hold two
# separate subject assignments that resolve to two separate classes.
# Superadmins/admins ignore this table entirely (they see everything);
# it only restricts role='teacher' accounts.
teacher_subject_assignments = db.Table(
    "teacher_subject_assignments",
    db.Column("admin_id", db.Integer, db.ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
)


class AdminRole:
    """Valid roles for an Admin account."""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEACHER = "teacher"

    ALL = (SUPERADMIN, ADMIN, TEACHER)
    # Roles that can see/manage every class (no restriction applied).
    UNRESTRICTED = (SUPERADMIN, ADMIN)


class Admin(db.Model, TimestampMixin, SerializerMixin):
    """Administrator / Teacher account used to access the protected dashboard."""

    __tablename__ = "admins"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=AdminRole.ADMIN)  # superadmin | admin | teacher
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # --- Account lockout (brute-force protection) ---
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    # --- Relationships ---
    # Only meaningful when role == 'teacher'. Superadmins/admins are
    # unrestricted regardless of what (if anything) is in this list.
    assigned_subjects = db.relationship(
        "Subject", secondary=teacher_subject_assignments, backref="teachers"
    )

    def assigned_subject_ids(self) -> list:
        """Return the list of Subject IDs this teacher is assigned to teach."""
        return [s.id for s in self.assigned_subjects]

    def assigned_class_ids(self) -> list:
        """
        Return the distinct list of ClassRoom IDs this teacher has access
        to, derived from the classes their assigned subjects belong to.
        (A subject with no class_id — a cross-class elective — grants no
        class access on its own.)
        """
        return sorted({s.class_id for s in self.assigned_subjects if s.class_id is not None})

    def can_access_all_classes(self) -> bool:
        """True for admin/superadmin roles, which are never restricted by class."""
        return self.role in AdminRole.UNRESTRICTED

    def is_locked(self) -> bool:
        """True if this account is currently locked out due to failed login attempts."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def register_failed_attempt(self) -> bool:
        """
        Record one failed login attempt. If this pushes the account over
        MAX_FAILED_LOGIN_ATTEMPTS, lock it for LOCKOUT_DURATION_HOURS.

        Returns:
            True if this attempt triggered a new lockout, False otherwise.
        """
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            self.locked_until = datetime.utcnow() + timedelta(hours=LOCKOUT_DURATION_HOURS)
            self.failed_login_attempts = 0
            return True
        return False

    def reset_lockout(self) -> None:
        """Clear any failed-attempt count and lockout (called on successful login or admin unlock)."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def set_password(self, raw_password: str) -> None:
        """Hash and store the given plain-text password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """Verify a plain-text password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(raw_password.encode("utf-8"), self.password_hash.encode("utf-8"))
        except (ValueError, AttributeError):
            return False

    def to_dict(self, exclude: tuple = ("password_hash",)) -> dict:
        """Serialize, always excluding the password hash by default."""
        return super().to_dict(exclude=exclude)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Admin id={self.id} username={self.username!r} role={self.role!r}>"
