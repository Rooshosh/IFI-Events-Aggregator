"""Test database functionality."""

from tests.base import BaseTestCase
from src.models.event import Event
from src.db import db_manager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

class TestDatabase(BaseTestCase):
    """Test database operations."""

    def test_database_creation(self):
        """Test that the database is created and accessible."""
        with db_manager.session() as db:
            self.assertIsNotNone(db, "Could not get database session")

    def test_event_creation(self):
        """Test creating and retrieving an event."""
        with db_manager.session() as db:
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

    def test_rollback(self):
        """Test transaction rollback."""
        with db_manager.session() as db:
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

    def test_session_management(self):
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
            self.assertIsNotNone(db1.query(Event).filter_by(title="Event 1").first())
            
            # Create a second session
            with db_manager.session() as db2:
                # Second session should see committed changes
                self.assertIsNotNone(db2.query(Event).filter_by(title="Event 1").first())
                
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
                self.assertIsNotNone(db1.query(Event).filter_by(title="Event 3").first())
                self.assertIsNotNone(db2.query(Event).filter_by(title="Event 3").first())
                
                # Neither session should see rolled back event 2
                self.assertIsNone(db1.query(Event).filter_by(title="Event 2").first())
                self.assertIsNone(db2.query(Event).filter_by(title="Event 2").first()) 