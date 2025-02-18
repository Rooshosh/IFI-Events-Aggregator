"""Test cases for the Peoply scraper."""

import logging
import pytest
from datetime import datetime
from pathlib import Path
import json

from src.scrapers.peoply import PeoplyScraper
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
        enabled_sources=['peoply.app'],
        force_live=False  # Use cached data for tests
    )

@pytest.fixture
def peoply_scraper(cache_config):
    """Provide a configured Peoply scraper instance."""
    return PeoplyScraper(cache_config=cache_config)

@pytest.mark.scraper
def test_scraper_initialization(peoply_scraper):
    """Test that the scraper initializes correctly"""
    assert peoply_scraper.name() == "peoply.app"
    assert peoply_scraper.base_url == "https://api.peoply.app"
    assert isinstance(peoply_scraper.cache_config, CacheConfig)

@pytest.mark.scraper
@pytest.mark.live
def test_raw_response_caching(peoply_scraper):
    """Test that raw API responses are cached correctly"""
    # Get the API URL
    url = peoply_scraper._get_api_url()
    
    # First fetch - should get from API and cache
    raw_response_first = peoply_scraper._fetch_json(url)
    
    # Second fetch - should get from cache
    raw_response_second = peoply_scraper._fetch_json(url)
    
    # Verify the raw responses are identical
    assert raw_response_first == raw_response_second, \
        "Raw API responses differ between cache reads"
    
    # Verify both are valid JSON strings
    try:
        json.loads(raw_response_first)
        json.loads(raw_response_second)
    except json.JSONDecodeError:
        pytest.fail("Cached response is not a valid JSON string")

@pytest.mark.scraper
@pytest.mark.live
def test_parsing_consistency(peoply_scraper):
    """Test that parsing the same raw response produces consistent results"""
    # Get raw response (from cache or API)
    url = peoply_scraper._get_api_url()
    raw_response = peoply_scraper._fetch_json(url)
    
    # Parse the raw response twice
    api_events = json.loads(raw_response)
    
    events_first = []
    events_second = []
    
    # First parse
    for api_event in api_events[:10]:  # Using same limit as scraper
        event = peoply_scraper._parse_api_event(api_event)
        if event:
            events_first.append(event)
    
    # Second parse
    for api_event in api_events[:10]:  # Using same limit as scraper
        event = peoply_scraper._parse_api_event(api_event)
        if event:
            events_second.append(event)
    
    # Verify both parses produced the same results
    assert len(events_first) == len(events_second), \
        "Number of parsed events differs between runs"
    
    for first, second in zip(events_first, events_second):
        assert first.title == second.title, \
            "Event title differs between parsing runs"
        assert first.start_time == second.start_time, \
            "Event start_time differs between parsing runs"

@pytest.mark.scraper
@pytest.mark.live
def test_event_scraping(peoply_scraper):
    """Test that events can be scraped and have the correct format"""
    events = peoply_scraper.get_events()
    
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
        assert event.end_time >= event.start_time, "end_time is before start_time"

@pytest.mark.scraper
@pytest.mark.live
def test_caching(peoply_scraper):
    """Test that caching works correctly"""
    # First fetch (should use cache)
    events_first = peoply_scraper.get_events()
    
    # Second fetch (should use same cache)
    events_second = peoply_scraper.get_events()
    
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
    live_scraper = PeoplyScraper(cache_config=cache_config)
    
    # Fetch live events
    events = live_scraper.get_events()
    
    # Basic validation
    assert len(events) > 0, "No events were scraped from live source"
    
    # Verify first event has required fields
    event = events[0]
    assert event.title, "Live event missing title"
    assert event.start_time, "Live event missing start time" 