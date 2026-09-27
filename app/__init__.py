"""
CampusPulse AI – Application Factory
Creates and configures the Flask application instance.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config import get_config

# ── Extension instances (not yet bound to an app) ─────────────────────────────
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=None):
    """
    Application factory.
    Usage:
        app = create_app()                     # uses FLASK_ENV
        app = create_app(TestingConfig)        # explicit override
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # ── Load configuration ─────────────────────────────────────────────────────
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # ── Ensure required directories exist ─────────────────────────────────────
    _ensure_directories(app)

    # ── Initialize extensions ──────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # ── Flask-Login settings ───────────────────────────────────────────────────
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # ── User loader ────────────────────────────────────────────────────────────
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Register blueprints ────────────────────────────────────────────────────
    _register_blueprints(app)

    # ── Register error handlers ────────────────────────────────────────────────
    _register_error_handlers(app)

    # ── Shell context (for `flask shell`) ─────────────────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Report, StatusHistory, ReportVote, Notification, AdminAction
        return {
            "db": db,
            "User": User,
            "Report": Report,
            "StatusHistory": StatusHistory,
            "ReportVote": ReportVote,
            "Notification": Notification,
            "AdminAction": AdminAction,
        }

    return app


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ensure_directories(app):
    """Create necessary runtime directories if they don't exist."""
    dirs = [
        app.config.get("UPLOAD_FOLDER", "uploads"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")

    # Root redirect – send authenticated users to dashboard, others to login
    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("reports.dashboard"))
        return redirect(url_for("auth.login"))

    # ── Convenience top-level aliases (/login, /register, /logout) ────────────
    @app.route("/login", methods=["GET", "POST"])
    def login_alias():
        return redirect(url_for("auth.login"), 301)

    @app.route("/register", methods=["GET", "POST"])
    def register_alias():
        return redirect(url_for("auth.register"), 301)

    @app.route("/logout", methods=["POST"])
    def logout_alias():
        return redirect(url_for("auth.logout"), 307)


def _register_error_handlers(app):
    """Register custom HTTP error pages."""
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500
