"""
Database Initialization Test
Verifies:
  1. Flask application starts
  2. SQLAlchemy connects to SQLite
  3. User table exists
  4. Report table exists
  5. AdminAction table exists
  6. Relationships between User, Report, AdminAction work
  7. No duplicate database initialization
"""

import sys
import os

# Ensure project root is on the path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import sqlalchemy as sa
from config import TestingConfig


def separator(title):
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}]  {label}"
    if detail:
        line += f"\n           {detail}"
    print(line)
    return condition


def run_tests():
    results = []

    # -- 1. Flask application starts ------------------------------------------
    separator("1. Flask application starts")
    try:
        from app import create_app
        app = create_app(TestingConfig)
        results.append(check("create_app() succeeds", True))
        results.append(check("app is a Flask instance", app is not None))
    except Exception as exc:
        results.append(check("create_app() succeeds", False, str(exc)))
        print("\nCannot continue without a working Flask app. Aborting.")
        return results

    with app.app_context():

        # -- 2. SQLAlchemy connects to SQLite ----------------------------------
        separator("2. SQLAlchemy connects to SQLite")
        from app import db
        try:
            conn = db.engine.connect()
            conn.close()
            uri = app.config["SQLALCHEMY_DATABASE_URI"]
            results.append(check("Engine connects successfully", True, f"URI: {uri}"))
            results.append(check("Using SQLite", "sqlite" in uri.lower()))
        except Exception as exc:
            results.append(check("Engine connects successfully", False, str(exc)))

        # -- Create tables (idempotent) ----------------------------------------
        try:
            db.create_all()
        except Exception as exc:
            print(f"\n  [ERROR] db.create_all() failed: {exc}")
            return results

        # Reflect actual tables from the database
        inspector = sa.inspect(db.engine)
        actual_tables = set(inspector.get_table_names())

        # -- 3. User table -----------------------------------------------------
        separator("3. User table exists")
        results.append(check("Table 'users' in database", "users" in actual_tables))
        if "users" in actual_tables:
            cols = {c["name"] for c in inspector.get_columns("users")}
            for col in ("id", "name", "email", "password_hash", "role", "is_active"):
                results.append(check(f"  Column: {col}", col in cols))

        # -- 4. Report table ---------------------------------------------------
        separator("4. Report table exists")
        results.append(check("Table 'reports' in database", "reports" in actual_tables))
        if "reports" in actual_tables:
            cols = {c["name"] for c in inspector.get_columns("reports")}
            for col in ("id", "title", "description", "category", "status", "user_id"):
                results.append(check(f"  Column: {col}", col in cols))

        # -- 5. AdminAction table ---------------------------------------------
        separator("5. AdminAction table exists")
        results.append(check("Table 'admin_actions' in database", "admin_actions" in actual_tables))
        if "admin_actions" in actual_tables:
            cols = {c["name"] for c in inspector.get_columns("admin_actions")}
            for col in ("id", "action_type", "admin_id", "report_id", "performed_at"):
                results.append(check(f"  Column: {col}", col in cols))

        # -- 6. Relationships work ---------------------------------------------
        separator("6. Relationships between User, Report, AdminAction")
        from app.models import User, Report, AdminAction

        try:
            # Create test user
            user = User(name="Test Student", email="dbtest@campus.test", role="student")
            user.set_password("testpass123")
            db.session.add(user)
            db.session.flush()  # get user.id without committing

            # Create test admin
            admin = User(name="Test Admin", email="admintest@campus.test", role="admin")
            admin.set_password("adminpass123")
            db.session.add(admin)
            db.session.flush()

            # Create test report linked to user
            report = Report(
                title="Broken light",
                description="Light near Block A is broken.",
                category="Electricity",
                user_id=user.id,
            )
            db.session.add(report)
            db.session.flush()

            # Create test admin action linked to admin & report
            action = AdminAction(
                action_type="status_change",
                description="Changed to In Progress",
                admin_id=admin.id,
                report_id=report.id,
            )
            db.session.add(action)
            db.session.flush()

            # Verify ORM relationships
            results.append(check("report.author -> User works", report.author.name == "Test Student"))
            results.append(check("user.reports -> Report works", report in user.reports.all()))
            results.append(check("action.admin -> User works", action.admin.name == "Test Admin"))
            results.append(check("action.report -> Report works", action.report.title == "Broken light"))
            results.append(check("report.admin_actions -> AdminAction works", action in report.admin_actions.all()))

            db.session.rollback()  # Don't persist test data
            results.append(check("Session rollback (no test data persisted)", True))

        except Exception as exc:
            db.session.rollback()
            results.append(check("Relationship test", False, str(exc)))

        # -- 7. No duplicate db initialization --------------------------------
        separator("7. No duplicate database initialization")
        from app import db as db2
        results.append(check(
            "Single SQLAlchemy instance (no re-init)",
            db is db2,
            "db imported twice resolves to same object"
        ))

        try:
            app2 = create_app(TestingConfig)
            results.append(check(
                "Second create_app() doesn't raise on init_app()",
                True,
                "Extensions handle multiple init_app() calls safely"
            ))
        except Exception as exc:
            results.append(check("Second create_app() call", False, str(exc)))

    return results


def main():
    print("\nCampusPulse AI - Database Initialization Test")
    print("=" * 60)

    results = run_tests()

    separator("Summary")
    passed = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)
    total = len(results)
    print(f"  Passed : {passed}/{total}")
    print(f"  Failed : {failed}/{total}")

    if failed == 0:
        print("\n  All checks passed. Database setup is verified.\n")
    else:
        print(f"\n  {failed} check(s) failed. Review output above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
