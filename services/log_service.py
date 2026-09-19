"""
services/log_service.py
========================
Read access to the system_logs audit table (see models/system_log.py)
for the admin "Logs" screen.
"""

from __future__ import annotations

from typing import Optional

from models import SystemLog


class LogService:
    """Query helpers for the audit log."""

    def search(self, level: Optional[str] = None, query: Optional[str] = None, page: int = 1, per_page: int = 50):
        """Paginated, filterable audit-log search."""
        stmt = SystemLog.query

        if level:
            stmt = stmt.filter_by(level=level)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.filter(SystemLog.description.ilike(like) | SystemLog.action.ilike(like))

        stmt = stmt.order_by(SystemLog.created_at.desc())
        return stmt.paginate(page=page, per_page=per_page, error_out=False)

    def clear_old_logs(self, days: int = 90) -> int:
        """Delete audit-log rows older than N days. Returns the number of rows deleted."""
        from datetime import datetime, timedelta

        from utils.extensions import db

        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = SystemLog.query.filter(SystemLog.created_at < cutoff).delete()
        db.session.commit()
        return deleted
