"""
CampusPulse AI – SQLAlchemy Models
All database tables are defined here as SQLAlchemy ORM models.

Tables
------
users          – Registered campus users (students & admins)
reports        – Campus problem reports submitted by students
status_history – Audit trail of report-status transitions
report_votes   – Community upvote / downvote records
notifications  – In-app notifications sent to students
admin_actions  – Log of every admin-initiated action
"""

import json
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


# ── Enum-style constants ───────────────────────────────────────────────────────

CATEGORIES = [
    "Safety", "Cleanliness", "Infrastructure", "Transport",
    "Electricity", "Water", "Internet", "Academic", "Accessibility", "Other",
]

PRIORITIES = ["Low", "Medium", "High", "Critical"]

STATUSES = ["Reported", "In Progress", "Resolved"]

SENTIMENTS = ["positive", "neutral", "negative", "urgent"]

ROLES = ["student", "admin"]


# ── Helper ─────────────────────────────────────────────────────────────────────

def utcnow():
    return datetime.now(timezone.utc)


# ── User ───────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    """Represents a registered campus user (student or admin)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    student_id = db.Column(db.String(40), unique=True, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    role = db.Column(db.String(10), nullable=False, default="student")
    avatar_url = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Relationships
    reports = db.relationship("Report", back_populates="author", lazy="dynamic", foreign_keys="Report.user_id")
    votes = db.relationship("ReportVote", back_populates="user", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="user", lazy="dynamic")
    status_changes = db.relationship("StatusHistory", back_populates="changed_by_user", lazy="dynamic")
    admin_actions = db.relationship("AdminAction", back_populates="admin", lazy="dynamic", foreign_keys="AdminAction.admin_id")

    # ── Password helpers ───────────────────────────────────────────────────────

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ── Role helpers ───────────────────────────────────────────────────────────

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "student_id": self.student_id,
            "department": self.department,
            "year": self.year,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"


# ── Report ─────────────────────────────────────────────────────────────────────

