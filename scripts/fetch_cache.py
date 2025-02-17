#!/usr/bin/env python3

import logging
import sys
from pathlib import Path
import argparse

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.utils.cache import CacheConfig, CacheError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Fetch and cache data from a specific source"""
    parser = argparse.ArgumentParser(description='Fetch and cache data from a specific source')
    parser.add_argument('source', choices=['navet', 'peoply'], help='Source to fetch from')
    parser.add_argument('--force-live', action='store_true', help='Force fetching live data (required for initial cache)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    args = parser.parse_args()
    
    # Configure caching
    cache_config = CacheConfig(
        cache_dir=Path(__file__).parent.parent / 'data' / 'cache',
        enabled_sources=['peoply.app', 'ifinavet.no'],
        force_live=args.force_live
    )
    
    # Initialize the appropriate scraper
    if args.source == 'navet':
        scraper = NavetScraper(cache_config=cache_config)
    else:  # peoply
        scraper = PeoplyScraper(cache_config=cache_config)
    
    try:
        logger.info(f"{'Fetching live data from' if args.force_live else 'Loading cached data for'} {scraper.name()}")
        events = scraper.get_events()
        logger.info(f"Found {len(events)} events from {scraper.name()}")
        
        if args.debug:
            for event in events:
                logger.info(f"Event: {event.title}")
                logger.info(f"URL: {event.source_url}")
                logger.info("-" * 80)
        
        if args.force_live and len(events) > 0:
            logger.info("Data successfully cached")
        
    except CacheError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fetching events from {scraper.name()}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 