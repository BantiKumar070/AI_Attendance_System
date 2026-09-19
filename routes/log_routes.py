"""
routes/log_routes.py
=====================
Admin "Logs" panel: browse/filter the system audit trail.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request

from controllers.log_controller import LogController
from utils.decorators import roles_required

log_bp = Blueprint("log", __name__, url_prefix="/logs")
log_controller = LogController()


@log_bp.route("/")
@roles_required("admin", "superadmin")
def index():
    """Paginated, filterable audit-log viewer."""
    pagination = log_controller.search(request.args)
    return render_template("admin/logs.html", pagination=pagination, args=request.args)