class Report(db.Model):
    """A campus problem report submitted by a student."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # User-selected fields
    category = db.Column(db.String(40), nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    is_emergency = db.Column(db.Boolean, default=False, nullable=False)

    # AI-analysed fields
    ai_category = db.Column(db.String(40), nullable=True)
    priority = db.Column(db.String(12), nullable=False, default="Low")
    ai_summary = db.Column(db.Text, nullable=True)
    ai_sentiment = db.Column(db.String(20), nullable=True)
    ai_confidence = db.Column(db.Float, nullable=True)
    ai_raw_response = db.Column(db.Text, nullable=True)

    # Status
    status = db.Column(db.String(20), nullable=False, default="Reported", index=True)

    # Location
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_label = db.Column(db.String(200), nullable=True)

    # File
    image_path = db.Column(db.String(300), nullable=True)

    # Admin
    admin_notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    author = db.relationship("User", back_populates="reports", foreign_keys=[user_id])
    status_history = db.relationship("StatusHistory", back_populates="report", lazy="dynamic", cascade="all, delete-orphan")
    votes = db.relationship("ReportVote", back_populates="report", lazy="dynamic", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="report", lazy="dynamic", cascade="all, delete-orphan")
    admin_actions = db.relationship("AdminAction", back_populates="report", lazy="dynamic", cascade="all, delete-orphan")

    # ── Display / Privacy helpers ──────────────────────────────────────────────

    @property
    def display_author(self) -> str:
        """Return 'Anonymous Student' if anonymous, otherwise author name."""
        if self.is_anonymous:
            return "Anonymous Student"
        return self.author.name if self.author else "Student"

    # ── Vote helpers ───────────────────────────────────────────────────────────

    @property
    def upvote_count(self) -> int:
        return self.votes.filter_by(vote_type="upvote").count()

    @property
    def downvote_count(self) -> int:
        return self.votes.filter_by(vote_type="downvote").count()

    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self, include_ai=True, viewer_is_author=False) -> dict:
        author_name = "Anonymous Student" if (self.is_anonymous and not viewer_is_author) else (self.author.name if self.author else None)
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "is_anonymous": self.is_anonymous,
            "is_emergency": self.is_emergency,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_label": self.location_label,
            "image_path": self.image_path,
            "upvotes": self.upvote_count,
            "downvotes": self.downvote_count,
            "author": author_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_ai:
            data.update({
                "ai_category": self.ai_category,
                "ai_summary": self.ai_summary,
                "ai_sentiment": self.ai_sentiment,
                "ai_confidence": self.ai_confidence,
                "ai_suggested_solution": self.ai_suggested_solution,
            })
        return data

    @property
    def ai_suggested_solution(self) -> str:
        """Derive or return the AI suggested practical solution for the report."""
        if self.ai_raw_response:
            try:
                data = json.loads(self.ai_raw_response)
                if isinstance(data, dict) and data.get("suggested_solution"):
                    return str(data["suggested_solution"]).strip()
            except Exception:
                pass
        from app.services.ai_service import get_fallback_solution
        cat = self.ai_category or self.category or "Other"
        return get_fallback_solution(cat, self.title or "", self.description or "")

    def to_map_dict(self) -> dict:
        """Minimal payload for the Leaflet map endpoint."""
        return {
            "id": self.id,
            "title": self.title,
            "description": (self.description[:180] + "...") if self.description and len(self.description) > 180 else (self.description or ""),
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "is_emergency": self.is_emergency,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_label": self.location_label,
        }

    def __repr__(self):
        return f"<Report #{self.id} [{'EMERGENCY ' if self.is_emergency else ''}{self.status}] '{self.title[:40]}'>"


# ── StatusHistory ──────────────────────────────────────────────────────────────

class StatusHistory(db.Model):
    """Audit trail of every status transition on a report."""

    __tablename__ = "status_history"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    note = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Relationships
    report = db.relationship("Report", back_populates="status_history")
    changed_by_user = db.relationship("User", back_populates="status_changes", foreign_keys=[changed_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by_user.name if self.changed_by_user else "System",
            "note": self.note,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }

    def __repr__(self):
        return f"<StatusHistory report={self.report_id} {self.old_status}→{self.new_status}>"


# ── ReportVote ─────────────────────────────────────────────────────────────────

class ReportVote(db.Model):
    """Community upvote/downvote on a report."""

    __tablename__ = "report_votes"
    __table_args__ = (
        db.UniqueConstraint("report_id", "user_id", name="uq_report_user_vote"),
    )

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    vote_type = db.Column(db.String(8), nullable=False)  # 'upvote' | 'downvote'
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Relationships
    report = db.relationship("Report", back_populates="votes")
    user = db.relationship("User", back_populates="votes")

    def __repr__(self):
        return f"<ReportVote report={self.report_id} user={self.user_id} {self.vote_type}>"


# ── Notification ───────────────────────────────────────────────────────────────

class Notification(db.Model):
    """In-app notification sent to a student when their report status changes."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Relationships
    user = db.relationship("User", back_populates="notifications")
    report = db.relationship("Report", back_populates="notifications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message": self.message,
            "report_id": self.report_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


    def __repr__(self):
        return f"<Notification user={self.user_id} read={self.is_read}>"


# ── AdminAction ────────────────────────────────────────────────────────────────

ADMIN_ACTION_TYPES = [
    "status_change",
    "priority_override",
    "add_note",
    "delete_report",
    "role_change",
    "other",
]


class AdminAction(db.Model):
    """
    Audit log of every administrative action performed by an admin user.

    Every time an admin changes a report status, overrides priority,
    adds a note, deletes a report, or changes a user's role, a row is
    inserted here.  The ``report_id`` column is nullable so that actions
    that are not tied to a specific report (e.g. role changes) can still
    be recorded.
    """

    __tablename__ = "admin_actions"

    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(30), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    payload = db.Column(db.Text, nullable=True)  # JSON string of extra data
    performed_at = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)

    # Foreign keys
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=True, index=True)

    # Relationships
    admin = db.relationship("User", back_populates="admin_actions", foreign_keys=[admin_id])
    report = db.relationship("Report", back_populates="admin_actions", foreign_keys=[report_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "description": self.description,
            "payload": self.payload,
            "admin": self.admin.name if self.admin else None,
            "report_id": self.report_id,
            "performed_at": self.performed_at.isoformat() if self.performed_at else None,
        }

    def __repr__(self):
        return f"<AdminAction [{self.action_type}] by admin={self.admin_id} report={self.report_id}>"
