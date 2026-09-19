"""
controllers/log_controller.py
==============================
HTTP-facing coordination layer for the audit-log viewer.
"""

from __future__ import annotations

from services.log_service import LogService
from utils.helpers import safe_int


class LogController:
    """Coordinates audit-log search requests."""

    def __init__(self) -> None:
        self.log_service = LogService()

    def search(self, args):
        return self.log_service.search(
            level=args.get("level") or None,
            query=args.get("q") or None,
            page=safe_int(args.get("page"), 1),
            per_page=safe_int(args.get("per_page"), 50),
        )
