"""
CampusPulse AI – Step 16 Admin Login Verification Suite
Tests:
1. Admin Login Page rendering & /admin/login alias redirect
2. Admin Portal link present on Student Login page
3. Bad admin password rejection
4. Student rejection from admin portal
5. Valid admin login to dashboard
6. Admin access to Admin Dashboard, All Reports, Report Details, and Status Updates
7. Student 403 Forbidden protection on all admin routes
8. Unauthenticated redirect to /auth/admin-login
"""

from app import create_app, db
from app.models import User, Report


def setup_data():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(email="admin@campuspulse.ai").first()
        student = User.query.filter_by(email="test@example.com").first()
        assert admin is not None, "Admin user must exist"
        assert student is not None, "Student user must exist"
        student.set_password("StudentPassword@123")
        admin.set_password("AdminPassword@123")
        db.session.commit()


def test_1_admin_page():
    app = create_app()
    client = app.test_client()
    resp_page = client.get("/auth/admin-login")
    assert resp_page.status_code == 200
    assert b"Admin" in resp_page.data
    assert b"admin-login-form" in resp_page.data

    resp_alias = client.get("/admin/login")
    assert resp_alias.status_code == 302
    assert "/auth/admin-login" in resp_alias.headers.get("Location", "")
    print("[PASS] 1. Admin login page and /admin/login alias redirect")


def test_2_student_page_link():
    app = create_app()
    client = app.test_client()
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"/auth/admin-login" in resp.data
    print("[PASS] 2. Student login page has admin portal link")


def test_3_bad_credentials():
    app = create_app()
    client = app.test_client()
    resp = client.post("/auth/admin-login", data={"email": "admin@campuspulse.ai", "password": "WrongPassword"}, follow_redirects=True)
    assert b"Invalid administrator credentials" in resp.data
    print("[PASS] 3. Invalid admin credentials rejection")


def test_4_student_rejected_on_admin():
    app = create_app()
    client = app.test_client()
    resp = client.post("/auth/admin-login", data={"email": "test@example.com", "password": "StudentPassword@123"}, follow_redirects=True)
    assert b"Access denied" in resp.data
    print("[PASS] 4. Student rejected from admin portal")


def test_5_valid_admin_login():
    app = create_app()
    client = app.test_client()
    resp = client.post("/auth/admin-login", data={"email": "admin@campuspulse.ai", "password": "AdminPassword@123"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Admin Dashboard" in resp.data or b"Recent Reports" in resp.data
    print("[PASS] 5. Valid admin login to dashboard")


def test_6_admin_access_and_status_update():
    app = create_app()
    with app.app_context():
        report = Report.query.first()
        report_id = report.id

    client = app.test_client()
    client.post("/auth/admin-login", data={"email": "admin@campuspulse.ai", "password": "AdminPassword@123"}, follow_redirects=True)

    resp_rep = client.get("/admin/reports")
    assert resp_rep.status_code == 200
    assert b"All Reports" in resp_rep.data

    resp_det = client.get(f"/admin/reports/{report_id}")
    assert resp_det.status_code == 200
    assert b"Update Status" in resp_det.data

    resp_status = client.patch(f"/admin/reports/{report_id}/status", json={"status": "In Progress", "note": "Admin step verification"})
    assert resp_status.status_code == 200
    assert resp_status.get_json().get("success") is True
    print("[PASS] 6. Admin access to Dashboard, All Reports, Report Details, and Status Updates")


def test_7_student_blocked():
    app = create_app()
    with app.app_context():
        report = Report.query.first()
        report_id = report.id

    client = app.test_client()
    client.post("/auth/login", data={"email": "test@example.com", "password": "StudentPassword@123"}, follow_redirects=True)

    r_dash = client.get("/admin/")
    assert r_dash.status_code == 403, f"Expected 403, got {r_dash.status_code}"

    r_rep = client.get("/admin/reports")
    assert r_rep.status_code == 403, f"Expected 403, got {r_rep.status_code}"

    r_det = client.get(f"/admin/reports/{report_id}")
    assert r_det.status_code == 403, f"Expected 403, got {r_det.status_code}"

    r_patch = client.patch(f"/admin/reports/{report_id}/status", json={"status": "Resolved"})
    assert r_patch.status_code == 403, f"Expected 403, got {r_patch.status_code}"
    print("[PASS] 7. Student blocked from all admin routes (403 Forbidden)")


def test_8_unauthenticated_redirect():
    app = create_app()
    client = app.test_client()
    r_unauth = client.get("/admin/")
    assert r_unauth.status_code == 302
    assert "/auth/login" in r_unauth.headers.get("Location", "") or "/auth/admin-login" in r_unauth.headers.get("Location", "")

    r_admin_login = client.get("/admin/login")
    assert r_admin_login.status_code == 302
    assert "/auth/admin-login" in r_admin_login.headers.get("Location", "")
    print("[PASS] 8. Unauthenticated redirects to login portal")


def run_tests():
    setup_data()
    test_1_admin_page()
    test_2_student_page_link()
    test_3_bad_credentials()
    test_4_student_rejected_on_admin()
    test_5_valid_admin_login()
    test_6_admin_access_and_status_update()
    test_7_student_blocked()
    test_8_unauthenticated_redirect()

    print("\n" + "=" * 60)
    print("ALL 8 STEP 16 ADMIN LOGIN TESTS PASSED WITH 0 ERRORS!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
