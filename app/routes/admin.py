"""
CampusPulse AI – Admin Blueprint
Restricted to users with role='admin'. Provides report management,
status updates, priority overrides, notes, and user management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Report, StatusHistory, User, Notification, CATEGORIES, PRIORITIES, STATUSES
from app.utils.decorators import admin_required
from app.services.notification_service import send_status_notification

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login")
def login_redirect():
    """Redirect /admin/login to the dedicated Admin Login portal."""
    return redirect(url_for("auth.admin_login"))


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    """Admin overview dashboard with summary statistics."""
    total = Report.query.count()
    by_status = {s: Report.query.filter_by(status=s).count() for s in STATUSES}
    open_reports = Report.query.filter(Report.status.in_(["Reported", "In Progress"])).count()
    high_critical = Report.query.filter(Report.priority.in_(["High", "Critical"])).count()
    recent = (
        Report.query
        .order_by(Report.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        total=total,
        by_status=by_status,
        open_reports=open_reports,
        high_critical=high_critical,
        critical=high_critical,
        recent=recent,
        statuses=STATUSES,
        categories=CATEGORIES,
        priorities=PRIORITIES,
    )


@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    """Paginated, filterable list of all submitted reports."""
    page = request.args.get("page", 1, type=int)
    category_filter = request.args.get("category", "")
    priority_filter = request.args.get("priority", "")
    status_filter = request.args.get("status", "")
    search_query = request.args.get("q", "").strip()

    query = Report.query

    if category_filter and category_filter in CATEGORIES:
        query = query.filter_by(category=category_filter)
    if priority_filter and priority_filter in PRIORITIES:
        query = query.filter_by(priority=priority_filter)
    if status_filter and status_filter in STATUSES:
        query = query.filter_by(status=status_filter)
    if search_query:
        query = query.filter(
            db.or_(
                Report.title.ilike(f"%{search_query}%"),
                Report.description.ilike(f"%{search_query}%"),
            )
        )

    paginated = query.order_by(Report.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template(
        "admin/reports.html",
        reports=paginated,
        categories=CATEGORIES,
        priorities=PRIORITIES,
        statuses=STATUSES,
        current_filters={
            "category": category_filter,
            "priority": priority_filter,
            "status": status_filter,
            "q": search_query,
        },
    )


@admin_bp.route("/reports/<int:report_id>")
@login_required
@admin_required
def report_detail(report_id):
    """Admin view of a single report with full management controls."""
    report = Report.query.get_or_404(report_id)
    history = report.status_history.order_by(db.text("changed_at ASC")).all()
    return render_template(
        "admin/report_detail.html",
        report=report,
        history=history,
        statuses=STATUSES,
        priorities=PRIORITIES,
    )


@admin_bp.route("/reports/<int:report_id>/status", methods=["PATCH"])
@login_required
@admin_required
def update_status(report_id):
    """Update a report's status and log the change."""
    report = Report.query.get_or_404(report_id)
    data = request.get_json() or {}
    new_status = data.get("status")
    note = data.get("note", "")

    if new_status not in STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {STATUSES}"}), 400

    old_status = report.status
    report.status = new_status

    if new_status == "Resolved":
        from datetime import datetime, timezone
        report.resolved_at = datetime.now(timezone.utc)

    history_entry = StatusHistory(
        report_id=report.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=current_user.id,
        note=note or None,
    )
    db.session.add(history_entry)
    db.session.commit()

    # Notify the report author
    send_status_notification(report, old_status, new_status)

    return jsonify({
        "success": True,
        "report_id": report.id,
        "new_status": new_status,
    })


@admin_bp.route("/reports/<int:report_id>/priority", methods=["PATCH"])
@login_required
@admin_required
def update_priority(report_id):
    """Override the AI-assigned priority."""
    report = Report.query.get_or_404(report_id)
    data = request.get_json() or {}
    new_priority = data.get("priority")

    if new_priority not in PRIORITIES:
        return jsonify({"error": f"Invalid priority. Must be one of: {PRIORITIES}"}), 400

    report.priority = new_priority
    db.session.commit()

    return jsonify({"success": True, "report_id": report.id, "new_priority": new_priority})


@admin_bp.route("/reports/<int:report_id>/note", methods=["POST"])
@login_required
@admin_required
def add_note(report_id):
    """Add or update an admin note on a report."""
    report = Report.query.get_or_404(report_id)
    data = request.get_json() or {}
    note = data.get("note", "").strip()

    if not note:
        return jsonify({"error": "Note cannot be empty."}), 400

    report.admin_notes = note
    db.session.commit()

    return jsonify({"success": True, "note": report.admin_notes})


@admin_bp.route("/reports/<int:report_id>/delete", methods=["DELETE"])
@login_required
@admin_required
def delete_report(report_id):
    """Hard delete a report (admin only)."""
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    """List all registered users."""
    page = request.args.get("page", 1, type=int)
    all_users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@login_required
@admin_required
def update_user_role(user_id):
    """Promote or demote a user's role."""
    if user_id == current_user.id:
        return jsonify({"error": "You cannot change your own role."}), 400

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    new_role = data.get("role")

    if new_role not in ("student", "admin"):
        return jsonify({"error": "Role must be 'student' or 'admin'."}), 400

    user.role = new_role
    db.session.commit()

    return jsonify({"success": True, "user_id": user.id, "new_role": user.role})
