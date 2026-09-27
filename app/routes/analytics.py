"""
CampusPulse AI – Analytics Blueprint
Provides JSON data endpoints consumed by Chart.js on the admin dashboard.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app import db
from app.models import Report, CATEGORIES, STATUSES, PRIORITIES
from app.utils.decorators import admin_required

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/summary")
@login_required
@admin_required
def summary():
    """
    Top-level counts: total reports, breakdown by status, category, priority.
    Used for KPI cards on the admin dashboard.
    """
    total = Report.query.count()

    by_status = {
        s: Report.query.filter_by(status=s).count() for s in STATUSES
    }
    by_priority = {
        p: Report.query.filter_by(priority=p).count() for p in PRIORITIES
    }
    by_category = {
        c: Report.query.filter_by(category=c).count() for c in CATEGORIES
    }

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
    })


@analytics_bp.route("/trends")
@login_required
@admin_required
def trends():
    """
    Reports submitted per day for the last N days (default: 30).
    Used for the line chart.
    """
    days = request.args.get("days", 30, type=int)
    days = max(7, min(days, 90))  # clamp between 7 and 90

    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.session.query(
            func.date(Report.created_at).label("day"),
            func.count(Report.id).label("count"),
        )
        .filter(Report.created_at >= since)
        .group_by(func.date(Report.created_at))
        .order_by(func.date(Report.created_at))
        .all()
    )

    # Fill in missing days with 0
    result = {}
    for i in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result[day] = 0
    for row in rows:
        result[str(row.day)] = row.count

    return jsonify({
        "labels": list(result.keys()),
        "data": list(result.values()),
    })


@analytics_bp.route("/category-breakdown")
@login_required
@admin_required
def category_breakdown():
    """
    Count of reports per category.
    Used for the doughnut/bar chart.
    """
    rows = (
        db.session.query(Report.category, func.count(Report.id))
        .group_by(Report.category)
        .all()
    )
    data = {row[0]: row[1] for row in rows}
    # Ensure all categories appear (even with 0)
    full = {c: data.get(c, 0) for c in CATEGORIES}

    return jsonify({
        "labels": list(full.keys()),
        "data": list(full.values()),
    })


@analytics_bp.route("/heatmap-data")
def heatmap_data():
    """
    Lat/lng/weight data for the Leaflet heatmap layer.
    Public endpoint – no auth required.
    """
    reports = (
        Report.query
        .filter(Report.latitude.isnot(None), Report.longitude.isnot(None))
        .with_entities(Report.latitude, Report.longitude, Report.priority)
        .all()
    )

    priority_weight = {"Low": 0.25, "Medium": 0.5, "High": 0.75, "Critical": 1.0}

    points = [
        [r.latitude, r.longitude, priority_weight.get(r.priority, 0.5)]
        for r in reports
    ]

    return jsonify(points)


@analytics_bp.route("/resolution-time")
@login_required
@admin_required
def resolution_time():
    """
    Average time (in hours) from 'Reported' to 'Resolved' per category.
    Used for the horizontal bar chart.
    """
    rows = (
        db.session.query(
            Report.category,
            func.avg(
                func.julianday(Report.resolved_at) - func.julianday(Report.created_at)
            ).label("avg_days"),
        )
        .filter(Report.resolved_at.isnot(None))
        .group_by(Report.category)
        .all()
    )

    data = {}
    for row in rows:
        avg_hours = round(row.avg_days * 24, 1) if row.avg_days else 0
        data[row.category] = avg_hours

    full = {c: data.get(c, 0) for c in CATEGORIES}

    return jsonify({
        "labels": list(full.keys()),
        "data": list(full.values()),
        "unit": "hours",
    })
