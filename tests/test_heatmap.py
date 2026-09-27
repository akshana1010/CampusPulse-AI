"""
Tests for CampusPulse AI – Feature #3 Campus Problem Heatmap.
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
    """Create a student user and log them in."""
    with app.app_context():
        user = User(name="Student Heatmap", email="student_heat@uni.edu", role="student")
        user.set_password("studentpass123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/auth/login", data={
        "email": "student_heat@uni.edu",
        "password": "studentpass123",
    })
    return user_id


class TestCampusProblemHeatmap:
    def test_campus_map_page_contains_heatmap_elements(self, client, logged_in_student):
        """Verify the campus map page includes heatmap toggle button, legend, and leaflet-heat assets."""
        res = client.get("/campus-map", follow_redirects=True)
        assert res.status_code == 200
        assert b"toggle-heatmap-btn" in res.data
        assert b"Heatmap: OFF" in res.data or b"Problem Heatmap" in res.data
        assert b"leaflet-heat.js" in res.data
        assert b"heatmap-legend-section" in res.data
        assert b"campus-map" in res.data

        # Also test direct route /reports/campus-map
        res_direct = client.get("/reports/campus-map")
        assert res_direct.status_code == 200
        assert b"toggle-heatmap-btn" in res_direct.data

    def test_map_data_includes_active_and_resolved_attributes(self, client, logged_in_student, app):
        """Verify /reports/map-data provides complete report coordinates and priority weights."""
        with app.app_context():
            # Add active critical report
            r1 = Report(
                title="Critical Power Outage in CSE Block",
                description="Power failure in server rooms.",
                category="Electricity",
                priority="Critical",
                status="Reported",
                location_label="CSE Academic Block",
                latitude=11.9145,
                longitude=79.6358,
                user_id=logged_in_student,
            )
            # Add resolved report
            r2 = Report(
                title="Fixed Water Tap in Admin Block",
                description="Water tap fixed.",
                category="Water",
                priority="Low",
                status="Resolved",
                location_label="Admin Block",
                latitude=11.9140,
                longitude=79.6350,
                user_id=logged_in_student,
            )
            db.session.add_all([r1, r2])
            db.session.commit()

        res = client.get("/reports/map-data")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2

        active_rep = next(r for r in data if r["priority"] == "Critical")
        assert active_rep["status"] == "Reported"
        assert active_rep["latitude"] == 11.9145
        assert active_rep["longitude"] == 79.6358

        resolved_rep = next(r for r in data if r["status"] == "Resolved")
        assert resolved_rep["priority"] == "Low"
