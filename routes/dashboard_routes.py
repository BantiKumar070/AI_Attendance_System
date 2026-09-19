"""
routes/dashboard_routes.py
===========================
The main landing page after login: KPI cards + Chart.js analytics.
"""

from __future__ import annotations

from flask import Blueprint, render_template

from controllers.dashboard_controller import DashboardController
from utils.decorators import get_session_class_filter, login_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")
dashboard_controller = DashboardController()


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    """Render the admin dashboard with live analytics."""
    data = dashboard_controller.get_dashboard_data(accessible_class_ids=get_session_class_filter())
    return render_template("admin/dashboard.html", **data)
