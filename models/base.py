"""
models/base.py
===============
Common base mixin shared by every ORM model in the system.

Provides:
    * Automatic ``created_at`` / ``updated_at`` timestamps.
    * A generic ``to_dict()`` serializer so controllers/services can
      return JSON from any model without writing repetitive boilerplate.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from utils.extensions import db


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (avoids naive-datetime bugs)."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds created_at / updated_at columns to any model that inherits it."""

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class SerializerMixin:
    """Generic dict-serialization for API responses."""

    def to_dict(self, exclude: tuple = ()) -> Dict[str, Any]:
        """
        Convert the SQLAlchemy model instance into a plain dictionary.

        Args:
            exclude: Column names to omit from the output (e.g. password
                     hashes, raw face encodings).

        Returns:
            A dict of column_name -> python-native value, safe to
            ``jsonify()`` directly.
        """
        result: Dict[str, Any] = {}
        for column in self.__table__.columns:  # type: ignore[attr-defined]
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, bytes):
                # Never serialize raw binary blobs (e.g. face encodings) as-is
                value = f"<{len(value)} bytes>"
            result[column.name] = value
        return result
