import unittest
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scrapers.navet import NavetScraper
from src.utils.cache import CacheConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestNavetScraper(unittest.TestCase):
    """Test cases for the Navet scraper"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.cache_config = CacheConfig(
            cache_dir=Path(__file__).parent.parent.parent / 'data' / 'cache',
            enabled_sources=['ifinavet.no'],
            force_live=True  # Use live data for tests
        )
        self.scraper = NavetScraper(cache_config=self.cache_config)
    
    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly"""
        self.assertEqual(self.scraper.name(), "ifinavet.no")
        self.assertEqual(self.scraper.base_url, "https://ifinavet.no")
        self.assertTrue(isinstance(self.scraper.cache_config, CacheConfig))
    
    def test_event_scraping(self):
        """Test that events can be scraped and have the correct format"""
        events = self.scraper.get_events()
        
        # Check that we got some events
        self.assertTrue(len(events) > 0, "No events were scraped")
        
        # Check the first event's structure
        event = events[0]
        self.assertTrue(hasattr(event, 'title'), "Event missing title")
        self.assertTrue(hasattr(event, 'description'), "Event missing description")
        self.assertTrue(hasattr(event, 'start_time'), "Event missing start_time")
        self.assertTrue(hasattr(event, 'end_time'), "Event missing end_time")
        
        # Check datetime fields
        self.assertTrue(isinstance(event.start_time, datetime), "start_time is not a datetime object")
        self.assertTrue(event.start_time.tzinfo is not None, "start_time is not timezone-aware")
        
        if event.end_time:
            self.assertTrue(isinstance(event.end_time, datetime), "end_time is not a datetime object")
            self.assertTrue(event.end_time.tzinfo is not None, "end_time is not timezone-aware")
            self.assertTrue(event.end_time > event.start_time, "end_time is before start_time")
    
    def test_caching(self):
        """Test that caching works correctly"""
        # First fetch (creates cache)
        self.scraper.cache_config.force_live = True
        events_live = self.scraper.get_events()
        
        # Second fetch (should use cache)
        self.scraper.cache_config.force_live = False
        events_cached = self.scraper.get_events()
        
        # Compare results
        self.assertEqual(len(events_live), len(events_cached), 
                        "Number of events differs between live and cached data")
        
        if len(events_live) > 0:
            # Compare first event
            live_event = events_live[0]
            cached_event = events_cached[0]
            self.assertEqual(live_event.title, cached_event.title,
                           "Event title differs between live and cached data")
            self.assertEqual(live_event.start_time, cached_event.start_time,
                           "Event start_time differs between live and cached data")

if __name__ == '__main__':
    unittest.main() 