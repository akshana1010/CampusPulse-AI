"""
CampusPulse AI – Custom Decorators
Route protection decorators beyond Flask-Login's @login_required.
"""

from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def admin_required(f):
    """
    Decorator that restricts a route to users with role='admin'.
    Must be applied AFTER @login_required.

    Usage:
        @app.route('/admin/')
        @login_required
        @admin_required
        def admin_dashboard():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.admin_login", next=request.path))
        if not current_user.is_admin:
            flash("Access denied: Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """
    Decorator that restricts a route to authenticated student users.
    Admins are also allowed through (they can do everything students can).
    Must be applied AFTER @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role not in ("student", "admin"):
            flash("Only registered students can access this page.", "warning")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
