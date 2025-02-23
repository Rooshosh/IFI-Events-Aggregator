#!/usr/bin/env python3

"""
This script provides a command-line interface for managing events in the IFI Events.

This script handles:
- Fetching events from different sources (Navet, Peoply, Facebook)
- Caching of raw API/web responses (to minimize calls to sources)
- Parsing events into our format
- Database storage of parsed events
- Event deduplication and management

Cache vs Database:
- Cache: Stores raw responses from APIs/web scraping to minimize calls to sources
- Database: Stores parsed events in our format for the web interface

Source-Specific Features:
- Facebook: Supports using existing snapshot IDs to avoid re-scraping
         Configurable wait times for scraping
         Debug mode to view raw posts
- Navet: HTML scraping with caching
- Peoply: API-based with caching

Related Scripts:
- fetch_cache.py: Testing tool focused on the caching system and raw data fetching
                 Useful for debugging scraping issues before database integration

For usage information, run:
    python events.py --help

Common use cases:
    # Fetch and store events (using cache by default)
    python events.py fetch

    # Force fresh data fetch (will update cache and store in DB)
    python events.py fetch --live

    # Just view events without storing in database
    python events.py fetch --no-store

    # Fetch Facebook events using existing snapshot
    python events.py fetch facebook --snapshot-id s_abc123 --detailed

    # Debug Facebook scraping
    python events.py fetch facebook --snapshot-id s_abc123 --debug --no-store
"""

import logging
import sys
from pathlib import Path
import argparse
from typing import List, Optional, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import text
import json
from logging.handlers import RotatingFileHandler
import os

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.db import init_db, get_db, close_db
from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.scrapers.facebook import FacebookGroupScraper
from src.utils.cache import CacheConfig
from src.models.event import Event
from src.utils.timezone import now_oslo
from src.utils.deduplication import check_duplicate_before_insert, deduplicate_database, DuplicateConfig

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'events.log'

# Configure logging to both file and console
handlers = []

# Always add console handler when LOG_TO_STDOUT is set
if os.environ.get('LOG_TO_STDOUT'):
    handlers.append(logging.StreamHandler(sys.stdout))
else:
    # In normal operation, use both file and console handlers
    handlers.extend([
        # Console handler
        logging.StreamHandler(),
        # File handler with rotation (keep 30 days of logs, max 10MB per file)
        RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=30,
            encoding='utf-8'
        )
    ])

