"""
Dashboard module for Timetracer.

Generates an HTML dashboard to browse and filter cassettes.
"""

from timetracer.dashboard.generator import DashboardData, generate_dashboard
from timetracer.dashboard.template import render_dashboard_html

__all__ = [
    "DashboardData",
    "generate_dashboard",
    "render_dashboard_html",
]
