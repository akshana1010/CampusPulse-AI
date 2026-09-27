"""
Tests for Automatic Admin Initialization
Verifies:
  1. Default admin account is created automatically when missing.
  2. Initialization is idempotent (never duplicates admin accounts).
  3. Environment variables (ADMIN_ID, ADMIN_EMAIL, ADMIN_PASSWORD) are respected.
  4. Existing admin accounts are preserved without alteration.
  5. Admin can authenticate using both email and student_id/admin_id.
"""

import pytest
from app import create_app, db, _ensure_admin
from app.models import User
from config import TestingConfig


class CustomAdminConfig(TestingConfig):
    ADMIN_ID = "custom_superadmin"
    ADMIN_EMAIL = "superadmin@campuspulse.ai"
    ADMIN_PASSWORD = "SuperSecretAdmin123!"


def test_admin_auto_created_when_missing():
    """Verify that default admin account is created when db tables are initialized."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Verify user table starts empty or we run _ensure_admin
        _ensure_admin(app)

        admin = User.query.filter_by(role="admin").first()
        assert admin is not None
        assert admin.email == app.config.get("ADMIN_EMAIL", "admin@campuspulse.ai")
        assert admin.student_id == app.config.get("ADMIN_ID", "admin")
        assert admin.check_password(app.config.get("ADMIN_PASSWORD", "Admin@12345"))
        assert admin.is_admin is True
        assert admin.is_active is True

        db.session.remove()
        db.drop_all()


def test_admin_init_is_idempotent():
    """Verify that running _ensure_admin multiple times never creates duplicate admins."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        _ensure_admin(app)
        count_after_first = User.query.filter_by(role="admin").count()
        assert count_after_first == 1

        # Run initialization again
        _ensure_admin(app)
        count_after_second = User.query.filter_by(role="admin").count()
        assert count_after_second == 1

        db.session.remove()
        db.drop_all()


def test_custom_admin_environment_config():
    """Verify that custom environment variables for admin credentials work properly."""
    app = create_app(CustomAdminConfig)
    with app.app_context():
        db.create_all()
        _ensure_admin(app)

        admin = User.query.filter_by(email="superadmin@campuspulse.ai").first()
        assert admin is not None
        assert admin.student_id == "custom_superadmin"
        assert admin.check_password("SuperSecretAdmin123!")

        client = app.test_client()

        # Login using email
        resp_email = client.post("/auth/admin-login", data={
            "email": "superadmin@campuspulse.ai",
            "password": "SuperSecretAdmin123!",
        }, follow_redirects=True)
        assert resp_email.status_code == 200

        client.post("/auth/logout", follow_redirects=True)

        # Login using admin ID
        resp_id = client.post("/auth/admin-login", data={
            "email": "custom_superadmin",
            "password": "SuperSecretAdmin123!",
        }, follow_redirects=True)
        assert resp_id.status_code == 200

        db.session.remove()
        db.drop_all()


def test_existing_admin_preserved():
    """Verify that if an admin already exists with a different password, it is not overwritten."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Manually create existing admin
        existing = User(
            name="Existing Admin",
            email="admin@campuspulse.ai",
            student_id="admin",
            role="admin",
            is_active=True,
        )
        existing.set_password("MyOriginalPassword123")
        db.session.add(existing)
        db.session.commit()

        # Run _ensure_admin
        _ensure_admin(app)

        admins = User.query.filter_by(role="admin").all()
        assert len(admins) == 1
        # Password remains the original password, not reset
        assert admins[0].check_password("MyOriginalPassword123")
        assert not admins[0].check_password("Admin@12345")

        db.session.remove()
        db.drop_all()
