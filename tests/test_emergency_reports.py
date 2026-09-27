"""
Tests for Feature #5: Emergency / Safety Reports
Verifies creation, storage, filtering, badge display, and privacy protection
for emergency/safety campus problem reports.
"""

import json
import pytest
from app import create_app, db
from app.models import User, Report
from config import TestingConfig


@pytest.fixture
def app():
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def student_user(app):
    with app.app_context():
        user = User(
            name="John Student",
            email="john_student@test.com",
            student_id="STU_EMERG_001",
            role="student",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = User(
            name="Campus Safety Admin",
            email="safety_admin@test.com",
            role="admin",
        )
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()
        return admin.id


def test_submit_emergency_report(client, student_user, app):
    """Test that a student can submit an emergency/safety report."""
    client.post("/auth/login", data={"email": "john_student@test.com", "password": "password123"}, follow_redirects=True)

    resp = client.post("/reports/submit", data={
        "title": "Exposed High Voltage Wire Near Library Entrance",
        "description": "Sparking exposed cable dangling across the main walkway near the central library.",
        "category": "Electricity",
        "campus_building": "central_library",
        "is_emergency": "1",
    }, follow_redirects=True)

    assert resp.status_code == 200

    with app.app_context():
        report = Report.query.filter_by(title="Exposed High Voltage Wire Near Library Entrance").first()
        assert report is not None
        assert report.is_emergency is True
        assert report.user_id == student_user
        assert report.category == "Electricity"

    # Verify badge on student report detail page
    detail_resp = client.get(f"/reports/{report.id}")
    assert detail_resp.status_code == 200
    html = detail_resp.data.decode("utf-8")
    assert "Emergency" in html
    assert "Flagged as Campus Emergency" in html


def test_submit_standard_non_emergency_report(client, student_user, app):
    """Test that standard reports default to is_emergency=False."""
    client.post("/auth/login", data={"email": "john_student@test.com", "password": "password123"}, follow_redirects=True)

    resp = client.post("/reports/submit", data={
        "title": "Slow Wi-Fi in Mechanical Block",
        "description": "The internet connection is intermittently slow during afternoon lab sessions.",
        "category": "Internet",
        "campus_building": "mech_block",
        # is_emergency not supplied
    }, follow_redirects=True)

    assert resp.status_code == 200

    with app.app_context():
        report = Report.query.filter_by(title="Slow Wi-Fi in Mechanical Block").first()
        assert report is not None
        assert report.is_emergency is False


def test_admin_dashboard_and_emergency_filtering(client, student_user, admin_user, app):
    """Test admin dashboard statistics and emergency filter on reports list."""
    with app.app_context():
        # 1 Emergency report
        r_emerg = Report(
            title="Fire Extinguisher Broken in Science Lab",
            description="Pressure gauge reads empty in the chemistry lab corridor.",
            category="Safety",
            is_emergency=True,
            is_anonymous=False,
            user_id=student_user,
        )
        # 1 Standard report
        r_std = Report(
            title="Desks missing in Room 204",
            description="Two chairs are needed in the second floor classroom.",
            category="Infrastructure",
            is_emergency=False,
            is_anonymous=False,
            user_id=student_user,
        )
        db.session.add_all([r_emerg, r_std])
        db.session.commit()
        emerg_id = r_emerg.id
        std_id = r_std.id

    # Admin logs in
    client.post("/auth/admin-login", data={"email": "safety_admin@test.com", "password": "adminpass123"}, follow_redirects=True)

    # 1. Admin Dashboard shows Emergency KPI
    dash_resp = client.get("/admin/")
    assert dash_resp.status_code == 200
    dash_html = dash_resp.data.decode("utf-8")
    assert "Emergency Reports" in dash_html

    # 2. Filter: Emergency Only
    resp_emerg_only = client.get("/admin/reports?emergency=true")
    assert resp_emerg_only.status_code == 200
    html_emerg = resp_emerg_only.data.decode("utf-8")
    assert "Fire Extinguisher Broken in Science Lab" in html_emerg
    assert "Desks missing in Room 204" not in html_emerg

    # 3. Filter: Non-Emergency Only
    resp_non_emerg = client.get("/admin/reports?emergency=false")
    assert resp_non_emerg.status_code == 200
    html_non_emerg = resp_non_emerg.data.decode("utf-8")
    assert "Desks missing in Room 204" in html_non_emerg
    assert "Fire Extinguisher Broken in Science Lab" not in html_non_emerg

    # 4. Filter: All Reports
    resp_all = client.get("/admin/reports")
    assert resp_all.status_code == 200
    html_all = resp_all.data.decode("utf-8")
    assert "Fire Extinguisher Broken in Science Lab" in html_all
    assert "Desks missing in Room 204" in html_all


def test_anonymous_emergency_report_privacy(client, student_user, admin_user, app):
    """Test that an emergency report submitted anonymously never reveals student identity to admin."""
    with app.app_context():
        r_anon_emerg = Report(
            title="Gas Odor Detected near Cafeteria Kitchen",
            description="Strong smell of LPG gas near the back entrance of the canteen.",
            category="Safety",
            is_emergency=True,
            is_anonymous=True,
            user_id=student_user,
        )
        db.session.add(r_anon_emerg)
        db.session.commit()
        rep_id = r_anon_emerg.id

    # Admin logs in
    client.post("/auth/admin-login", data={"email": "safety_admin@test.com", "password": "adminpass123"}, follow_redirects=True)

    # Admin views the report detail
    resp = client.get(f"/admin/reports/{rep_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert "Emergency Report" in html
    assert "Anonymous Student" in html
    assert "john_student@test.com" not in html
    assert "STU_EMERG_001" not in html
    assert "John Student" not in html


def test_map_data_includes_emergency_flag(client, student_user, app):
    """Test that /reports/map-data payload includes is_emergency boolean for map markers."""
    with app.app_context():
        report = Report(
            title="Tree Branch Fallen on Pathway",
            description="Heavy branch blocking vehicle access path.",
            category="Safety",
            is_emergency=True,
            latitude=11.91411,
            longitude=79.63558,
            user_id=student_user,
        )
        db.session.add(report)
        db.session.commit()

    resp = client.get("/reports/map-data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    matching = [r for r in data if r["title"] == "Tree Branch Fallen on Pathway"]
    assert len(matching) == 1
    assert matching[0]["is_emergency"] is True
