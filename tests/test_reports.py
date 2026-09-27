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
        """Valid report submission creates a DB record with AI analysis and suggested solution."""
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
            assert report.ai_suggested_solution is not None
            assert len(report.ai_suggested_solution) > 10


# ── Detail ─────────────────────────────────────────────────────────────────────

class TestReportDetail:
    def test_detail_own_report(self, client, logged_in_student, sample_report):
        """Student can view their own report detail including AI suggested solution."""
        res = client.get(f"/reports/{sample_report}")
        assert res.status_code == 200
        assert b"AI Suggested Solution" in res.data or b"Description" in res.data

    def test_ai_fallback_solutions(self, app):
        """Test that local fallback generates sensible solutions for all categories."""
        from app.services.ai_service import _local_fallback_analyzer, get_fallback_solution, VALID_CATEGORIES
        for cat in VALID_CATEGORIES:
            sol = get_fallback_solution(cat, f"Issue with {cat}", f"Detailed description for {cat}")
            assert sol is not None and len(sol) > 15
            res = _local_fallback_analyzer(f"Issue with {cat}", f"Detailed description for {cat}", cat)
            assert "suggested_solution" in res
            assert len(res["suggested_solution"]) > 15

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

    def test_campus_map_page_authenticated(self, client, logged_in_student):
        """GET /campus-map and /reports/campus-map load for logged-in users."""
        res_alias = client.get("/campus-map", follow_redirects=True)
        assert res_alias.status_code == 200
        assert b"SMVEC Campus Map" in res_alias.data

        res_direct = client.get("/reports/campus-map")
        assert res_direct.status_code == 200
        assert b"SMVEC Campus Map" in res_direct.data

    def test_404_error_page_renders_safely(self, client, logged_in_student):
        """404 error page renders safely without crashing on request.endpoint check."""
        res = client.get("/nonexistent-page-xyz")
        assert res.status_code == 404
        assert b"Page Not Found" in res.data

    def test_submit_report_with_campus_building(self, client, logged_in_student):
        """Submitting a report with a campus building automatically sets coordinates and shows on map."""
        import json
        res = client.post("/reports/submit", data={
            "title": "Wi-Fi not working in CSE Lab 3",
            "description": "Access point 4 in CSE Block 2nd floor is completely unresponsive.",
            "category": "Internet",
            "campus_building": "smvec-cse-it-block"
        }, follow_redirects=True)
        assert res.status_code == 200

        # Verify in map data
        map_res = client.get("/reports/map-data")
        data = json.loads(map_res.data)
        cse_reports = [r for r in data if "Wi-Fi not working in CSE Lab 3" in r["title"]]
        assert len(cse_reports) == 1
        assert cse_reports[0]["location_label"] == "CSE, IT & AI-DS Academic Block"
        assert abs(cse_reports[0]["latitude"] - 11.91440) < 0.001
        assert abs(cse_reports[0]["longitude"] - 79.63665) < 0.001

    def test_multiple_reports_at_same_building(self, client, logged_in_student):
        """Multiple reports at the same building are stored and returned in map data."""
        import json
        client.post("/reports/submit", data={
            "title": "Water cooler leaking in Admin Block",
            "description": "Ground floor water dispenser near reception is overflowing.",
            "category": "Water",
            "campus_building": "smvec-admin-block"
        }, follow_redirects=True)

        client.post("/reports/submit", data={
            "title": "Power socket broken in Admin Office 2",
            "description": "Switchboard sparking near counter 3.",
            "category": "Electricity",
            "campus_building": "smvec-admin-block"
        }, follow_redirects=True)

        map_res = client.get("/reports/map-data")
        data = json.loads(map_res.data)
        admin_reports = [r for r in data if r.get("location_label") == "Main Administrative Block & Admissions"]
        assert len(admin_reports) >= 2


