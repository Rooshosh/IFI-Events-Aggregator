"""Test cases for the Event model."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from src.models.event import Event
from src.db import db_manager

@pytest.mark.db
def test_event_creation(db, test_event):
    """Test that we can create and retrieve an event"""
    # Add event to database
    db.add(test_event)
    db.commit()
    
    # Retrieve event
    stored_event = db.query(Event).first()
    
    # Check fields
    assert stored_event.title == test_event.title
    assert stored_event.description == test_event.description
    assert stored_event.location == test_event.location
    assert stored_event.source_url == test_event.source_url
    assert stored_event.source_name == test_event.source_name

@pytest.mark.db
def test_event_update(db, test_event):
    """Test that we can update an event"""
    # Add event to database
    db.add(test_event)
    db.commit()
    
    # Update event
    test_event.title = "Updated Title"
    db.commit()
    
    # Retrieve event
    stored_event = db.query(Event).first()
    assert stored_event.title == "Updated Title"

@pytest.mark.db
def test_event_deletion(db, test_event):
    """Test that we can delete an event"""
    # Add event to database
    db.add(test_event)
    db.commit()
    
    # Delete event
    db.delete(test_event)
    db.commit()
    
    # Check that event is gone
    stored_event = db.query(Event).first()
    assert stored_event is None

@pytest.mark.db
def test_timezone_handling(db, test_event):
    """Test that times are stored correctly in Oslo time"""
    # Create event with UTC timezone (should be converted to Oslo)
    utc_tz = ZoneInfo("UTC")
    utc_time = datetime.now(utc_tz)
    oslo_time = utc_time.astimezone(ZoneInfo("Europe/Oslo"))
    
    test_event.start_time = utc_time
    db.add(test_event)
    db.commit()
    
    # Retrieve event and verify the time matches Oslo time
    # (ignoring timezone info since SQLite doesn't store it)
    stored_event = db.query(Event).first()
    assert stored_event.start_time.replace(tzinfo=None) == oslo_time.replace(tzinfo=None) 