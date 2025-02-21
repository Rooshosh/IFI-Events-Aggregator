#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.db.database import init_db, get_db, close_db
from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.utils.cache import CacheConfig
from src.utils.deduplication import check_duplicate_before_insert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Update events in database from all sources"""
    # Initialize database
    init_db()
    db = get_db()
    
    try:
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
        total_new = 0
        total_merged = 0
        
        for scraper in scrapers:
            try:
                logger.info(f"Fetching events from {scraper.name()}")
                events = scraper.get_events()
                logger.info(f"Found {len(events)} events from {scraper.name()}")
                
                # Store events in database with deduplication
                new_count = 0
                merged_count = 0
                
                for event in events:
                    # Check for duplicates
                    duplicate = check_duplicate_before_insert(event)
                    if duplicate:
                        # Use the merged event instead
                        db.merge(duplicate)
                        merged_count += 1
                    else:
                        # Add new event
                        db.add(event)
                        new_count += 1
                
                total_new += new_count
                total_merged += merged_count
                
                logger.info(f"Processed {len(events)} events from {scraper.name()} "
                          f"({new_count} new, {merged_count} merged)")
            except Exception as e:
                logger.error(f"Error fetching events from {scraper.name()}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully updated all events "
                   f"({total_new} new, {total_merged} merged)")
    
    finally:
        # Always close the database session
        close_db()

if __name__ == '__main__':
    main() 