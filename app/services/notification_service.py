"""
CampusPulse AI – Notification Service
Creates in-app notifications when a report's status changes.
"""

import logging
from app import db
from app.models import Notification

logger = logging.getLogger(__name__)

# Status change message templates
_STATUS_MESSAGES = {
    "Under Review": "Your report \"{title}\" is now under review by the campus team.",
    "In Progress": "Work has started on your report \"{title}\". We're on it!",
    "Resolved": "Great news! Your report \"{title}\" has been resolved.",
}

_DEFAULT_MESSAGE = "Your report \"{title}\" has been updated to: {status}."


def send_status_notification(report, old_status: str, new_status: str) -> None:
    """
    Create an in-app notification for the report author when status changes.

    Args:
        report:     Report model instance.
        old_status: Previous status string.
        new_status: New status string.
    """
    if report.user_id is None:
        return

    template = _STATUS_MESSAGES.get(new_status, _DEFAULT_MESSAGE)
    message = template.format(title=report.title[:80], status=new_status)

    try:
        notification = Notification(
            user_id=report.user_id,
            report_id=report.id,
            message=message,
            is_read=False,
        )
        db.session.add(notification)
        db.session.commit()
        logger.info(
            f"Notification sent to user {report.user_id} for report {report.id} "
            f"({old_status} → {new_status})"
        )
    except Exception as exc:
        logger.error(f"Failed to create notification: {exc}")
        db.session.rollback()


def mark_notifications_read(user_id: int) -> int:
    """
    Mark all unread notifications for a user as read.

    Returns:
        Number of notifications updated.
    """
    try:
        count = (
            Notification.query
            .filter_by(user_id=user_id, is_read=False)
            .update({"is_read": True})
        )
        db.session.commit()
        return count
    except Exception as exc:
        logger.error(f"Failed to mark notifications read: {exc}")
        db.session.rollback()
        return 0


def get_unread_count(user_id: int) -> int:
    """Return the number of unread notifications for a user."""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()
