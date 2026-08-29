"""Basic tools for Jarvis - time and simple utilities."""

from datetime import datetime


def get_current_time():
    """Return the current local date and time."""
    return datetime.now().strftime(
        "%A, %d %B %Y at %H:%M:%S"
    )
