"""
Tests for CampusPulse AI – Anonymous Complaint Reporting Feature.
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
def student_user(app):
    """Create a sample student user."""
    with app.app_context():
        user = User(name="Alice Student", email="alice@uni.edu", role="student")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def admin_user(app):
    """Create a sample admin user."""
    with app.app_context():
        admin = User(name="Admin Officer", email="admin@uni.edu", role="admin")
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()
        return admin.id


class TestAnonymousComplaintReporting:
    def test_submit_anonymous_report(self, client, student_user, app):
        """Student submits an anonymous report: is_anonymous is True and linked to user_id."""
        client.post("/auth/login", data={"email": "alice@uni.edu", "password": "password123"})

        res = client.post("/reports/submit", data={
            "title": "Harassment near bus stop",
            "description": "Unsafe situation near the north campus bus stop.",
            "category": "Safety",
            "is_anonymous": "1",
            "campus_building": "smvec-main-gate",
            "location_label": "Main Campus Entrance & Security Gate",
        }, follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            rep = Report.query.filter_by(title="Harassment near bus stop").first()
            assert rep is not None
            assert rep.is_anonymous is True
            assert rep.user_id == student_user
            assert rep.author.email == "alice@uni.edu"

    def test_anonymous_report_hides_identity_from_admin(self, client, student_user, admin_user, app):
        """Admin viewing an anonymous report sees 'Anonymous Student' and no student name or email."""
        with app.app_context():
            rep = Report(
                title="Faulty elevator in science block",
                description="Elevator getting stuck between 2nd and 3rd floors.",
                category="Infrastructure",
                is_anonymous=True,
                user_id=student_user,
            )
            db.session.add(rep)
            db.session.commit()
            rep_id = rep.id

        # Log in as admin
        client.post("/auth/login", data={"email": "admin@uni.edu", "password": "adminpass123"})

        # Check admin report detail page
        detail_res = client.get(f"/admin/reports/{rep_id}")
        assert detail_res.status_code == 200
        assert b"Anonymous Report" in detail_res.data
        assert b"Anonymous Student" in detail_res.data
        assert b"Alice Student" not in detail_res.data
        assert b"alice@uni.edu" not in detail_res.data

        # Check admin reports list table
        list_res = client.get("/admin/reports")
        assert list_res.status_code == 200
        assert b"Anonymous Student" in list_res.data
        assert b"Alice Student" not in list_res.data

    def test_identified_report_shows_identity_to_admin(self, client, student_user, admin_user, app):
        """Admin viewing a non-anonymous report sees student's name, email, and Identified badge."""
        with app.app_context():
            rep = Report(
                title="Library AC not cooling",
                description="AC units in reading hall are blowing warm air.",
                category="Infrastructure",
                is_anonymous=False,
                user_id=student_user,
            )
            db.session.add(rep)
            db.session.commit()
            rep_id = rep.id

        # Log in as admin
        client.post("/auth/login", data={"email": "admin@uni.edu", "password": "adminpass123"})

        # Check admin report detail page
        detail_res = client.get(f"/admin/reports/{rep_id}")
        assert detail_res.status_code == 200
        assert b"Identified Report" in detail_res.data
        assert b"Alice Student" in detail_res.data
        assert b"alice@uni.edu" in detail_res.data

    def test_student_sees_anonymity_status_on_own_reports(self, client, student_user, app):
        """Student sees whether their own report is Anonymous or Identified."""
        with app.app_context():
            r_anon = Report(
                title="Anonymous issue",
                description="Details here.",
                category="Other",
                is_anonymous=True,
                user_id=student_user,
            )
            r_ident = Report(
                title="Identified issue",
                description="Details here.",
                category="Other",
                is_anonymous=False,
                user_id=student_user,
            )
            db.session.add_all([r_anon, r_ident])
            db.session.commit()
            anon_id = r_anon.id
            ident_id = r_ident.id

        client.post("/auth/login", data={"email": "alice@uni.edu", "password": "password123"})

        # Anonymous report detail
        res_anon = client.get(f"/reports/{anon_id}")
        assert res_anon.status_code == 200
        assert b"Anonymous Report" in res_anon.data

        # Identified report detail
        res_ident = client.get(f"/reports/{ident_id}")
        assert res_ident.status_code == 200
        assert b"Identified Report" in res_ident.data
