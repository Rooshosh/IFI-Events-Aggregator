"""Test cases for the Navet scraper."""

import logging
import pytest
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

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
@pytest.mark.live
def test_raw_response_caching(navet_scraper):
    """Test that raw HTML responses are cached correctly"""
    # Main page URL
    main_url = f"{navet_scraper.base_url}/arrangementer/2025/var/"
    
    # First fetch - should get from website and cache
    raw_html_first = navet_scraper._fetch_html(main_url)
    
    # Second fetch - should get from cache
    raw_html_second = navet_scraper._fetch_html(main_url)
    
    # Verify the raw HTML responses are identical
    assert raw_html_first == raw_html_second, \
        "Raw HTML responses differ between cache reads"
    
    # Verify both are valid HTML by parsing with BeautifulSoup
    try:
        BeautifulSoup(raw_html_first, 'html.parser')
        BeautifulSoup(raw_html_second, 'html.parser')
    except Exception as e:
        pytest.fail(f"Cached response is not valid HTML: {e}")

@pytest.mark.scraper
@pytest.mark.live
def test_event_details_caching(navet_scraper):
    """Test that event details pages are cached correctly"""
    # Get main page and extract first event URL
    main_url = f"{navet_scraper.base_url}/arrangementer/2025/var/"
    main_html = navet_scraper._fetch_html(main_url)
    soup = BeautifulSoup(main_html, 'html.parser')
    event_item = soup.find('div', class_='event-list-item-wrapper')
    
    if not event_item or not event_item.get('onclick'):
        pytest.skip("No event found to test details caching")
    
    event_url = navet_scraper._get_event_url(event_item['onclick'])
    
    # First fetch of details
    details_html_first = navet_scraper._fetch_event_details(event_url)
    
    # Second fetch of details (should use cache)
    details_html_second = navet_scraper._fetch_event_details(event_url)
    
    # Verify the raw HTML responses are identical
    assert details_html_first == details_html_second, \
        "Raw HTML responses for event details differ between cache reads"

@pytest.mark.scraper
@pytest.mark.live
def test_parsing_consistency(navet_scraper):
    """Test that parsing the same raw HTML produces consistent results"""
    # Get raw HTML (from cache or website)
    main_url = f"{navet_scraper.base_url}/arrangementer/2025/var/"
    raw_html = navet_scraper._fetch_html(main_url)
    
    # Parse the HTML twice
    soup = BeautifulSoup(raw_html, 'html.parser')
    event_cards = soup.find_all('div', class_='event-list-item-wrapper', recursive=True)
    
    events_first = []
    events_second = []
    
    # First parse
    for event_card in event_cards:
        event = navet_scraper._parse_event_card(event_card)
        if event:
            events_first.append(event)
    
    # Second parse
    for event_card in event_cards:
        event = navet_scraper._parse_event_card(event_card)
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