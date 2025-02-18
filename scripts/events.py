#!/usr/bin/env python3

"""
IFI Events Management Tool

This script provides a command-line interface for managing events in the IFI Events Aggregator.
It handles:
- Fetching events from different sources (Navet, Peoply)
- Caching of raw API/web responses (to minimize calls to sources)
- Parsing events into our format
- Database storage of parsed events

Cache vs Database:
- Cache: Stores raw responses from APIs/web scraping to minimize calls to sources
- Database: Stores parsed events in our format for the web interface

For usage information, run:
    python events.py --help

Common use cases:
    # Fetch and store events (using cache by default)
    python events.py fetch

    # Force fresh data fetch (will update cache and store in DB)
    python events.py fetch --live

    # Just view events without storing in database
    python events.py fetch --no-store
"""

import logging
import sys
from pathlib import Path
import argparse
from typing import List, Optional

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.db.database import init_db, get_db
from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.utils.cache import CacheConfig
from src.models.event import Event

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up loggers for all modules we want to control
for module in ['src.scrapers.peoply', 'src.scrapers.navet', 'src.db.database']:
    logging.getLogger(module).setLevel(logging.INFO)

def get_scraper(source: str, cache_config: CacheConfig):
    """
    Get a scraper instance for the specified source.
    
    Args:
        source: Source identifier ('navet' or 'peoply')
        cache_config: Configuration for the cache behavior
    
    Returns:
        An initialized scraper instance
    
    Raises:
        ValueError: If the source is not recognized
    """
    if source == 'navet':
        return NavetScraper(cache_config=cache_config)
    elif source == 'peoply':
        return PeoplyScraper(cache_config=cache_config)
    else:
        raise ValueError(f"Unknown source: {source}")

def get_all_scrapers(cache_config: CacheConfig):
    """
    Get all available scrapers.
    
    Args:
        cache_config: Configuration for the cache behavior
    
    Returns:
        List of initialized scraper instances
    """
    return [
        PeoplyScraper(cache_config=cache_config),
        NavetScraper(cache_config=cache_config)
    ]

def print_events_info(events: List[Event], detailed: bool = False):
    """
    Print information about events.
    
    Args:
        events: List of events to display
        detailed: If True, shows all available event information.
                 If False, shows only count.
    """
    logger.info(f"Found {len(events)} events")
    
    if detailed:
        for event in events:
            logger.info("-" * 80)
            logger.info(f"Title: {event.title}")
            logger.info(f"Start: {event.start_time}")
            logger.info(f"End: {event.end_time}")
            logger.info(f"Location: {event.location}")
            logger.info(f"Source: {event.source_name}")
            logger.info(f"URL: {event.source_url}")
            if event.capacity is not None:
                logger.info(f"Capacity: {event.capacity}")
            if event.spots_left is not None:
                logger.info(f"Spots Left: {event.spots_left}")
            if event.food:
                logger.info(f"Food: {event.food}")

def fetch_events(
    source: Optional[str] = None,
    use_cache: bool = True,
    store_db: bool = True,
    detailed_output: bool = False,
    quiet: bool = False
) -> List[Event]:
    """
    Fetch events from specified source(s).
    
    This function handles:
    - Fetching events from one or all sources
    - Using cached or live data (always updates cache with live data)
    - Storing events in database (default behavior)
    - Displaying event information
    
    Args:
        source: Specific source to fetch from, or None for all sources
        use_cache: Whether to use cached data (False means force live)
        store_db: Whether to store events in database (default True)
        detailed_output: Whether to print detailed event information
        quiet: Whether to reduce output verbosity
    
    Returns:
        List of fetched events
    """
    # Set logging levels based on quiet mode
    if quiet:
        logging.getLogger('src.scrapers.peoply').setLevel(logging.WARNING)
        logging.getLogger('src.scrapers.navet').setLevel(logging.WARNING)
        logging.getLogger('src.db.database').setLevel(logging.WARNING)
        logger.setLevel(logging.WARNING)
    
    # Configure cache based on parameters
    cache_config = CacheConfig(
        cache_dir=Path(__file__).parent.parent / 'data' / 'cache',
        enabled_sources=['peoply.app', 'ifinavet.no'],
        force_live=not use_cache
    )
    
    # Get appropriate scrapers
    scrapers = [get_scraper(source, cache_config)] if source else get_all_scrapers(cache_config)
    
    all_events = []
    total_stored = 0
    
    for scraper in scrapers:
        try:
            if not use_cache and not quiet:
                logger.info(f"Fetching live data from {scraper.name()} (will update cache)")
            elif not quiet:
                logger.info(f"Using cached data for {scraper.name()}")
            
            events = scraper.get_events()
            if not quiet:
                logger.info(f"Found {len(events)} events from {scraper.name()}")
            all_events.extend(events)
            
            # Store in database if enabled (default behavior)
            if store_db:
                db = get_db()
                for event in events:
                    db.merge_event(event)
                total_stored += len(events)
                if not quiet:
                    logger.info(f"Stored {len(events)} events in database from {scraper.name()}")
            elif not quiet:
                logger.info("Events were not stored in database (--no-store flag used)")
        
        except Exception as e:
            logger.error(f"Error processing events from {scraper.name()}: {e}")
            continue
    
    # Print detailed information if requested
    if detailed_output and not quiet:
        print_events_info(all_events, detailed=True)
    
    # Always show total summary, even in quiet mode
    if store_db:
        logger.warning(f"Total: Found {len(all_events)} events, stored {total_stored} in database")
    else:
        logger.warning(f"Total: Found {len(all_events)} events (not stored in database)")
    
    return all_events

def main():
    """Main CLI interface for the events management tool."""
    parser = argparse.ArgumentParser(
        description='IFI Events management tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch and store all events (using cache by default)
  %(prog)s fetch
  
  # Force fresh data fetch (will update cache and store in DB)
  %(prog)s fetch --live
  
  # Just view events without storing in database
  %(prog)s fetch --no-store
  
  # View detailed event information
  %(prog)s fetch --detailed
        """
    )
    
    parser.add_argument(
        'command',
        choices=['fetch'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--source',
        choices=['navet', 'peoply'],
        help='Specific source to fetch from (default: all sources)'
    )
    
    parser.add_argument(
        '--live',
        action='store_true',
        help='Force live data fetch (will update cache)'
    )
    
    parser.add_argument(
        '--no-store',
        action='store_true',
        help='Do not store events in database (view only)'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed information about events'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )
    
    args = parser.parse_args()
    
    # Initialize database if we're going to use it
    if not args.no_store:
        init_db()
    
    if args.command == 'fetch':
        fetch_events(
            source=args.source,
            use_cache=not args.live,
            store_db=not args.no_store,
            detailed_output=args.detailed,
            quiet=args.quiet
        )

if __name__ == "__main__":
    main() 