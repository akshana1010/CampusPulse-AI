"""
CampusPulse AI – Auth Blueprint
Handles user registration, login, and logout.
Routes: /auth/login  /auth/register  /auth/logout  /auth/me
"""

import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

# Simple email regex
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("reports.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        # Field presence check
        if not email or not password:
            flash("Email or User ID and password are required.", "danger")
            return render_template("auth/login.html", email=email)

        lookup_email = "admin@campuspulse.ai" if email == "admin" else email
        user = User.query.filter(
            db.or_(
                User.email == lookup_email,
                User.student_id == email
            )
        ).first()

        if user is None:
            flash("No account found with that email or User ID.", "danger")
            return render_template("auth/login.html", email=email)

        if not user.is_active:
            flash("Your account has been deactivated. Contact support.", "danger")
            return render_template("auth/login.html", email=email)

        if not user.check_password(password):
            flash("Incorrect password. Please try again.", "danger")
            return render_template("auth/login.html", email=email)

        login_user(user, remember=remember)
        next_page = request.args.get("next")
        flash(f"Welcome back, {user.name}! 👋", "success")

        # Role-based redirect
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        if user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("reports.dashboard"))

    return render_template("auth/login.html", email="")


@auth_bp.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    """Dedicated administrative login portal."""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email or not password:
            flash("Admin ID and password are required.", "danger")
            return render_template("auth/admin_login.html", email=email)

        lookup_email = "admin@campuspulse.ai" if email == "admin" else email
        user = User.query.filter(
            db.or_(
                User.email == lookup_email,
                User.student_id == email
            )
        ).first()

        if user is None or not user.check_password(password):
            flash("Invalid administrator credentials. Please try again.", "danger")
            return render_template("auth/admin_login.html", email=email)

        if not user.is_active:
            flash("Your administrator account is inactive. Please contact system support.", "danger")
            return render_template("auth/admin_login.html", email=email)

        if not user.is_admin:
            flash("Access denied: This portal is restricted to authorized campus administrators only.", "danger")
            return render_template("auth/admin_login.html", email=email)

        if current_user.is_authenticated:
            logout_user()

        login_user(user, remember=remember)
        flash(f"Welcome to the Admin Portal, {user.name}! 🛡️", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/admin"):
            return redirect(next_page)
        return redirect(url_for("admin.dashboard"))

    return render_template("auth/admin_login.html", email="")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new student account."""
    if current_user.is_authenticated:
        return redirect(url_for("reports.dashboard"))

    form_data = {}

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        student_id = request.form.get("student_id", "").strip() or None
        department = request.form.get("department", "").strip() or None
        year = request.form.get("year", type=int)

        # Preserve form values on error
        form_data = {
            "name": name,
            "email": email,
            "student_id": student_id or "",
            "department": department or "",
            "year": year or "",
        }

        errors = []

        # Empty field checks
        if not name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email address is required.")
        if not password:
            errors.append("Password is required.")
        if not confirm_password:
            errors.append("Please confirm your password.")

        # Email format
        if email and not _EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")

        # Password strength
        if password and len(password) < 8:
            errors.append("Password must be at least 8 characters long.")

        # Password match
        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match.")

        # Duplicate email
        if email and _EMAIL_RE.match(email) and User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists. Try logging in instead.")

        # Duplicate student ID
        if student_id and User.query.filter_by(student_id=student_id).first():
            errors.append("This student ID is already registered.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html", form=form_data)

        user = User(
            name=name,
            email=email,
            student_id=student_id,
            department=department,
            year=year,
            role="student",
        )
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Registration failed due to a database error. Please try again.", "danger")
            return render_template("auth/register.html", form=form_data)

        login_user(user)
        flash(f"Welcome to CampusPulse AI, {user.name}! 🎓 Your account has been created.", "success")
        return redirect(url_for("reports.dashboard"))

    return render_template("auth/register.html", form=form_data)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash("You have been signed out. See you next time! 👋", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/me")
@login_required
def me():
    """Return current user info as JSON (used by frontend JS)."""
    return jsonify(current_user.to_dict())
