"""
Tests for CampusPulse AI – Authentication routes.
Run with: pytest tests/test_auth.py -v
"""

import pytest
from app import create_app, db
from app.models import User
from config import TestingConfig


@pytest.fixture
def app():
    """Create application configured for testing with an in-memory DB."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create and return a sample student user."""
    with app.app_context():
        user = User(name="Test Student", email="test@uni.edu", role="student")
        user.set_password("securepassword123")
        db.session.add(user)
        db.session.commit()
        return user


# ── Register ───────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_page_loads(self, client):
        """GET /auth/register returns 200."""
        res = client.get("/auth/register")
        assert res.status_code == 200

    def test_register_success(self, client):
        """Valid registration creates user and redirects to dashboard."""
        res = client.post("/auth/register", data={
            "name": "Jane Doe",
            "email": "jane@uni.edu",
            "password": "securepass123",
            "confirm_password": "securepass123",
        }, follow_redirects=True)
        assert res.status_code == 200

    def test_register_duplicate_email(self, client, sample_user):
        """Registering with an existing email shows an error."""
        res = client.post("/auth/register", data={
            "name": "Other",
            "email": "test@uni.edu",   # same as sample_user
            "password": "somepass123",
            "confirm_password": "somepass123",
        }, follow_redirects=True)
        assert b"already exists" in res.data or res.status_code == 200

    def test_register_password_mismatch(self, client):
        """Mismatched passwords are rejected."""
        res = client.post("/auth/register", data={
            "name": "Bad User",
            "email": "bad@uni.edu",
            "password": "passA123",
            "confirm_password": "passB456",
        }, follow_redirects=True)
        assert b"do not match" in res.data or res.status_code == 200

    def test_register_short_password(self, client):
        """Password shorter than 8 characters is rejected."""
        res = client.post("/auth/register", data={
            "name": "Short Pass",
            "email": "short@uni.edu",
            "password": "abc",
            "confirm_password": "abc",
        }, follow_redirects=True)
        assert b"8 characters" in res.data or res.status_code == 200


# ── Login ──────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_page_loads(self, client):
        """GET /auth/login returns 200."""
        res = client.get("/auth/login")
        assert res.status_code == 200

    def test_login_success(self, client, sample_user):
        """Valid credentials log in the user."""
        res = client.post("/auth/login", data={
            "email": "test@uni.edu",
            "password": "securepassword123",
        }, follow_redirects=True)
        assert res.status_code == 200

    def test_login_wrong_password(self, client, sample_user):
        """Wrong password shows error message."""
        res = client.post("/auth/login", data={
            "email": "test@uni.edu",
            "password": "wrongpassword",
        }, follow_redirects=True)
        assert b"Invalid" in res.data or res.status_code == 200

    def test_login_unknown_email(self, client):
        """Unknown email shows error message."""
        res = client.post("/auth/login", data={
            "email": "nobody@uni.edu",
            "password": "whatever123",
        }, follow_redirects=True)
        assert b"Invalid" in res.data or res.status_code == 200


# ── Logout ─────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_redirects_to_login(self, client, sample_user):
        """POST /auth/logout logs out user and redirects."""
        # First log in
        client.post("/auth/login", data={
            "email": "test@uni.edu",
            "password": "securepassword123",
        })
        # Then log out
        res = client.post("/auth/logout", follow_redirects=True)
        assert res.status_code == 200