logging.basicConfig(
    format='%(message)s' if os.environ.get('LOG_TO_STDOUT') else '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Set up loggers for all modules we want to control
for module in ['src.scrapers.peoply', 'src.scrapers.navet', 'src.db.database']:
    logging.getLogger(module).setLevel(logging.INFO)

def log_separator(level='source'):
    """Add a visual separator to the logs"""
    if level == 'source':
        # Shorter separator between sources with newlines
        logger.info('\n' + '-' * 50)
    elif level == 'fetch':
        # Longer separator between fetch operations with more newlines
        logger.info('\n\n' + '=' * 100)
        logger.info(f"Starting new fetch operation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info('=' * 100 + '\n')

# Add after imports, before main()
VALID_SOURCES = {
    'peoply': 'peoply.app',  # Fastest (API-based)
    'navet': 'ifinavet.no',  # Medium (HTML scraping)
    'facebook': 'facebook.group',  # Slowest (complex scraping with wait times)
    'all': None  # Special case handled in code
}

# Source mapping for database operations - using the same mapping as VALID_SOURCES
SOURCE_MAPPING = {k: v for k, v in VALID_SOURCES.items() if k != 'all'}

def get_scraper(source: str, cache_config: CacheConfig):
    """
    Get a scraper instance for the specified source.
    
    Args:
        source: Source identifier ('navet', 'peoply', or 'facebook')
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
    elif source == 'facebook':
        return FacebookGroupScraper(cache_config=cache_config)
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
        NavetScraper(cache_config=cache_config),
        FacebookGroupScraper(cache_config=cache_config)
    ]

def print_events_info(events: List[Event], detailed: bool = False, source: Optional[str] = None, debug: bool = False):
    """
    Print information about events.
    
    Args:
        events: List of events to display
        detailed: If True, shows all available event information
        source: Source of the events (for source-specific handling)
        debug: If True, shows additional debug information
    """
    logger.info(f"Found {len(events)} events")
    
    if detailed:
        for event in events:
            logger.info(event.to_detailed_string())
            
    # Show raw Facebook posts in debug mode
    if debug and source == 'facebook':
        scraper = FacebookGroupScraper(CacheConfig())
        try:
            posts_json = scraper._fetch_posts()
            posts = json.loads(posts_json)
            logger.info("\nRaw Facebook posts:")
            for post in posts:
                logger.info("-" * 80)
                logger.info(f"Post content: {post.get('content', 'No content')[:200]}...")
                logger.info(f"Post URL: {post.get('url', 'No URL')}")
        except Exception as e:
            logger.error(f"Error showing raw posts: {e}")
    else:
        for event in events:
            logger.info(event.to_summary_string())

def fetch_events(
    source: Optional[str] = None,
    use_cache: bool = True,
    store_db: bool = True,
    detailed_output: bool = False,
    quiet: bool = False,
    snapshot_id: Optional[str] = None,
    debug: bool = False,
    facebook_config: Optional[Dict[str, Any]] = None
) -> List[Event]:
    """
    Fetch events from specified source(s).
    
    Args:
        source: Specific source to fetch from, or None for all sources
        use_cache: Whether to use cached data (False means force live)
        store_db: Whether to store events in database (default True)
        detailed_output: Whether to print detailed event information
        quiet: Whether to reduce output verbosity
        snapshot_id: Optional snapshot ID for Facebook scraper
        debug: Whether to show debug information
        facebook_config: Optional configuration for Facebook scraper
    """
    # Add source separator if not quiet
    if not quiet and source:
        log_separator('source')
        logger.info(f"Processing source: {source}")
    
    # Set logging levels based on quiet mode
    if quiet:
        logging.getLogger('src.scrapers.peoply').setLevel(logging.WARNING)
        logging.getLogger('src.scrapers.navet').setLevel(logging.WARNING)
        logging.getLogger('src.db.database').setLevel(logging.WARNING)
        logger.setLevel(logging.WARNING)
    
    # Force live fetch if snapshot_id is provided
    if snapshot_id:
        use_cache = False
    
    # Configure cache based on parameters
    cache_config = CacheConfig(
        cache_dir=Path(__file__).parent.parent / 'data' / 'cache',
        enabled_sources=['peoply.app', 'ifinavet.no', 'facebook.group'],
        force_live=not use_cache
    )
    
    # Get appropriate scrapers
    scrapers = [get_scraper(source, cache_config)] if source else get_all_scrapers(cache_config)
    
    all_events = []
    total_stored = 0
    total_merged = 0
    
    # Get database session if we're storing events
    db = get_db() if store_db else None
    
    try:
        for scraper in scrapers:
            try:
                if not use_cache and not quiet:
                    logger.info(f"Fetching live data from {scraper.name()} (will update cache)")
                elif not quiet:
                    logger.info(f"Using cached data for {scraper.name()}")
                
                # Handle Facebook scraper differently due to snapshot support
                if isinstance(scraper, FacebookGroupScraper):
                    # Configure Facebook scraper if settings provided
                    if facebook_config:
                        scraper.initial_wait = facebook_config.get('initial_wait', scraper.initial_wait)
                        scraper.poll_interval = facebook_config.get('poll_interval', scraper.poll_interval)
                        scraper.max_poll_attempts = facebook_config.get('max_attempts', scraper.max_poll_attempts)
                    events = scraper.get_events(snapshot_id=snapshot_id)
                else:
                    events = scraper.get_events()
                
                if not quiet:
                    logger.info(f"Found {len(events)} events from {scraper.name()}")
                all_events.extend(events)
                
                # Store in database if enabled (default behavior)
                if store_db:
                    for event in events:
                        # Check for duplicates before adding
                        duplicate = check_duplicate_before_insert(event)
                        if duplicate:
                            # Use the merged event instead
                            db.merge(duplicate)
                            total_merged += 1
                            if not quiet:
                                logger.info(f"Merged duplicate event: {event.title}")
                        else:
                            # Add new event
                            db.add(event)
                            total_stored += 1
                    
                    if not quiet:
                        logger.info(f"Processed {len(events)} events from {scraper.name()} "
                                  f"({total_stored} new, {total_merged} merged)")
                elif not quiet:
                    logger.info("Events were not stored in database (--no-store flag used)")
                
                # Print detailed information if requested
                if detailed_output and not quiet:
                    print_events_info(events, detailed=True, source=source, debug=debug)
                
                # Add a newline after each source's summary
                if not quiet:
                    logger.info("")
            
            except Exception as e:
                logger.error(f"Error processing events from {scraper.name()}: {e}")
                continue
        
        # Commit changes if we're storing events
        if store_db:
            db.commit()
        
        # Always show total summary, even in quiet mode
        if store_db:
            logger.warning(f"Total: Found {len(all_events)} events "
                         f"({total_stored} new, {total_merged} merged)")
        else:
            logger.warning(f"Total: Found {len(all_events)} events (not stored in database)")
        
        return all_events
    
    finally:
        # Always close the database session if we opened one
        if store_db:
            close_db()

def get_event_by_id(event_id: int) -> Optional[Event]:
    """Get a single event from the database by ID"""
    db = get_db()
    try:
        return db.query(Event).filter(Event.id == event_id).first()
    finally:
        close_db()

def get_random_event() -> Optional[Event]:
    """Get a random event from the database"""
    db = get_db()
    try:
        # Use SQLite's random() function to get a random event
        return db.query(Event).order_by(text('RANDOM()')).first()
    finally:
        close_db()

def get_next_event() -> Optional[Event]:
    """Get the next upcoming event from the current date/time"""
    db = get_db()
    try:
        now = now_oslo()
        return db.query(Event).filter(Event.start_time > now).order_by(Event.start_time.asc()).first()
    finally:
        close_db()

def get_all_events(source: Optional[str] = None) -> List[Event]:
    """Get all events from the database, optionally filtered by source"""
    db = get_db()
    try:
        query = db.query(Event).order_by(Event.start_time.asc())
        if source:
            # Use consistent source mapping
            db_source = SOURCE_MAPPING[source]
            logger.info(f"[Source Debug] Filtering events by source: cli_source={source}, db_source={db_source}")
            query = query.filter(Event.source_name == db_source)
        events = query.all()
        logger.info(f"[Source Debug] Found {len(events)} events")
        for event in events:
            logger.debug(f"[Source Debug] Retrieved event: source={event.source_name}, title={event.title}")
        return events
    finally:
        close_db()

def clear_database(quiet: bool = False, source: Optional[str] = None) -> None:
    """
    Clear events from the database.
    
    Args:
        quiet: If True, suppress output messages
        source: Optional source to clear. If None, clears all events.
    """
    init_db()  # Ensure database is initialized
    db = get_db()
    try:
        # Build query
        query = db.query(Event)
        if source:
            logger.info(f"[Source Debug] Clearing events for source: {source}")
            query = query.filter(Event.source_name == source)
        
        # Delete events
        count = query.delete()
        db.commit()
        
        if not quiet:
            source_str = f" from {source}" if source else ""
            logger.info(f"[Source Debug] Cleared {count} events{source_str} from database")
    finally:
        close_db()

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='IFI Events management tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Fetch events from a specific source
  events.py fetch facebook
  
  # Fetch from all sources
  events.py fetch all
  
  # Fetch Facebook events from last 2 days
  events.py fetch facebook --days 2
  
  # List events from a specific source
  events.py list navet
  
  # List all events
  events.py list all
  
  # Clear events from a specific source
  events.py clear facebook
  
  # Clear all events
  events.py clear all
  
  # View a specific event by ID
  events.py show 1
  
  # View a random event
  events.py show r
  
  # View the next upcoming event
  events.py show n
  
  # Deduplicate events in database
  events.py deduplicate
  
  # Deduplicate with custom settings
  events.py deduplicate --title-similarity 0.7 --time-window 60
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Source-dependent commands (fetch, list, clear)
    fetch_parser = subparsers.add_parser('fetch', help='Fetch events from source')
    fetch_parser.add_argument('source', choices=list(VALID_SOURCES.keys()),
                            help='Source to fetch from (use "all" for all sources)')
    fetch_parser.add_argument('--live', action='store_true',
                            help='Force live data fetch (will update cache)')
    fetch_parser.add_argument('--no-store', action='store_true',
                            help='Do not store events in database (view only)')
    fetch_parser.add_argument('--detailed', action='store_true',
                            help='Show detailed information about events')
    fetch_parser.add_argument('--quiet', action='store_true',
                            help='Reduce output verbosity')
    fetch_parser.add_argument('--snapshot-id',
                            help='Use an existing snapshot ID for Facebook scraper')
    fetch_parser.add_argument('--debug', action='store_true',
                            help='Show debug information')
    
    list_parser = subparsers.add_parser('list', help='List events from database')
    list_parser.add_argument('source', choices=list(VALID_SOURCES.keys()),
                           help='Source to list (use "all" for all sources)')
    list_parser.add_argument('--detailed', action='store_true',
                           help='Show detailed information about events')
    
    clear_parser = subparsers.add_parser('clear', help='Clear events from database')
    clear_parser.add_argument('source', choices=list(VALID_SOURCES.keys()),
                            help='Source to clear (use "all" for all sources)')
    clear_parser.add_argument('--quiet', action='store_true',
                            help='Reduce output verbosity')
    
    # Source-independent commands (show, deduplicate)
    show_parser = subparsers.add_parser('show', help='Show specific event')
    show_parser.add_argument('event_id',
                           help='Event ID to show (use "r" for random event or "n" for next upcoming event)')
    
    dedup_parser = subparsers.add_parser('deduplicate', help='Deduplicate events in database')
    dedup_parser.add_argument('source', choices=list(VALID_SOURCES.keys()),
                           help='Source to deduplicate (use "all" for all sources)')
    dedup_parser.add_argument('--title-similarity', type=float, default=0.85,
                           help='Title similarity threshold (0-1, default: 0.85)')
    dedup_parser.add_argument('--time-window', type=int, default=120,
                           help='Time window in minutes for considering events duplicates (default: 120)')
    dedup_parser.add_argument('--require-location', action='store_true',
                           help='Require location to match for duplicate detection')
    dedup_parser.add_argument('--require-exact-time', action='store_true',
                           help='Require exact time match for duplicate detection')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Add fetch operation separator for fetch commands
    if args.command == 'fetch':
        log_separator('fetch')
    
    # Initialize database for commands that need it
    if args.command in ['show', 'list', 'deduplicate'] or (args.command == 'fetch' and not args.no_store):
        init_db()
    
    # Handle source-independent commands first
    if args.command == 'show':
        if args.event_id is None:
            parser.error(
                "The show command requires an argument:\n"
                "  - A numeric event ID (e.g., 'show 1')\n"
                "  - 'r' for a random event (e.g., 'show r')\n"
                "  - 'n' for the next upcoming event (e.g., 'show n')"
            )
        
        event = None
        if args.event_id.lower() == 'r':
            event = get_random_event()
            if not event:
                logger.error("No events found in the database")
                return
            logger.info("Showing random event:")
        elif args.event_id.lower() == 'n':
            event = get_next_event()
            if not event:
                logger.error("No upcoming events found")
                return
            logger.info("Showing next upcoming event:")
        else:
            try:
                event_id = int(args.event_id)
                event = get_event_by_id(event_id)
                if not event:
                    logger.error(f"No event found with ID {event_id}")
                    return
            except ValueError:
                parser.error(
                    f"Invalid event identifier '{args.event_id}'. Use:\n"
                    "  - A numeric event ID (e.g., 'show 1')\n"
                    "  - 'r' for a random event (e.g., 'show r')\n"
                    "  - 'n' for the next upcoming event (e.g., 'show n')"
                )
        
        if event:
            logger.info("Summary view:")
            logger.info(event.to_summary_string())
            logger.info("\nDetailed view:")
            logger.info(event.to_detailed_string())
            
    elif args.command == 'deduplicate':
        # Create config from command line arguments
        config = DuplicateConfig(
            title_similarity_threshold=args.title_similarity,
            time_window_minutes=args.time_window,
            require_same_location=args.require_location,
            require_exact_time=args.require_exact_time
        )
        
        # Run deduplication
        logger.info("[Source Debug] Starting database deduplication...")
        logger.info(f"Using settings:")
        logger.info(f"  - Title similarity threshold: {config.title_similarity_threshold}")
        logger.info(f"  - Time window: {config.time_window_minutes} minutes")
        logger.info(f"  - Require location match: {config.require_same_location}")
        logger.info(f"  - Require exact time: {config.require_exact_time}")
        
        # Get the database source name
        source_name = SOURCE_MAPPING[args.source] if args.source != 'all' else None
        logger.info(f"[Source Debug] Deduplicating with source: cli_source={args.source}, db_source={source_name}")

        # Run deduplication with source filtering
        duplicate_count, merged_events = deduplicate_database(config, source_name=source_name)
        
        logger.info(f"[Source Debug] Found and merged {duplicate_count} duplicate events")
        logger.info(f"[Source Debug] Database now contains {len(merged_events)} unique events")
        
    # Handle source-dependent commands
    else:
        # Convert source to list of sources to process
        sources = list(VALID_SOURCES.keys())[:-1] if args.source == 'all' else [args.source]
        
        if args.command == 'fetch':
            if not args.no_store:
                init_db()
            
            # Prepare Facebook configuration if needed
            facebook_config = None
            if 'facebook' in sources:
                facebook_config = {
                    'initial_wait': 90,  # Default values since we removed the arguments
                    'poll_interval': 30,
                    'max_attempts': 20
                }
            
            for source in sources:
                fetch_events(
                    source=source,
                    use_cache=not args.live,
                    store_db=not args.no_store,
                    detailed_output=args.detailed,
                    quiet=args.quiet,
                    snapshot_id=args.snapshot_id if source == 'facebook' else None,
                    debug=args.debug,
                    facebook_config=facebook_config if source == 'facebook' else None
                )
                
        elif args.command == 'list':
            init_db()
            for source in sources:
                # Use consistent source mapping
                db_source = SOURCE_MAPPING[source]
                logger.info(f"[Source Debug] Listing events for source: cli_source={source}, db_source={db_source}")
                events = get_all_events(source=source)
                if not events:
                    logger.error(f"No events found from {source}")
                    continue
                
                logger.info(f"Found {len(events)} events from {db_source}:")
                print_events_info(events, detailed=args.detailed)
                
        elif args.command == 'clear':
            for source in sources:
                clear_database(quiet=args.quiet, source=VALID_SOURCES[source])

        elif args.command == 'deduplicate':
            # Create config from command line arguments
            config = DuplicateConfig(
                title_similarity_threshold=args.title_similarity,
                time_window_minutes=args.time_window,
                require_same_location=args.require_location,
                require_exact_time=args.require_exact_time
            )

            for source in sources:
                # Run deduplication
                logger.info(f"Starting deduplication for {source}...")
                source_name = VALID_SOURCES[source]
                duplicate_count, merged_events = deduplicate_database(config, source_name=source_name)
                logger.info(f"Found and merged {duplicate_count} duplicate events for {source}")
                logger.info(f"Database now contains {len(merged_events)} unique events for {source}")

if __name__ == "__main__":
    main() 