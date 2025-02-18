"""Test cases for the Event model."""

from datetime import datetime
from zoneinfo import ZoneInfo

from tests.base import BaseTestCase
from src.models.event import Event
from src.db.base import get_db, close_db

class TestEventModel(BaseTestCase):
    """Test cases for the Event model with SQLAlchemy"""
    
    def setUp(self):
        """Set up test case"""
        super().setUp()
        self.db = get_db()
        
        # Create a test event with Oslo timezone
        oslo_tz = ZoneInfo("Europe/Oslo")
        self.test_event = Event(
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(oslo_tz),
            end_time=datetime.now(oslo_tz),
            location="Test Location",
            source_url="http://test.com",
            source_name="test_source"
        )
    
    def tearDown(self):
        """Clean up after test"""
        close_db()
        super().tearDown()
    
    def test_event_creation(self):
        """Test that we can create and retrieve an event"""
        # Add event to database
        self.db.add(self.test_event)
        self.db.commit()
        
        # Retrieve event
        stored_event = self.db.query(Event).first()
        
        # Check fields
        self.assertEqual(stored_event.title, self.test_event.title)
        self.assertEqual(stored_event.description, self.test_event.description)
        self.assertEqual(stored_event.location, self.test_event.location)
        self.assertEqual(stored_event.source_url, self.test_event.source_url)
        self.assertEqual(stored_event.source_name, self.test_event.source_name)
    
    def test_event_update(self):
        """Test that we can update an event"""
        # Add event to database
        self.db.add(self.test_event)
        self.db.commit()
        
        # Update event
        self.test_event.title = "Updated Title"
        self.db.commit()
        
        # Retrieve event
        stored_event = self.db.query(Event).first()
        self.assertEqual(stored_event.title, "Updated Title")
    
    def test_event_deletion(self):
        """Test that we can delete an event"""
        # Add event to database
        self.db.add(self.test_event)
        self.db.commit()
        
        # Delete event
        self.db.delete(self.test_event)
        self.db.commit()
        
        # Check that event is gone
        stored_event = self.db.query(Event).first()
        self.assertIsNone(stored_event)
    
    def test_timezone_handling(self):
        """Test that times are stored correctly in Oslo time"""
        # Create event with UTC timezone (should be converted to Oslo)
        utc_tz = ZoneInfo("UTC")
        utc_time = datetime.now(utc_tz)
        oslo_time = utc_time.astimezone(ZoneInfo("Europe/Oslo"))
        
        self.test_event.start_time = utc_time
        self.db.add(self.test_event)
        self.db.commit()
        
        # Retrieve event and verify the time matches Oslo time
        # (ignoring timezone info since SQLite doesn't store it)
        stored_event = self.db.query(Event).first()
        self.assertEqual(stored_event.start_time.replace(tzinfo=None), 
                        oslo_time.replace(tzinfo=None))

if __name__ == '__main__':
    unittest.main() 