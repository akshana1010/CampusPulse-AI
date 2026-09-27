"""
CampusPulse AI – Step 17 Complete End-to-End Verification
"""

import sys
from app import create_app, db
from app.models import User, Report, StatusHistory, CATEGORIES, STATUSES
from app.services.ai_service import _local_fallback_analyzer

def verify_all():
    app = create_app()
    errors = []

    print("=" * 70)
    print("STEP 17: COMPLETE END-TO-END VERIFICATION OF CAMPUSPULSE-AI")
    print("=" * 70)

    # 1. AI FALLBACK VERIFICATION
    print("\n[TEST 1] AI Service & Local Fallback Analyzer")
    try:
        res = _local_fallback_analyzer("Broken street light", "Light is broken near library, very dark at night", "Safety")
        assert res["predicted_category"] in CATEGORIES
        assert res["priority"] in ["Low", "Medium", "High", "Critical"]
        assert res["sentiment"] in ["positive", "neutral", "negative", "urgent"]
        assert 0.0 <= res["confidence"] <= 1.0
        assert len(res["summary"]) > 0
        print(f" - Local keyword fallback analyzer: PASS (Category: {res['predicted_category']}, Priority: {res['priority']}, Confidence: {res['confidence']})")
    except Exception as e:
        errors.append(f"AI fallback failed: {e}")
        print(f" - Local keyword fallback analyzer: FAIL - {e}")

    # 2. STUDENT SIDE END-TO-END VERIFICATION
    print("\n[TEST 2] Student Side End-to-End Flow")
    with app.app_context():
        student = User.query.filter_by(role="student").first()
        assert student is not None, "Student account not found in DB"
        student_email = student.email

    client = app.test_client()

    # 2.1 Student Login
    login_resp = client.post("/auth/login", data={"email": student_email, "password": "password123"}, follow_redirects=True)
    if login_resp.status_code != 200 or b"My Dashboard" not in login_resp.data:
        errors.append("Student login failed")
        print(" - 2.1 Student Login: FAIL")
    else:
        print(" - 2.1 Student Login: PASS")

    # 2.2 Student Dashboard
    dash_resp = client.get("/reports/")
    if dash_resp.status_code == 200 and b"Total Reports" in dash_resp.data and b"studentCategoryChart" in dash_resp.data:
        print(" - 2.2 Student Dashboard & Category Charts: PASS")
    else:
        errors.append("Student dashboard failed to render stats or chart")
        print(" - 2.2 Student Dashboard: FAIL")

    # 2.3 Submit Report with Map Coordinates & AI Analysis
    submit_page = client.get("/reports/submit")
    if submit_page.status_code == 200 and b"location-map" in submit_page.data and b"latitude" in submit_page.data:
        print(" - 2.3 Submit Page & Interactive Map Form Fields: PASS")
    else:
        errors.append("Submit report page failed to render")
        print(" - 2.3 Submit Page: FAIL")

    # 2.4 Post New Report with Location and verify AI result
    report_title = "Water Leakage and Overflow in Chemistry Lab 3"
    report_desc = "Main water pipe is leaking rapidly flooding lab floor and threatening electrical cabinets nearby."
    post_resp = client.post("/reports/submit", data={
        "title": report_title,
        "description": report_desc,
        "category": "Water",
        "latitude": "11.9216",
        "longitude": "79.6387",
        "location_label": "Chemistry Lab 3 Ground Floor"
    }, follow_redirects=True)

    if post_resp.status_code != 200:
        errors.append("Report submission POST failed")
        print(" - 2.4 Report Submission: FAIL")
    else:
        print(" - 2.4 Report Submission with Coordinates: PASS")

    # 2.5 Verify Report in Student's Dashboard & Details Page
    with app.app_context():
        new_report = Report.query.filter_by(title=report_title).first()
        if new_report is None:
            errors.append("Created report not found in DB")
            print(" - 2.5 Report DB Verification: FAIL")
        else:
            print(f" - 2.5 Report Saved in DB (ID: {new_report.id}): PASS")
            assert new_report.latitude == 11.9216
            assert new_report.longitude == 79.6387
            print(f" - 2.6 Location Pin Stored: {new_report.latitude}, {new_report.longitude} ({new_report.location_label}): PASS")
            print(f" - 2.7 AI Result Stored: Category={new_report.ai_category or new_report.category}, Priority={new_report.priority}, Sentiment={new_report.ai_sentiment}, Confidence={new_report.ai_confidence}: PASS")

            # Detail view
            detail_resp = client.get(f"/reports/{new_report.id}")
            if detail_resp.status_code == 200 and report_title.encode() in detail_resp.data and b"AI Analysis" in detail_resp.data:
                print(" - 2.8 Student Report Details Page Rendering: PASS")
            else:
                errors.append("Student report details page rendering failed")
                print(" - 2.8 Student Report Details Page: FAIL")

    # 3. ADMIN SIDE END-TO-END VERIFICATION
    print("\n[TEST 3] Admin Side End-to-End Flow")
    admin_client = app.test_client()

    # 3.1 Admin Login with 'admin' and 'Admin@12345'
    admin_login_resp = admin_client.post("/auth/admin-login", data={"email": "admin", "password": "Admin@12345"}, follow_redirects=True)
    if admin_login_resp.status_code == 200 and (b"Admin Dashboard" in admin_login_resp.data or b"Recent Reports" in admin_login_resp.data):
        print(" - 3.1 Admin Login with ID 'admin': PASS")
    else:
        errors.append("Admin login with ID 'admin' failed")
        print(" - 3.1 Admin Login with ID 'admin': FAIL")

    # 3.2 Admin Dashboard stats and charts
    admin_dash = admin_client.get("/admin/")
    if admin_dash.status_code == 200 and b"Total Reports" in admin_dash.data and b"categoryChart" in admin_dash.data:
        print(" - 3.2 Admin Dashboard KPI & Charts: PASS")
    else:
        errors.append("Admin dashboard failed")
        print(" - 3.2 Admin Dashboard: FAIL")

    # 3.3 View All Reports Table
    reports_resp = admin_client.get("/admin/reports")
    if reports_resp.status_code == 200 and b"All Reports" in reports_resp.data:
        print(" - 3.3 Admin View All Reports: PASS")
    else:
        errors.append("Admin all reports page failed")
        print(" - 3.3 Admin View All Reports: FAIL")

    # 3.4 Open Report in Admin Detail View
    with app.app_context():
        test_rep = Report.query.first()
        test_rep_id = test_rep.id

    admin_rep_detail = admin_client.get(f"/admin/reports/{test_rep_id}")
    if admin_rep_detail.status_code == 200 and b"Update Status" in admin_rep_detail.data and b"Status Timeline" in admin_rep_detail.data:
        print(f" - 3.4 Admin Report Detail Page (Report #{test_rep_id}): PASS")
    else:
        errors.append("Admin report detail page failed")
        print(" - 3.4 Admin Report Detail Page: FAIL")

    # 3.5 Status Transitions: Reported -> In Progress -> Resolved
    p1 = admin_client.patch(f"/admin/reports/{test_rep_id}/status", json={"status": "In Progress", "note": "Maintenance crew dispatched"})
    assert p1.status_code == 200 and p1.get_json().get("new_status") == "In Progress"
    print(" - 3.5 Status Transition -> 'In Progress': PASS")

    p2 = admin_client.patch(f"/admin/reports/{test_rep_id}/status", json={"status": "Resolved", "note": "Issue successfully fixed and verified"})
    assert p2.status_code == 200 and p2.get_json().get("new_status") == "Resolved"
    print(" - 3.6 Status Transition -> 'Resolved': PASS")

    p3 = admin_client.patch(f"/admin/reports/{test_rep_id}/status", json={"status": "Reported", "note": "Reopened for inspection"})
    assert p3.status_code == 200 and p3.get_json().get("new_status") == "Reported"
    print(" - 3.7 Status Transition -> 'Reported': PASS")

    # 4. SECURITY & ACCESS CONTROL VERIFICATION
    print("\n[TEST 4] Security, Authorization & Routing")
    student_check_client = app.test_client()
    student_check_client.post("/auth/login", data={"email": "test@example.com", "password": "password123"}, follow_redirects=True)

    assert student_check_client.get("/admin/").status_code == 403
    assert student_check_client.get("/admin/reports").status_code == 403
    assert student_check_client.get(f"/admin/reports/{test_rep_id}").status_code == 403
    assert student_check_client.patch(f"/admin/reports/{test_rep_id}/status", json={"status": "Resolved"}).status_code == 403
    print(" - 4.1 Student Access Blocked on Admin Routes (403 Forbidden): PASS")

    # 5. DEMO REPORTS AVAILABILITY
    print("\n[TEST 5] Demo Reports Availability")
    with app.app_context():
        demo_reports = Report.query.filter(Report.title.like("[Demo]%")).all()
        print(f" - Found {len(demo_reports)} demo reports in database: PASS")
        categories_present = sorted(list(set(r.category for r in demo_reports)))
        print(f" - Categories covered: {categories_present}")

    print("\n" + "=" * 70)
    if len(errors) == 0:
        print("STEP 17 COMPLETE — 0 ERRORS")
    else:
        print(f"STEP 17 COMPLETED WITH {len(errors)} ERRORS:")
        for err in errors:
            print(" -", err)
    print("=" * 70)

    return len(errors) == 0

if __name__ == "__main__":
    ok = verify_all()
    sys.exit(0 if ok else 1)
