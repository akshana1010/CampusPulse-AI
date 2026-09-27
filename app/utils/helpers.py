"""
CampusPulse AI – Utility Helpers
General-purpose helpers used across the application.
"""

import re
from datetime import datetime, timezone


def format_datetime(dt: datetime, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    """Format a datetime object to a human-readable string."""
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(fmt)


def time_since(dt: datetime) -> str:
    """
    Return a human-readable 'time ago' string.
    e.g. '2 hours ago', 'just now', '3 days ago'
    """
    if dt is None:
        return "—"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        weeks = seconds // 604800
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"


def slugify(text: str) -> str:
    """Convert a string to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def priority_color(priority: str) -> str:
    """Return a CSS color class for a given priority level."""
    colors = {
        "Critical": "danger",
        "High": "warning",
        "Medium": "info",
        "Low": "secondary",
    }
    return colors.get(priority, "secondary")


def status_color(status: str) -> str:
    """Return a CSS color class for a given report status."""
    colors = {
        "Reported": "secondary",
        "Under Review": "info",
        "In Progress": "warning",
        "Resolved": "success",
    }
    return colors.get(status, "secondary")


def paginate_args(request) -> dict:
    """Extract common pagination query args from a request."""
    return {
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 20, type=int),
    }
