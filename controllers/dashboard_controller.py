"""
controllers/dashboard_controller.py
====================================
Assembles all data needed to render the admin dashboard in one place.
"""

from __future__ import annotations

from services.dashboard_service import DashboardService


class DashboardController:
    """Coordinates dashboard data aggregation."""

    def __init__(self) -> None:
        self.dashboard_service = DashboardService()

    def get_dashboard_data(self, accessible_class_ids=None) -> dict:
        return {
            "overview": self.dashboard_service.get_overview(accessible_class_ids),
            "weekly_trend": self.dashboard_service.get_weekly_trend_chart(accessible_class_ids),
            "class_distribution": self.dashboard_service.get_class_distribution_chart(accessible_class_ids),
            "recent_attendance": self.dashboard_service.get_recent_attendance(accessible_class_ids=accessible_class_ids),
            "subject_breakdown": self.dashboard_service.get_subject_breakdown(accessible_class_ids),
        }
