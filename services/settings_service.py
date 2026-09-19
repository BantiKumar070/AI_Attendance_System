"""
services/settings_service.py
=============================
Read/write access to the generic key-value ``Setting`` table backing
the admin Settings panel (recognition tolerance, cooldown, email
toggle, etc).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from models import Setting
from utils.extensions import db

# Defaults shown/created the first time the Settings page is opened.
DEFAULT_SETTINGS: Dict[str, str] = {
    "face_recognition_tolerance": "0.45",
    "attendance_cooldown_minutes": "5",
    "late_cutoff_hour": "",  # empty = disabled; every mark counts as "Present"
    "enable_email_notifications": "false",
    "dataset_samples_per_student": "100",
    "institution_name": "My Institution",
}


class SettingsService:
    """CRUD for application settings."""

    def get_all(self) -> Dict[str, str]:
        """Return every setting as a dict, seeding defaults for any missing keys."""
        self._ensure_defaults()
        return {s.key: s.value for s in Setting.query.all()}

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default

    def set(self, key: str, value: Any) -> Setting:
        setting = Setting.query.filter_by(key=key).first()
        if setting is None:
            setting = Setting(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)
        db.session.commit()
        return setting

    def update_many(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    def _ensure_defaults(self) -> None:
        existing_keys = {s.key for s in Setting.query.all()}
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing_keys:
                db.session.add(Setting(key=key, value=value, description=key.replace("_", " ").title()))
        db.session.commit()
