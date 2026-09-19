"""
app.py
======
Application entry point for the AI-Powered Automatic Attendance System.

Uses the Flask "Application Factory" pattern (``create_app``) so the app
can be instantiated multiple times with different configs — once for
running the dev server, once for gunicorn/waitress in production, and
once per test-suite run with an in-memory database.

Run locally with:
    python app.py

Run in production with:
    gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException

# Load variables from a local .env file (if present) before anything else
# reads os.environ — lets `config.py` pick up DATABASE_URL, SECRET_KEY, etc.
load_dotenv()

from config import get_config
from utils.extensions import db, mail, migrate
from utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


def create_app(config_object=None) -> Flask:
    """
    Application factory.

    Args:
        config_object: Optional explicit config class (mainly used by
                        tests). Falls back to ``get_config()`` which
                        inspects the ``APP_ENV`` environment variable.

    Returns:
        A fully configured Flask application instance.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ---------------- Configuration ----------------
    cfg = config_object or get_config()
    app.config.from_object(cfg)
    cfg.init_app(app)  # ensures uploads/dataset/trainer/... folders exist

    # ---------------- Logging ----------------
    configure_logging(app.config["LOGS_FOLDER"], debug=app.config.get("DEBUG", False))
    logger.info("Starting %s in '%s' mode", app.config["APP_NAME"], os.environ.get("APP_ENV", "development"))

    # ---------------- Extensions ----------------
    db.init_app(app)
    migrate.init_app(app, db)
    if app.config.get("ENABLE_EMAIL_NOTIFICATIONS"):
        mail.init_app(app)

    # ---------------- Blueprints ----------------
    _register_blueprints(app)

    # ---------------- Error Handlers ----------------
    _register_error_handlers(app)

    # ---------------- CLI Commands ----------------
    _register_cli_commands(app)

    # ---------------- Database bootstrap ----------------
    with app.app_context():
        # Import models so their tables are registered on db.metadata
        import models  # noqa: F401

        db.create_all()
        _seed_default_admin(app)

    logger.info("Application initialized successfully.")
    return app


def _register_blueprints(app: Flask) -> None:
    """
    Register every Flask blueprint that makes up the application.

    NOTE: These modules (routes/*) are built out in subsequent steps of
    this project. Each blueprint encapsulates one functional area
    (auth, students, classes, subjects, attendance, face recognition,
    dashboard, settings, logs) following the MVC pattern: routes/ receive
    the HTTP request and delegate business logic to controllers/services.
    """
    from routes.auth_routes import auth_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.student_routes import student_bp
    from routes.class_routes import class_bp
    from routes.subject_routes import subject_bp
    from routes.attendance_routes import attendance_bp
    from routes.face_routes import face_bp
    from routes.settings_routes import settings_bp
    from routes.log_routes import log_bp
    from routes.teacher_routes import teacher_bp
    from routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(class_bp)
    app.register_blueprint(subject_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(face_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(log_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")


def _register_error_handlers(app: Flask) -> None:
    """Register application-wide error handlers for clean JSON/HTML responses."""

    @app.errorhandler(404)
    def not_found(error: HTTPException):
        if _wants_json():
            return jsonify(success=False, message="Resource not found."), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error: HTTPException):
        if _wants_json():
            return jsonify(success=False, message="Access forbidden."), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(error: HTTPException):
        logger.exception("Unhandled server error: %s", error)
        if _wants_json():
            return jsonify(success=False, message="Internal server error."), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def handle_uncaught_exception(error: Exception):
        # Let real HTTP exceptions (404, 403, etc.) fall through to their
        # dedicated handlers above; only swallow truly unexpected errors.
        if isinstance(error, HTTPException):
            return error
        logger.exception("Uncaught exception: %s", error)
        if _wants_json():
            return jsonify(success=False, message="An unexpected error occurred."), 500
        return render_template("errors/500.html"), 500


def _wants_json() -> bool:
    """Heuristic: does the current request expect a JSON error response (API call)?"""
    from flask import request

    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def _register_cli_commands(app: Flask) -> None:
    """Register custom `flask <command>` CLI commands for admin/dev tasks."""

    @app.cli.command("create-admin")
    def create_admin_command():
        """Interactively create a new admin user: `flask create-admin`."""
        from services.auth_service import AuthService

        username = input("Username: ").strip()
        email = input("Email: ").strip()
        full_name = input("Full name: ").strip()
        password = input("Password: ").strip()

        service = AuthService()
        admin, error = service.create_admin(username, email, full_name, password)
        if error:
            print(f"Failed to create admin: {error}")
        else:
            print(f"Admin '{admin.username}' created successfully.")

    @app.cli.command("rebuild-encodings")
    def rebuild_encodings_command():
        """Regenerate the encodings.pickle cache from the database: `flask rebuild-encodings`."""
        from services.face_service import FaceService

        count = FaceService().rebuild_encoding_cache()
        print(f"Rebuilt encoding cache with {count} encodings.")

    @app.cli.command("unlock-admin")
    def unlock_admin_command():
        """Unlock any admin/teacher account from the command line: `flask unlock-admin`."""
        from models import Admin

        username = input("Username of the account to unlock: ").strip()
        admin = Admin.query.filter_by(username=username).first()
        if admin is None:
            print(f"No account found with username '{username}'.")
            return

        admin.reset_lockout()
        db.session.commit()
        print(f"Account '{username}' has been unlocked.")

    @app.cli.command("reset-password")
    def reset_password_command():
        """
        Reset any account's password from the command line — the fallback
        for when even the super admin forgets theirs: `flask reset-password`.
        """
        from getpass import getpass

        from models import Admin
        from services.auth_service import AuthService

        username = input("Username of the account to reset: ").strip()
        admin = Admin.query.filter_by(username=username).first()
        if admin is None:
            print(f"No account found with username '{username}'.")
            return

        new_password = getpass("New password (min 8 chars, letter + number): ")
        confirm_password = getpass("Confirm new password: ")
        if new_password != confirm_password:
            print("Passwords do not match. Aborted.")
            return

        success, error = AuthService().reset_password_direct(admin.id, new_password)
        if not success:
            print(f"Failed: {error}")
        else:
            print(f"Password for '{username}' has been reset successfully.")


def _seed_default_admin(app: Flask) -> None:
    """
    Create a default admin account on first run so the system is usable
    immediately after installation, if no admin exists yet.

    Credentials are read from environment variables when provided, and
    fall back to safe defaults intended ONLY for local development.
    """
    from models import Admin

    if Admin.query.first() is not None:
        return  # An admin already exists — nothing to seed.

    default_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    default_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@attendance.local")
    default_password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@123")

    admin = Admin(
        username=default_username,
        email=default_email,
        full_name="System Administrator",
        role="superadmin",
    )
    admin.set_password(default_password)
    db.session.add(admin)
    db.session.commit()

    logger.warning(
        "No admin existed — created default admin '%s'. "
        "CHANGE THIS PASSWORD IMMEDIATELY IN PRODUCTION.",
        default_username,
    )


# --------------------------------------------------------------------------
# Local development entry point.
# --------------------------------------------------------------------------
app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))
