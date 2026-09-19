"""
utils/jwt_utils.py
===================
Small wrapper around PyJWT used for stateless admin authentication on
the REST API (routes/api_routes.py). The HTML dashboard itself uses a
normal Flask session cookie (see services/auth_service.py) for simplicity,
while the JWT is offered for programmatic / mobile API consumers.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional, Tuple

import jwt
from flask import current_app


def generate_token(payload: Dict[str, Any], expires_delta: Optional[dt.timedelta] = None) -> str:
    """
    Create a signed JWT containing the given payload.

    Args:
        payload: Claims to embed (e.g. {"admin_id": 1, "username": "admin"}).
        expires_delta: Optional custom expiry; defaults to
                        JWT_ACCESS_TOKEN_EXPIRES from config.

    Returns:
        The encoded JWT string.
    """
    now = dt.datetime.now(dt.timezone.utc)
    expires_delta = expires_delta or current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]

    claims = payload.copy()
    claims.update({"iat": now, "exp": now + expires_delta})

    return jwt.encode(
        claims,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def decode_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Decode and validate a JWT.

    Returns:
        (payload, None) on success, or (None, error_message) on failure.
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired."
    except jwt.InvalidTokenError:
        return None, "Invalid token."
