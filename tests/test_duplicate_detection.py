"""
Tests for CampusPulse AI – Feature #2 Duplicate Report Detection.
"""

import pytest
from app import create_app, db
from app.models import User, Report
from config import TestingConfig
from app.services.duplicate_service import compute_cosine_similarity, are_locations_matching, find_duplicate_report


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
    """Create a student user and log them in. Returns user id."""
    with app.app_context():
        user = User(name="Student Two", email="student2@uni.edu", role="student")
        user.set_password("studentpass123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/auth/login", data={
        "email": "student2@uni.edu",
        "password": "studentpass123",
    })
    return user_id


class TestDuplicateDetectionUnit:
    def test_text_similarity_high_on_similar_texts(self):
        s1 = "Broken street light near library. Extremely dark and unsafe."
        s2 = "Street light is broken outside central library, area is pitch dark."
        sim = compute_cosine_similarity(s1, s2)
        assert sim >= 0.40

    def test_text_similarity_zero_on_unrelated_texts(self):
        s1 = "Broken street light near library"
        s2 = "Canteen food quality issue with lunch menu"
        sim = compute_cosine_similarity(s1, s2)
        assert sim < 0.15

    def test_location_matching_building_and_coords(self):
        # Same building ID
        assert are_locations_matching(None, None, "smvec-central-library", "", None, None, "smvec-central-library", "")
        # Close coordinates (~20m)
        assert are_locations_matching(11.91411, 79.63558, None, None, 11.91415, 79.63560, None, None)
        # Far coordinates (>1km)
        assert not are_locations_matching(11.91411, 79.63558, None, None, 11.92500, 79.65000, None, None)


class TestDuplicateDetectionFlow:
    def test_duplicate_warning_on_similar_report_at_same_location(self, client, logged_in_student, app):
        # Create initial report
        with app.app_context():
            rep = Report(
                title="Broken street light near central library",
                description="The street light is completely damaged and dark at night near the library.",
                category="Safety",
                priority="High",
                status="Reported",
                location_label="Central Library & Digital Knowledge Centre",
                latitude=11.9142,
                longitude=79.6355,
                user_id=logged_in_student,
            )
            db.session.add(rep)
            db.session.commit()

        # Try submitting a very similar report via AJAX check endpoint
        check_res = client.post("/reports/check-duplicate", json={
            "title": "Street light broken at library",
            "description": "Street light outside central library is broken and area is dark",
            "category": "Safety",
            "campus_building": "smvec-central-library",
            "location_label": "Central Library & Digital Knowledge Centre",
            "latitude": 11.9142,
            "longitude": 79.6355,
        })
        assert check_res.status_code == 200
        data = check_res.get_json()
        assert data["has_duplicate"] is True
        assert "Broken street light near central library" in data["duplicate"]["title"]
        assert data["duplicate"]["similarity_pct"] >= 40
        assert data["duplicate"]["status"] == "Reported"

        # Try standard POST submit without confirm_duplicate -> triggers duplicate warning
        post_res = client.post("/reports/submit", data={
            "title": "Street light broken at library",
            "description": "Street light outside central library is broken and area is dark",
            "category": "Safety",
            "campus_building": "smvec-central-library",
            "location_label": "Central Library & Digital Knowledge Centre",
            "latitude": "11.9142",
            "longitude": "79.6355",
        })
        assert post_res.status_code == 200
        # Warning appears in rendered HTML
        assert b"A similar problem has already been reported at this location." in post_res.data
        assert b"Submit Anyway" in post_res.data
        assert b"View Existing Report" in post_res.data

        # Verify second report was NOT created yet
        with app.app_context():
            count = Report.query.count()
            assert count == 1

    def test_submit_anyway_creates_report(self, client, logged_in_student, app):
        # Create initial report
        with app.app_context():
            rep = Report(
                title="Broken street light near central library",
                description="The street light is completely damaged and dark at night near the library.",
                category="Safety",
                priority="High",
                status="Reported",
                location_label="Central Library & Digital Knowledge Centre",
                latitude=11.9142,
                longitude=79.6355,
                user_id=logged_in_student,
            )
            db.session.add(rep)
            db.session.commit()

        # Submit with confirm_duplicate=1
        post_res = client.post("/reports/submit", data={
            "title": "Street light broken at library",
            "description": "Street light outside central library is broken and area is dark",
            "category": "Safety",
            "campus_building": "smvec-central-library",
            "location_label": "Central Library & Digital Knowledge Centre",
            "latitude": "11.9142",
            "longitude": "79.6355",
            "confirm_duplicate": "1",
        }, follow_redirects=True)
        assert post_res.status_code == 200

        # Verify both reports now exist
        with app.app_context():
            count = Report.query.count()
            assert count == 2

    def test_distinct_problem_at_different_location_not_blocked(self, client, logged_in_student, app):
        # Create initial report at Library
        with app.app_context():
            rep = Report(
                title="Broken street light near central library",
                description="The street light is completely damaged and dark at night near the library.",
                category="Safety",
                location_label="Central Library",
                latitude=11.9142,
                longitude=79.6355,
                user_id=logged_in_student,
            )
            db.session.add(rep)
            db.session.commit()

        # Submit distinct report at Sports Ground
        post_res = client.post("/reports/submit", data={
            "title": "Football goalpost broken",
            "description": "The net and post at sports ground need immediate repair.",
            "category": "Infrastructure",
            "campus_building": "smvec-sports-ground",
            "location_label": "Main Sports Ground",
            "latitude": "11.9155",
            "longitude": "79.6375",
        }, follow_redirects=True)
        assert post_res.status_code == 200

        # Successfully created directly without duplicate block
        with app.app_context():
            new_rep = Report.query.filter_by(title="Football goalpost broken").first()
            assert new_rep is not None
