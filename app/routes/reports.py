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
from app.services.duplicate_service import find_duplicate_report
from app.utils.decorators import student_required
from app.utils.campus_data import SMVEC_CAMPUS_AREAS, get_building_by_id, get_building_by_name

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/check-duplicate", methods=["POST"])
@login_required
def check_duplicate():
    """Live API endpoint to check if a problem report is a duplicate."""
    data = request.get_json(silent=True) or request.form
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    category = data.get("category", "")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    campus_building = data.get("campus_building", "").strip()
    location_label = data.get("location_label", "").strip()

    try:
        if latitude is not None and latitude != "":
            latitude = float(latitude)
        else:
            latitude = None
    except (ValueError, TypeError):
        latitude = None

    try:
        if longitude is not None and longitude != "":
            longitude = float(longitude)
        else:
            longitude = None
    except (ValueError, TypeError):
        longitude = None

    if campus_building and campus_building != "custom":
        b_info = get_building_by_id(campus_building) or get_building_by_name(campus_building)
        if b_info:
            if not location_label:
                location_label = b_info["name"]
            if latitude is None or longitude is None:
                latitude = b_info["center"][0]
                longitude = b_info["center"][1]
    elif location_label:
        b_info = get_building_by_name(location_label)
        if b_info and (latitude is None or longitude is None):
            latitude = b_info["center"][0]
            longitude = b_info["center"][1]

    dup = find_duplicate_report(
        title=title,
        description=description,
        category=category,
        latitude=latitude,
        longitude=longitude,
        campus_building=campus_building,
        location_label=location_label,
    )

    if dup:
        return jsonify({"has_duplicate": True, "duplicate": dup})
    return jsonify({"has_duplicate": False, "duplicate": None})


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
        campus_building = request.form.get("campus_building", "").strip()
        location_label = request.form.get("location_label", "").strip() or None
        is_anonymous = request.form.get("is_anonymous") in ("1", "true", "True", "on", "yes")
        is_emergency = request.form.get("is_emergency") in ("1", "true", "True", "on", "yes")
        confirm_duplicate = request.form.get("confirm_duplicate") in ("1", "true", "True") or request.form.get("force_submit") in ("1", "true", "True")

        # If campus building was chosen, set default coordinates and label if missing
        if campus_building and campus_building != "custom":
            b_info = get_building_by_id(campus_building) or get_building_by_name(campus_building)
            if b_info:
                if not location_label:
                    location_label = b_info["name"]
                if latitude is None or longitude is None:
                    latitude = b_info["center"][0]
                    longitude = b_info["center"][1]
        elif location_label:
            b_info = get_building_by_name(location_label)
            if b_info and (latitude is None or longitude is None):
                latitude = b_info["center"][0]
                longitude = b_info["center"][1]

        # Ensure coordinates are within valid geographic range
        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                latitude = None
                longitude = None

        # Validation
        if not title or not description:
            flash("Title and description are required.", "danger")
            return render_template("student/submit_report.html", categories=CATEGORIES, campus_areas=SMVEC_CAMPUS_AREAS)

        if category not in CATEGORIES:
            category = "Other"

        # Check for duplicates unless confirmed
        if not confirm_duplicate:
            dup = find_duplicate_report(
                title=title,
                description=description,
                category=category,
                latitude=latitude,
                longitude=longitude,
                campus_building=campus_building,
                location_label=location_label,
            )
            if dup:
                if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"has_duplicate": True, "duplicate": dup}), 200

                flash("⚠️ A similar problem has already been reported at this location.", "warning")
                return render_template(
                    "student/submit_report.html",
                    categories=CATEGORIES,
                    campus_areas=SMVEC_CAMPUS_AREAS,
                    duplicate_warning=dup,
                    form_data={
                        "title": title,
                        "description": description,
                        "category": category,
                        "is_anonymous": is_anonymous,
                        "is_emergency": is_emergency,
                        "latitude": latitude,
                        "longitude": longitude,
                        "campus_building": campus_building,
                        "location_label": location_label,
                    }
                )

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
            is_anonymous=is_anonymous,
            is_emergency=is_emergency,
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

    return render_template("student/submit_report.html", categories=CATEGORIES, campus_areas=SMVEC_CAMPUS_AREAS)


@reports_bp.route("/<int:report_id>")
@login_required
def detail(report_id):
    """View a single report's full detail page."""
    report = Report.query.get_or_404(report_id)
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
@reports_bp.route("/campus-map")
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
    """Support / upvote a problem report (toggle on repeat)."""
    report = Report.query.get_or_404(report_id)
    data = request.get_json(silent=True) or {}
    vote_type = data.get("vote_type", "upvote")

    if vote_type not in ("upvote", "downvote"):
        vote_type = "upvote"

    existing = ReportVote.query.filter_by(
        report_id=report_id, user_id=current_user.id
    ).first()

    has_upvoted = False
    if existing:
        if existing.vote_type == vote_type:
            # Same vote → remove it (toggle off)
            db.session.delete(existing)
            has_upvoted = False
        else:
            # Different vote → switch it
            existing.vote_type = vote_type
            has_upvoted = (vote_type == "upvote")
    else:
        new_vote = ReportVote(
            report_id=report_id,
            user_id=current_user.id,
            vote_type=vote_type,
        )
        db.session.add(new_vote)
        has_upvoted = (vote_type == "upvote")

    db.session.commit()

    return jsonify({
        "upvotes": report.upvote_count,
        "downvotes": report.downvote_count,
        "has_upvoted": has_upvoted,
        "report_id": report.id,
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
