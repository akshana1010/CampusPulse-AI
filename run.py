"""
CampusPulse AI – Entry Point
Run this file to start the development server:
    python run.py
"""

from app import create_app, db

app = create_app()

# ── Ensure all database tables exist ──────────────────────────────────────────
# db.create_all() is safe to call on every startup; it is a no-op for tables
# that already exist and only creates the ones that are missing.
with app.app_context():
    db.create_all()
    from app import _ensure_admin
    _ensure_admin(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
