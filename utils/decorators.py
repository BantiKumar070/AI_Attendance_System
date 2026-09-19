"""
utils/decorators.py
====================
Reusable route decorators for authentication / authorization.

Two auth mechanisms are supported side by side:
    * Session-based (``@login_required``) — used by the server-rendered
      HTML dashboard (routes/*_routes.py).
    * JWT-based (``@token_required``) — used by the pure REST API
      (routes/api_routes.py) for external / mobile clients.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import g, jsonify, redirect, request, session, url_for, flash

from utils.jwt_utils import decode_token
from utils.logger import get_logger

logger = get_logger(__name__)


def login_required(view_func: Callable) -> Callable:
    """Protect a server-rendered dashboard route with the session cookie."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login_page", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped


def roles_required(*allowed_roles: str) -> Callable:
    """Restrict a route to specific admin roles (e.g. 'superadmin')."""

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not session.get("admin_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login_page"))
            if session.get("role") not in allowed_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard.index"))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def superadmin_required(view_func: Callable) -> Callable:
    """Restrict a route to superadmin only (e.g. teacher account management)."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login_page"))
        if session.get("role") != "superadmin":
            flash("Only a super admin can access this page.", "danger")
            return redirect(url_for("dashboard.index"))
        return view_func(*args, **kwargs)

    return wrapped


def get_session_class_filter():
    """
    Read the current session's class restriction, set at login time.

    Returns:
        None -> caller has unrestricted access (admin/superadmin)
        []   -> a teacher account with NO classes assigned yet (sees nothing)
        [..] -> a teacher restricted to these ClassRoom IDs
    """
    return session.get("accessible_class_ids")


def get_session_subject_filter():
    """
    Read the current session's subject restriction, set at login time.

    Returns:
        None -> caller has unrestricted access (admin/superadmin)
        []   -> a teacher account with NO subjects assigned yet
        [..] -> a teacher restricted to teaching these Subject IDs
    """
    return session.get("accessible_subject_ids")


def token_required(view_func: Callable) -> Callable:
    """Protect a JSON API route (routes/api_routes.py) using a Bearer JWT."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify(success=False, message="Missing or malformed Authorization header."), 401

        token = auth_header.split(" ", 1)[1].strip()
        payload, error = decode_token(token)
        if error:
            return jsonify(success=False, message=error), 401

        g.jwt_payload = payload
        g.admin_id = payload.get("admin_id")
        return view_func(*args, **kwargs)

    return wrapped
