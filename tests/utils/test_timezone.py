"""Test cases for timezone utilities."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from src.utils.timezone import (
    ensure_oslo_timezone,
    now_oslo,
    is_timezone_aware,
    DEFAULT_TIMEZONE
)

def test_ensure_oslo_timezone_with_none():
    """Test that None input returns None."""
    assert ensure_oslo_timezone(None) is None

def test_ensure_oslo_timezone_with_naive():
    """Test converting naive datetime to Oslo timezone."""
    naive_dt = datetime(2024, 1, 1, 12, 0)
    oslo_dt = ensure_oslo_timezone(naive_dt)
    
    assert oslo_dt.tzinfo is not None
    assert oslo_dt.tzinfo.key == "Europe/Oslo"
    assert oslo_dt.hour == naive_dt.hour

def test_ensure_oslo_timezone_with_utc():
    """Test converting UTC datetime to Oslo timezone."""
    utc_dt = datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC"))
    oslo_dt = ensure_oslo_timezone(utc_dt)
    
    assert oslo_dt.tzinfo.key == "Europe/Oslo"
    # The hour should be different due to timezone conversion (UTC+1 in winter, UTC+2 in summer)
    assert oslo_dt.hour in [utc_dt.hour + 1, utc_dt.hour + 2]
    # But they should represent the same moment in time
    assert oslo_dt.astimezone(ZoneInfo("UTC")) == utc_dt

def test_ensure_oslo_timezone_with_oslo():
    """Test that Oslo timezone datetime remains unchanged."""
    oslo_dt = datetime(2024, 1, 1, 12, 0, tzinfo=DEFAULT_TIMEZONE)
    result = ensure_oslo_timezone(oslo_dt)
    
    assert result == oslo_dt
    assert result.tzinfo.key == "Europe/Oslo"

def test_now_oslo():
    """Test that now_oslo returns current time in Oslo timezone."""
    dt = now_oslo()
    assert dt.tzinfo is not None
    assert dt.tzinfo.key == "Europe/Oslo"

def test_is_timezone_aware():
    """Test timezone awareness checker."""
    naive_dt = datetime(2024, 1, 1, 12, 0)
    aware_dt = datetime(2024, 1, 1, 12, 0, tzinfo=DEFAULT_TIMEZONE)
    
    assert not is_timezone_aware(None)
    assert not is_timezone_aware(naive_dt)
    assert is_timezone_aware(aware_dt) 