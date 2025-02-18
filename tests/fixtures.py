"""Test fixtures and data management."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List

from src.models.event import Event
from src.db.base import get_db

def create_test_event(**overrides) -> Event:
    """Create a single test event with default values that can be overridden."""
    oslo_tz = ZoneInfo("Europe/Oslo")
    defaults = {
        "title": "Test Event",
        "description": "Test Description",
        "start_time": datetime.now(oslo_tz),
        "end_time": datetime.now(oslo_tz) + timedelta(hours=2),
        "location": "Test Location",
        "source_url": "http://test.com",
        "source_name": "test_source"
    }
    # Override defaults with any provided values
    event_data = {**defaults, **overrides}
    return Event(**event_data)

def create_sample_events() -> List[Event]:
    """Create a set of realistic test events."""
    db = get_db()
    oslo_tz = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo_tz)
    
    events = [
        # Regular event
        create_test_event(
            title="IFI Career Day",
            description="Annual career fair at IFI",
            location="Ole-Johan Dahls hus"
        ),
        # Event with registration
        create_test_event(
            title="Programming Workshop",
            description="Learn Python programming",
            capacity=30,
            spots_left=15,
            registration_opens=now - timedelta(days=1)
        ),
        # Multi-day event
        create_test_event(
            title="Tech Conference",
            description="Annual technology conference",
            end_time=now + timedelta(days=2),
            location="IFI - Kristen Nygaards hus"
        ),
        # Event with food
        create_test_event(
            title="Pizza and Programming",
            description="Coding session with pizza",
            food="Pizza and soft drinks"
        )
    ]
    
    for event in events:
        db.add(event)
    db.commit()
    
    return events

def create_duplicate_events() -> List[Event]:
    """Create events that are potential duplicates for testing deduplication."""
    db = get_db()
    oslo_tz = ZoneInfo("Europe/Oslo")
    now = datetime.now(oslo_tz)
    
    # Create original event
    original = create_test_event(
        title="Original Event",
        start_time=now,
        source_name="source1"
    )
    db.add(original)
    
    # Create similar events with slight differences
    duplicates = [
        # Same title, slightly different time
        create_test_event(
            title="Original Event",
            start_time=now + timedelta(minutes=30),
            source_name="source2"
        ),
        # Similar title, same time
        create_test_event(
            title="Original Event (Copy)",
            start_time=now,
            source_name="source3"
        )
    ]
    
    for event in duplicates:
        db.add(event)
    db.commit()
    
    return [original] + duplicates 