import logging
import os
import sys
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.scrapers.navet import NavetScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_navet_scraper():
    """Test the Navet scraper by fetching and displaying events"""
    scraper = NavetScraper()
    
    logger.info("Starting Navet scraper test")
    events = scraper.scrape_events()
    
    if not events:
        logger.warning("No events were found!")
        return
    
    logger.info(f"Successfully scraped {len(events)} events")
    
    # Display detailed information for each event
    for i, event in enumerate(events, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Event {i}:")
        logger.info(f"{'='*80}")
        logger.info(f"Title: {event.title}")
        logger.info(f"Start Time: {event.start_time.strftime('%Y-%m-%d %H:%M %Z')}")
        logger.info(f"End Time: {event.end_time.strftime('%Y-%m-%d %H:%M %Z')}")
        logger.info(f"Location: {event.location or 'Not specified'}")
        logger.info(f"Food: {event.food or 'Not specified'}")
        logger.info(f"Capacity: {event.capacity if event.capacity is not None else 'Not specified'}")
        logger.info(f"Spots Left: {event.spots_left if event.spots_left is not None else 'Not specified'}")
        logger.info(f"Source URL: {event.source_url}")
        logger.info(f"Source: {event.source_name}")
        logger.info("\nDescription:")
        # Print full description, line by line for better readability
        for line in event.description.split('\n'):
            logger.info(f"  {line}")

if __name__ == '__main__':
    test_navet_scraper() 