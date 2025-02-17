#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.db.database import init_db, get_db
from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.utils.cache import CacheConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Update events in database from all sources"""
    # Initialize database
    init_db()
    db = get_db()
    
    # Configure caching
    cache_config = CacheConfig(
        cache_dir=Path(__file__).parent.parent / 'data' / 'cache',
        enabled_sources=['peoply.app', 'ifinavet.no']
    )
    
    # Initialize scrapers with cache config
    scrapers = [
        PeoplyScraper(cache_config=cache_config),
        NavetScraper(cache_config=cache_config)
    ]
    
    # Fetch and store events from each source
    for scraper in scrapers:
        try:
            logger.info(f"Fetching events from {scraper.name()}")
            events = scraper.get_events()
            logger.info(f"Found {len(events)} events from {scraper.name()}")
            
            # Store events in database
            for event in events:
                db.merge_event(event)
            
            logger.info(f"Successfully updated events from {scraper.name()}")
        except Exception as e:
            logger.error(f"Error fetching events from {scraper.name()}: {e}")
            continue

if __name__ == "__main__":
    main() 