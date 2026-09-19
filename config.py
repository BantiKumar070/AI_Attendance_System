"""
config.py
=========
Centralized configuration management for the AI-Powered Automatic
Attendance System.

Uses the standard "Config object per environment" pattern so the same
codebase can run in development, testing, or production simply by
changing the ``FLASK_ENV`` / ``APP_ENV`` environment variable.

Author: Attendance System Engineering Team
"""

import os
from datetime import timedelta
from pathlib import Path

# --------------------------------------------------------------------------
# Base directory of the project (absolute path). All relative paths in the
# application are built from this to make the app runnable from anywhere.
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """
    Base configuration class.

    Holds settings that are common to every environment. Environment
    specific classes (DevelopmentConfig, ProductionConfig, TestingConfig)
    inherit from this and override only what differs.
    """

    # ---------------- General ----------------
    APP_NAME: str = "AI-Powered Automatic Attendance System"
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # ---------------- Database ----------------
    # Default: SQLite (file based). Can be swapped for MySQL by simply
    # setting the DATABASE_URL environment variable, e.g.:
    #   mysql+pymysql://user:password@localhost/attendance_db
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verify connections before using (helps w/ MySQL)
    }

    # ---------------- JWT Authentication ----------------
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-this-jwt-secret-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=7)

    # ---------------- Session / Auto-Logout ----------------
    # The dashboard session expires after this many minutes of inactivity.
    # SESSION_REFRESH_EACH_REQUEST resets the countdown on every request,
    # so any activity (page navigation, AJAX ping) keeps the user logged in.
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(minutes=5)
    SESSION_REFRESH_EACH_REQUEST: bool = True
    # How many seconds before expiry the "session expiring" warning modal appears.
    SESSION_WARNING_SECONDS: int = 60

    # ---------------- File / Folder Paths ----------------
    UPLOAD_FOLDER: str = str(BASE_DIR / "uploads")
    DATASET_FOLDER: str = str(BASE_DIR / "dataset")
    TRAINER_FOLDER: str = str(BASE_DIR / "trainer")
    RECOGNIZER_FOLDER: str = str(BASE_DIR / "recognizer")
    EXPORTS_FOLDER: str = str(BASE_DIR / "exports")
    REPORTS_FOLDER: str = str(BASE_DIR / "reports")
    LOGS_FOLDER: str = str(BASE_DIR / "logs")

    ENCODINGS_FILE: str = str(BASE_DIR / "trainer" / "encodings.pickle")

    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

    # ---------------- Face Recognition Settings ----------------
    FACE_DATASET_SAMPLES: int = 100          # Images captured per student
    FACE_DETECTION_MODEL: str = "hog"        # "hog" (CPU) or "cnn" (GPU)
    FACE_RECOGNITION_TOLERANCE: float = 0.45  # Lower = stricter matching
    FACE_RESIZE_WIDTH: int = 640             # Resize frame width for speed
    ATTENDANCE_COOLDOWN_MINUTES: int = 5     # Prevent duplicate marks within window

    # ---------------- Email (optional notifications) ----------------
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.environ.get("MAIL_DEFAULT_SENDER", "attendance-system@example.com")
    ENABLE_EMAIL_NOTIFICATIONS: bool = os.environ.get("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"

    # ---------------- Pagination ----------------
    DEFAULT_PAGE_SIZE: int = 25

    # ---------------- CORS ----------------
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    @staticmethod
    def init_app(app) -> None:
        """
        Hook for subclasses / factory to perform extra initialization.
        Ensures all required directories exist before the app starts.
        """
        for folder in [
            Config.UPLOAD_FOLDER,
            Config.DATASET_FOLDER,
            Config.TRAINER_FOLDER,
            Config.RECOGNIZER_FOLDER,
            Config.EXPORTS_FOLDER,
            Config.REPORTS_FOLDER,
            Config.LOGS_FOLDER,
        ]:
            os.makedirs(folder, exist_ok=True)


class DevelopmentConfig(Config):
    """Configuration used for local development."""

    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = False  # Set True to log every SQL statement


class ProductionConfig(Config):
    """Configuration used in production deployments."""

    DEBUG: bool = False

    # In production, secrets MUST come from environment variables.
    # We intentionally do not provide insecure fallbacks here beyond the
    # base class so misconfiguration is obvious in logs instead of silently
    # running with a known default secret.


class TestingConfig(Config):
    """Configuration used by the automated test-suite (pytest)."""

    TESTING: bool = True
    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False


# --------------------------------------------------------------------------
# Mapping used by the application factory (app.py) to pick the right
# configuration class based on the APP_ENV environment variable.
# --------------------------------------------------------------------------
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config() -> type:
    """
    Return the configuration class that matches the current APP_ENV
    environment variable (defaults to 'development').
    """
    env = os.environ.get("APP_ENV", "default")
    return config_by_name.get(env, DevelopmentConfig)
