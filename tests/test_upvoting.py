"""
Tests for Feature #4: Student Upvoting
Verifies upvote functionality, toggle behavior, database constraints,
privacy preservation, and display across student and admin views.
"""

import json
import pytest
from app import create_app, db
from app.models import User, Report, ReportVote
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
            name="Student Voter One",
            email="student_voter1@test.com",
            student_id="STU_VOTE_001",
            role="student",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def second_student_user(app):
    with app.app_context():
        user = User(
            name="Student Voter Two",
            email="student_voter2@test.com",
            student_id="STU_VOTE_002",
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
            name="Admin User",
            email="admin_test@test.com",
            role="admin",
        )
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def sample_report(app, student_user):
    with app.app_context():
        report = Report(
            title="Broken Water Cooler in Block 3",
            description="The water cooler on the 2nd floor is leaking and not cooling water.",
            category="Infrastructure",
            is_anonymous=False,
            user_id=student_user,
            location_label="Main Block",
            latitude=11.91411,
            longitude=79.63558,
        )
        db.session.add(report)
        db.session.commit()
        return report.id


@pytest.fixture
def sample_anonymous_report(app, student_user):
    with app.app_context():
        report = Report(
            title="Poor lighting behind girls hostel",
            description="Very dark pathway at night making students feel unsafe.",
            category="Safety",
            is_anonymous=True,
            user_id=student_user,
            location_label="Girls Hostel",
            latitude=11.91350,
            longitude=79.63500,
        )
        db.session.add(report)
        db.session.commit()
        return report.id


def test_upvote_and_toggle(client, student_user, sample_report):
    """Test upvoting a report and toggling it off."""
    # Login as student
    client.post("/auth/login", data={"email": "student_voter1@test.com", "password": "password123"})

    initial_report_count = Report.query.count()

    # 1. Upvote
    resp = client.post(
        f"/reports/{sample_report}/vote",
        data=json.dumps({"vote_type": "upvote"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["upvotes"] == 1
    assert data["has_upvoted"] is True
    assert data["report_id"] == sample_report

    # Ensure no duplicate report created
    assert Report.query.count() == initial_report_count

    # 2. Toggle off (upvote again)
    resp2 = client.post(
        f"/reports/{sample_report}/vote",
        data=json.dumps({"vote_type": "upvote"}),
        content_type="application/json",
    )
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2["upvotes"] == 0
    assert data2["has_upvoted"] is False


def test_multiple_students_upvoting(client, student_user, second_student_user, sample_report):
    """Test that multiple distinct students can upvote and count aggregates properly."""
    # First student upvotes
    client.post("/auth/login", data={"email": "student_voter1@test.com", "password": "password123"})
    client.post(
        f"/reports/{sample_report}/vote",
        data=json.dumps({"vote_type": "upvote"}),
        content_type="application/json",
    )
    client.post("/auth/logout")

    # Second student upvotes
    client.post("/auth/login", data={"email": "student_voter2@test.com", "password": "password123"})
    resp = client.post(
        f"/reports/{sample_report}/vote",
        data=json.dumps({"vote_type": "upvote"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["upvotes"] == 2
    assert data["has_upvoted"] is True

    # Check report detail page displays support button and count
    detail_resp = client.get(f"/reports/{sample_report}")
    assert detail_resp.status_code == 200
    html = detail_resp.data.decode("utf-8")
    assert "Support This Problem" in html or "Supported" in html
    assert "2 students support this problem" in html


def test_anonymous_report_upvote_and_privacy(client, second_student_user, admin_user, sample_anonymous_report):
    """Test upvoting an anonymous report preserves author anonymity and voter privacy."""
    # Second student logs in and upvotes anonymous report
    client.post("/auth/login", data={"email": "student_voter2@test.com", "password": "password123"}, follow_redirects=True)
    resp = client.post(
        f"/reports/{sample_anonymous_report}/vote",
        data=json.dumps({"vote_type": "upvote"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    client.post("/auth/logout", follow_redirects=True)

    # Login as admin
    client.post("/auth/admin-login", data={"email": "admin_test@test.com", "password": "adminpass123"}, follow_redirects=True)

    # Check Admin Report Detail
    admin_resp = client.get(f"/admin/reports/{sample_anonymous_report}")
    assert admin_resp.status_code == 200
    admin_html = admin_resp.data.decode("utf-8")

    # Admin should see upvote count / student support
    assert "1 Student Support" in admin_html or "1 student" in admin_html
    # Author identity must remain hidden
    assert "Anonymous Student" in admin_html
    assert "student_voter1@test.com" not in admin_html
    assert "STU_VOTE_001" not in admin_html
    # Voter identity must not be exposed
    assert "student_voter2@test.com" not in admin_html
    assert "Student Voter Two" not in admin_html


def test_admin_reports_list_shows_supports(client, sample_report, second_student_user, admin_user):
    """Test admin reports list shows the support count column and badge."""
    # Upvote sample report
    client.post("/auth/login", data={"email": "student_voter2@test.com", "password": "password123"})
    client.post(
        f"/reports/{sample_report}/vote",
        data=json.dumps({"vote_type": "upvote"}),
        content_type="application/json",
    )
    client.post("/auth/logout")

    # Admin checks reports list
    client.post("/auth/admin-login", data={"email": "admin_test@test.com", "password": "adminpass123"})
    list_resp = client.get("/admin/reports")
    assert list_resp.status_code == 200
    list_html = list_resp.data.decode("utf-8")
    assert "Supports" in list_html
    assert "👍" in list_html
