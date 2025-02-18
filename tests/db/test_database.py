"""Test database functionality."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest

from src.models.event import Event
from src.db import db_manager

@pytest.mark.db
def test_database_creation(db):
    """Test that the database is created and accessible."""
    assert db is not None, "Could not get database session"

@pytest.mark.db
def test_event_creation(db):
    """Test creating and retrieving an event."""
    # Create test event
    event = Event(
        title="Test Event",
        description="Test Description",
        start_time=datetime.now(ZoneInfo("UTC")),
        end_time=datetime.now(ZoneInfo("UTC")) + timedelta(hours=1),
        location="Test Location",
        source_url="http://test.com",
        source_name="test"
    )
    
    # Add and commit
    db.add(event)
    db.commit()
    
    # Verify event was saved
    saved_event = db.query(Event).filter_by(title="Test Event").first()
    assert saved_event is not None
    assert saved_event.title == "Test Event"

@pytest.mark.db
def test_rollback(db):
    """Test transaction rollback."""
    # Create test event
    event = Event(
        title="Test Event",
        description="Test Description",
        start_time=datetime.now(ZoneInfo("UTC")),
        end_time=datetime.now(ZoneInfo("UTC")) + timedelta(hours=1),
        location="Test Location",
        source_url="http://test.com",
        source_name="test"
    )
    
    # Add but don't commit
    db.add(event)
    
    # Rollback
    db.rollback()
    
    # Verify event was not saved
    saved_event = db.query(Event).filter_by(title="Test Event").first()
    assert saved_event is None

@pytest.mark.db
def test_session_management():
    """Test session creation and cleanup."""
    # Test that sessions work correctly with commits and rollbacks
    with db_manager.session() as db1:
        # Create and commit first event
        event1 = Event(
            title="Event 1",
            description="Test Description",
            start_time=datetime.now(ZoneInfo("UTC")),
            end_time=datetime.now(ZoneInfo("UTC")) + timedelta(hours=1),
            location="Test Location",
            source_url="http://test.com",
            source_name="test"
        )
        db1.add(event1)
        db1.commit()
        
        # Verify event exists
        assert db1.query(Event).filter_by(title="Event 1").first() is not None
        
        # Create a second session
        with db_manager.session() as db2:
            # Second session should see committed changes
            assert db2.query(Event).filter_by(title="Event 1").first() is not None
            
            # Create but don't commit second event
            event2 = Event(
                title="Event 2",
                description="Test Description",
                start_time=datetime.now(ZoneInfo("UTC")),
                end_time=datetime.now(ZoneInfo("UTC")) + timedelta(hours=1),
                location="Test Location",
                source_url="http://test.com",
                source_name="test"
            )
            db2.add(event2)
            
            # Rollback second session
            db2.rollback()
            
            # Create and commit third event
            event3 = Event(
                title="Event 3",
                description="Test Description",
                start_time=datetime.now(ZoneInfo("UTC")),
                end_time=datetime.now(ZoneInfo("UTC")) + timedelta(hours=1),
                location="Test Location",
                source_url="http://test.com",
                source_name="test"
            )
            db2.add(event3)
            db2.commit()
            
            # Both sessions should see event 3
            assert db1.query(Event).filter_by(title="Event 3").first() is not None
            assert db2.query(Event).filter_by(title="Event 3").first() is not None
            
            # Neither session should see rolled back event 2
            assert db1.query(Event).filter_by(title="Event 2").first() is None
            assert db2.query(Event).filter_by(title="Event 2").first() is None 