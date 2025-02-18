"""Test database functionality."""

from tests.base import BaseTestCase
from src.models.event import Event
from src.db.base import get_db, close_db, DB_PATH
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

class TestDatabase(BaseTestCase):
    """Test database operations."""

    def test_database_creation(self):
        """Test that the database is created and accessible."""
        # For in-memory database, we just verify we can get a session
        db = get_db()
        self.assertIsNotNone(db, "Could not get database session")
        close_db()

    def test_event_creation(self):
        """Test creating and retrieving an event."""
        db = get_db()
        
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
        self.assertIsNotNone(saved_event)
        self.assertEqual(saved_event.title, "Test Event")
        
        close_db()

    def test_rollback(self):
        """Test transaction rollback."""
        db = get_db()
        
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
        self.assertIsNone(saved_event)
        
        close_db()

    def test_session_management(self):
        """Test session creation and cleanup."""
        # Get multiple sessions
        db1 = get_db()
        db2 = get_db()
        
        # Verify they're the same session (scoped_session behavior)
        self.assertEqual(id(db1), id(db2))
        
        # Close sessions
        close_db()
        close_db()  # Should not raise error 