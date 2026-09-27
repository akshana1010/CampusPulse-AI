"""
CampusPulse AI – Configuration
All sensitive values are loaded from environment variables.
Never commit actual secrets to source control.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared across all environments."""

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

    # ── Default Admin Account ────────────────────────────────────────────────
    ADMIN_ID = os.environ.get("ADMIN_ID", "admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@campuspulse.ai")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'campuspulse.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── File Uploads ──────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # ── Gemini AI ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    # ── Campus Map Defaults ───────────────────────────────────────────────────
    CAMPUS_NAME = os.environ.get("CAMPUS_NAME", "Sri Manakula Vinayagar Engineering College (SMVEC)")
    CAMPUS_LAT = float(os.environ.get("CAMPUS_LAT", "11.91411"))
    CAMPUS_LNG = float(os.environ.get("CAMPUS_LNG", "79.63558"))
    CAMPUS_ZOOM = int(os.environ.get("CAMPUS_ZOOM", "16"))

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"

    # ── WTF / CSRF ────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Development-specific overrides."""

    DEBUG = True
    TESTING = False
    WTF_CSRF_ENABLED = False  # Disable CSRF in dev for easier API testing


class TestingConfig(Config):
    """Testing-specific overrides."""

    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "tests", "test_uploads")


class ProductionConfig(Config):
    """Production-specific overrides."""

    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True


# ── Config registry ────────────────────────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Return the configuration class based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
