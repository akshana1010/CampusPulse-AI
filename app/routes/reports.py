"""
CampusPulse AI – Reports Blueprint
Handles report submission, listing, detail view, map data, and voting.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Report, ReportVote, Notification, CATEGORIES, STATUSES
from app.services.ai_service import analyze_report
from app.services.file_service import save_uploaded_image
from app.utils.decorators import student_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@login_required
def dashboard():
    """Student dashboard – shows the current user's reports."""
    page = request.args.get("page", 1, type=int)
    user_reports = (
        Report.query
        .filter_by(user_id=current_user.id)
        .order_by(Report.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    # Summary stats for the student
    total = Report.query.filter_by(user_id=current_user.id).count()
    resolved = Report.query.filter_by(user_id=current_user.id, status="Resolved").count()
    open_reports = Report.query.filter(
        Report.user_id == current_user.id,
        Report.status.in_(["Reported", "In Progress"])
    ).count()
    high_critical = Report.query.filter(
        Report.user_id == current_user.id,
        Report.priority.in_(["High", "Critical"])
    ).count()

    # Problems by Category breakdown
    category_counts = {
        cat: Report.query.filter_by(user_id=current_user.id, category=cat).count()
        for cat in CATEGORIES
    }

    unread_notifications = (
        Notification.query
        .filter_by(user_id=current_user.id, is_read=False)
        .count()
    )

    return render_template(
        "student/dashboard.html",
        reports=user_reports,
        total=total,
        open_reports=open_reports,
        pending=open_reports,
        resolved=resolved,
        high_critical=high_critical,
        category_counts=category_counts,
        categories=CATEGORIES,
        unread_notifications=unread_notifications,
    )


@reports_bp.route("/submit", methods=["GET", "POST"])
@login_required
@student_required
def submit():
    """Render and handle the problem report submission form."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Other")
        latitude = request.form.get("latitude", type=float)
        longitude = request.form.get("longitude", type=float)
        location_label = request.form.get("location_label", "").strip() or None

        # Validation
        if not title or not description:
            flash("Title and description are required.", "danger")
            return render_template("student/submit_report.html", categories=CATEGORIES)

        if category not in CATEGORIES:
            category = "Other"

        # File upload (optional)
        image_path = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename:
                image_path, error = save_uploaded_image(file, current_app.config)
                if error:
                    flash(f"Image upload failed: {error}", "warning")

        # AI analysis (graceful fallback on failure)
        ai_result = {}
        try:
            ai_result = analyze_report(title, description, category)
        except Exception as exc:
            current_app.logger.warning(f"AI analysis failed: {exc}")

        report = Report(
            title=title,
            description=description,
            category=category,
            latitude=latitude,
            longitude=longitude,
            location_label=location_label,
            image_path=image_path,
            user_id=current_user.id,
            # AI fields (empty strings become None-safe defaults)
            ai_category=ai_result.get("predicted_category"),
            priority=ai_result.get("priority", "Low"),
            ai_summary=ai_result.get("summary"),
            ai_sentiment=ai_result.get("sentiment"),
            ai_confidence=ai_result.get("confidence"),
            ai_raw_response=ai_result.get("raw_response"),
        )

        db.session.add(report)
        db.session.commit()

        flash("Report submitted successfully! AI analysis complete.", "success")
        return redirect(url_for("reports.detail", report_id=report.id))

    return render_template("student/submit_report.html", categories=CATEGORIES)


@reports_bp.route("/<int:report_id>")
@login_required
def detail(report_id):
    """View a single report's full detail page."""
    report = Report.query.get_or_404(report_id)

    # Students can only view their own reports; admins can view all
    if not current_user.is_admin and report.user_id != current_user.id:
        flash("You do not have permission to view this report.", "danger")
        return redirect(url_for("reports.dashboard"))

    history = report.status_history.order_by(db.text("changed_at ASC")).all()

    user_vote = ReportVote.query.filter_by(
        report_id=report_id, user_id=current_user.id
    ).first()

    return render_template(
        "student/report_detail.html",
        report=report,
        history=history,
        user_vote=user_vote,
    )


@reports_bp.route("/map-data")
def map_data():
    """
    Public JSON endpoint returning all geo-located reports for the Leaflet map.
    No authentication required so the campus map is publicly viewable.
    """
    reports = (
        Report.query
        .filter(Report.latitude.isnot(None), Report.longitude.isnot(None))
        .all()
    )
    return jsonify([r.to_map_dict() for r in reports])


@reports_bp.route("/map")
@login_required
def campus_map():
    """Full-page interactive campus map showing all geo-located problem reports."""
    total_reports = Report.query.filter(
        Report.latitude.isnot(None), Report.longitude.isnot(None)
    ).count()
    return render_template("student/campus_map.html", total_reports=total_reports)


@reports_bp.route("/<int:report_id>/vote", methods=["POST"])
@login_required
@student_required
def vote(report_id):
    """Upvote or downvote a report (toggle on repeat)."""
    report = Report.query.get_or_404(report_id)
    vote_type = request.json.get("vote_type", "upvote")

    if vote_type not in ("upvote", "downvote"):
        return jsonify({"error": "Invalid vote type."}), 400

    existing = ReportVote.query.filter_by(
        report_id=report_id, user_id=current_user.id
    ).first()

    if existing:
        if existing.vote_type == vote_type:
            # Same vote → remove it (toggle off)
            db.session.delete(existing)
        else:
            # Different vote → switch it
            existing.vote_type = vote_type
    else:
        new_vote = ReportVote(
            report_id=report_id,
            user_id=current_user.id,
            vote_type=vote_type,
        )
        db.session.add(new_vote)

    db.session.commit()

    return jsonify({
        "upvotes": report.upvote_count,
        "downvotes": report.downvote_count,
    })


@reports_bp.route("/<int:report_id>/delete", methods=["POST"])
@login_required
def delete(report_id):
    """Allow a student to delete their own unresolved report."""
    report = Report.query.get_or_404(report_id)

    if report.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized."}), 403

    if report.status == "Resolved" and not current_user.is_admin:
        flash("Resolved reports cannot be deleted.", "warning")
        return redirect(url_for("reports.detail", report_id=report_id))

    db.session.delete(report)
    db.session.commit()
    flash("Report deleted.", "info")
    return redirect(url_for("reports.dashboard"))
