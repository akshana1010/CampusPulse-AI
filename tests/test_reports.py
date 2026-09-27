"""
Tests for CampusPulse AI – Report routes.
Run with: pytest tests/test_reports.py -v
"""

import pytest
from app import create_app, db
from app.models import User, Report
from config import TestingConfig


@pytest.fixture
def app():
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
def logged_in_student(client, app):
    """Create a student user and log them in. Returns the user."""
    with app.app_context():
        user = User(name="Student One", email="student@uni.edu", role="student")
        user.set_password("studentpass123")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={
        "email": "student@uni.edu",
        "password": "studentpass123",
    })
    return user


@pytest.fixture
def sample_report(app, logged_in_student):
    """Create a sample report in the DB."""
    with app.app_context():
        user = User.query.filter_by(email="student@uni.edu").first()
        report = Report(
            title="Broken Light",
            description="The street light near Block A is broken.",
            category="Electricity",
            priority="Medium",
            status="Reported",
            user_id=user.id,
        )
        db.session.add(report)
        db.session.commit()
        return report.id


# ── Dashboard ──────────────────────────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_requires_login(self, client):
        """Unauthenticated access to /reports/ redirects to login."""
        res = client.get("/reports/", follow_redirects=False)
        assert res.status_code in (302, 301)

    def test_dashboard_accessible_when_logged_in(self, client, logged_in_student):
        """Logged-in student can access dashboard."""
        res = client.get("/reports/")
        assert res.status_code == 200


# ── Submit ─────────────────────────────────────────────────────────────────────

class TestSubmitReport:
    def test_submit_page_loads(self, client, logged_in_student):
        """GET /reports/submit returns 200 for logged-in student."""
        res = client.get("/reports/submit")
        assert res.status_code == 200

    def test_submit_missing_required_fields(self, client, logged_in_student):
        """Submission without title or description stays on form."""
        res = client.post("/reports/submit", data={
            "category": "Safety",
        }, follow_redirects=True)
        assert res.status_code == 200

    def test_submit_valid_report(self, client, logged_in_student, app):
        """Valid report submission creates a DB record."""
        res = client.post("/reports/submit", data={
            "title": "Pothole near Cafeteria",
            "description": "Large pothole causing hazard for cyclists.",
            "category": "Infrastructure",
        }, follow_redirects=True)
        assert res.status_code == 200
        with app.app_context():
            report = Report.query.filter_by(title="Pothole near Cafeteria").first()
            assert report is not None
            assert report.category == "Infrastructure"


# ── Detail ─────────────────────────────────────────────────────────────────────

class TestReportDetail:
    def test_detail_own_report(self, client, logged_in_student, sample_report):
        """Student can view their own report detail."""
        res = client.get(f"/reports/{sample_report}")
        assert res.status_code == 200

    def test_detail_nonexistent_report(self, client, logged_in_student):
        """Accessing a non-existent report returns 404."""
        res = client.get("/reports/99999")
        assert res.status_code == 404


# ── Map Data ───────────────────────────────────────────────────────────────────

class TestMapData:
    def test_map_data_public(self, client):
        """Map data endpoint is publicly accessible (no login required)."""
        res = client.get("/reports/map-data")
        assert res.status_code == 200
        assert res.content_type == "application/json"

    def test_map_data_returns_list(self, client):
        """Map data returns a JSON list."""
        import json
        res = client.get("/reports/map-data")
        data = json.loads(res.data)
        assert isinstance(data, list)
