"""Timezone utilities for the application."""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

# Default timezone for the application
DEFAULT_TIMEZONE = ZoneInfo("Europe/Oslo")

def ensure_oslo_timezone(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is in Oslo timezone.
    
    Args:
        dt: Datetime to convert, can be:
           - None (returns None)
           - Naive datetime (assumes Oslo timezone)
           - Timezone-aware datetime (converts to Oslo timezone)
    
    Returns:
        Datetime in Oslo timezone, or None if input was None
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        return dt.replace(tzinfo=DEFAULT_TIMEZONE)
    return dt.astimezone(DEFAULT_TIMEZONE)

def now_oslo() -> datetime:
    """Get current time in Oslo timezone."""
    return datetime.now(DEFAULT_TIMEZONE)

def is_timezone_aware(dt: Optional[datetime]) -> bool:
    """Check if a datetime is timezone-aware."""
    return dt is not None and dt.tzinfo is not None 