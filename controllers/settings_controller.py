"""
controllers/settings_controller.py
===================================
HTTP-facing coordination layer for the Settings panel.
"""

from __future__ import annotations

from services.settings_service import SettingsService


class SettingsController:
    """Coordinates read/update of application settings."""

    def __init__(self) -> None:
        self.settings_service = SettingsService()

    def get_all(self) -> dict:
        return self.settings_service.get_all()

    def update(self, form) -> None:
        # Only persist keys that were actually part of the settings form,
        # to avoid accidentally wiping unrelated settings.
        from services.settings_service import DEFAULT_SETTINGS

        values = {key: form.get(key) for key in DEFAULT_SETTINGS if key in form}
        self.settings_service.update_many(values)
