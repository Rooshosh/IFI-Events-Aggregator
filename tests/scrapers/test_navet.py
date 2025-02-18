"""Test cases for the Navet scraper."""

import logging
import pytest
from datetime import datetime
from pathlib import Path

from src.scrapers.navet import NavetScraper
from src.utils.cache import CacheConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture
def cache_config():
    """Provide a cache configuration for testing."""
    return CacheConfig(
        cache_dir=Path(__file__).parent.parent.parent / 'data' / 'cache',
        enabled_sources=['ifinavet.no'],
        force_live=False  # Use cached data for tests
    )

@pytest.fixture
def navet_scraper(cache_config):
    """Provide a configured Navet scraper instance."""
    return NavetScraper(cache_config=cache_config)

@pytest.mark.scraper
def test_scraper_initialization(navet_scraper):
    """Test that the scraper initializes correctly"""
    assert navet_scraper.name() == "ifinavet.no"
    assert navet_scraper.base_url == "https://ifinavet.no"
    assert isinstance(navet_scraper.cache_config, CacheConfig)

@pytest.mark.scraper
def test_event_scraping(navet_scraper):
    """Test that events can be scraped and have the correct format"""
    events = navet_scraper.get_events()
    
    # Check that we got some events
    assert len(events) > 0, "No events were scraped"
    
    # Check the first event's structure
    event = events[0]
    assert hasattr(event, 'title'), "Event missing title"
    assert hasattr(event, 'description'), "Event missing description"
    assert hasattr(event, 'start_time'), "Event missing start_time"
    assert hasattr(event, 'end_time'), "Event missing end_time"
    
    # Check datetime fields
    assert isinstance(event.start_time, datetime), "start_time is not a datetime object"
    assert event.start_time.tzinfo is not None, "start_time is not timezone-aware"
    
    if event.end_time:
        assert isinstance(event.end_time, datetime), "end_time is not a datetime object"
        assert event.end_time.tzinfo is not None, "end_time is not timezone-aware"
        assert event.end_time > event.start_time, "end_time is before start_time"

@pytest.mark.scraper
def test_caching(navet_scraper):
    """Test that caching works correctly"""
    # First fetch (should use cache)
    events_first = navet_scraper.get_events()
    
    # Second fetch (should use same cache)
    events_second = navet_scraper.get_events()
    
    # Compare results
    assert len(events_first) == len(events_second), \
        "Number of events differs between cache reads"
    
    if len(events_first) > 0:
        # Compare first event
        first_event = events_first[0]
        second_event = events_second[0]
        assert first_event.title == second_event.title, \
            "Event title differs between cache reads"
        assert first_event.start_time == second_event.start_time, \
            "Event start_time differs between cache reads"

@pytest.mark.scraper
@pytest.mark.live
def test_live_scraping(cache_config):
    """Test that live scraping works correctly. Only runs when explicitly requested."""
    # Enable live scraping for this test
    cache_config.force_live = True
    live_scraper = NavetScraper(cache_config=cache_config)
    
    # Fetch live events
    events = live_scraper.get_events()
    
    # Basic validation
    assert len(events) > 0, "No events were scraped from live source"
    
    # Verify first event has required fields
    event = events[0]
    assert event.title, "Live event missing title"
    assert event.start_time, "Live event missing start time" 