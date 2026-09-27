"""
CampusPulse AI – Create/Update Admin Account CLI Tool
Safely creates or resets the administrator password locally.

Usage:
    # Interactive prompt:
    python create_admin.py

    # Or via command line arguments:
    python create_admin.py --email admin@campuspulse.ai --password MySecretPassword123

    # Or via environment variables:
    set ADMIN_EMAIL=admin@campuspulse.ai
    set ADMIN_PASSWORD=MySecretPassword123
    python create_admin.py
"""

import sys
import os
import argparse
import getpass
from app import create_app, db
from app.models import User


def setup_admin(email=None, password=None, name="Campus Administrator"):
    app = create_app()
    with app.app_context():
        # Fallbacks: args -> env -> prompt
        email = email or os.getenv("ADMIN_EMAIL")
        password = password or os.getenv("ADMIN_PASSWORD")
        name = name or os.getenv("ADMIN_NAME", "Campus Administrator")

        if not email:
            try:
                email = input("Enter admin email [default: admin@campuspulse.ai]: ").strip()
            except (EOFError, KeyboardInterrupt):
                email = ""
            if not email:
                email = "admin@campuspulse.ai"

        if not password:
            try:
                password = getpass.getpass("Enter admin password (min 8 characters): ").strip()
            except (EOFError, KeyboardInterrupt):
                password = ""

        if not password:
            print("Error: Admin password cannot be empty.")
            return False

        if len(password) < 8:
            print("Error: Password must be at least 8 characters long.")
            return False

        user = User.query.filter_by(email=email.lower()).first()

        if user:
            user.name = name
            user.role = "admin"
            user.is_active = True
            user.set_password(password)
            db.session.commit()
            print(f"[OK] Administrator account '{user.email}' updated successfully.")
        else:
            user = User()
            user.name = name
            user.email = email.lower()
            user.role = "admin"
            user.is_active = True
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"[OK] Administrator account '{user.email}' created successfully.")

        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update a CampusPulse AI admin account.")
    parser.add_argument("--email", default=None, help="Admin email address")
    parser.add_argument("--password", default=None, help="Admin password")
    parser.add_argument("--name", default="Campus Administrator", help="Admin display name")

    args = parser.parse_args()
    success = setup_admin(email=args.email, password=args.password, name=args.name)
    sys.exit(0 if success else 1)
