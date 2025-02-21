#!/usr/bin/env python3

"""
IFI Events Cache Testing Tool

This script is a testing and debugging tool focused on the caching system and raw data fetching.
Unlike events.py which handles the complete event management pipeline, this script is designed
for testing and debugging the data fetching and caching layers in isolation.

Key Features:
- Test raw data fetching from sources without database integration
- Verify caching behavior
- Debug source-specific scraping issues
- View raw data before event parsing

Source-Specific Features:
- Facebook: 
  * Test snapshot creation and retrieval
  * Configure wait times for scraping
  * View raw post content
  * Use existing snapshots
- Navet: Test HTML scraping and caching
- Peoply: Test API responses and caching

Usage:
    # Test Facebook scraping with new snapshot
    python scripts/fetch_cache.py facebook --live

    # Use existing snapshot
    python scripts/fetch_cache.py facebook --snapshot-id s_abc123

    # Debug Facebook scraping
    python scripts/fetch_cache.py facebook --snapshot-id s_abc123 --debug

Related Scripts:
- events.py: Main event management tool that handles the complete pipeline
            including database storage and event management

Note: This script is primarily for development and debugging. For production
event management, use events.py instead.
"""

import logging
import sys
from pathlib import Path
import argparse
import json

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.scrapers.navet import NavetScraper
from src.scrapers.peoply import PeoplyScraper
from src.scrapers.facebook import FacebookGroupScraper
from src.utils.cache import CacheConfig, CacheError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Fetch and cache data from a specific source"""
    parser = argparse.ArgumentParser(description='Fetch and cache data from a specific source')
    parser.add_argument('source', choices=['navet', 'peoply', 'facebook'], help='Source to fetch from')
    parser.add_argument('--live', action='store_true', help='Force fetching live data (required for initial cache)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    
    # Add Facebook-specific arguments
    parser.add_argument('--initial-wait', type=int, default=90,
                      help='Initial wait time in seconds for Facebook scraper (default: 90)')
    parser.add_argument('--poll-interval', type=int, default=30,
                      help='Poll interval in seconds for Facebook scraper (default: 30)')
    parser.add_argument('--max-attempts', type=int, default=20,
                      help='Maximum number of polling attempts for Facebook scraper (default: 20)')
    parser.add_argument('--snapshot-id',
                      help='Use an existing snapshot ID instead of triggering a new scrape')
    
    args = parser.parse_args()
    
    # Configure caching
    cache_config = CacheConfig(
        cache_dir=Path(__file__).parent.parent / 'data' / 'cache',
        enabled_sources=['peoply.app', 'ifinavet.no', 'facebook.group'],
        force_live=args.live
    )
    
    # Initialize the appropriate scraper
    if args.source == 'navet':
        scraper = NavetScraper(cache_config=cache_config)
    elif args.source == 'peoply':
        scraper = PeoplyScraper(cache_config=cache_config)
    else:  # facebook
        scraper = FacebookGroupScraper(cache_config=cache_config)
        # Configure wait times if provided
        scraper.initial_wait = args.initial_wait
        scraper.poll_interval = args.poll_interval
        scraper.max_poll_attempts = args.max_attempts
    
    try:
        logger.info(f"{'Fetching live data from' if args.live else 'Loading cached data for'} {scraper.name()}")
        
        if args.source == 'facebook':
            # For Facebook, first get the raw posts to verify scraping works
            logger.info("Fetching Facebook posts (before event parsing)...")
            try:
                posts_json = scraper._fetch_posts(
                    url=scraper.base_url + "/trigger",
                    snapshot_id=args.snapshot_id
                )
                posts = json.loads(posts_json)
                logger.info(f"Successfully fetched {len(posts)} posts from Facebook group")
                
                # Explicitly save to cache if we got data
                if args.live and posts:
                    scraper.cache_manager.save(
                        scraper.name(),
                        "latest_posts",
                        posts_json,
                        metadata={'url': scraper.base_url + "/trigger"}
                    )
                    logger.info("Successfully cached Facebook posts")
                
                if args.debug:
                    for post in posts:
                        logger.info("-" * 80)
                        logger.info(f"Post content: {post.get('content', 'No content')[:200]}...")
                        logger.info(f"Post URL: {post.get('url', 'No URL')}")
            except Exception as e:
                logger.error(f"Error fetching Facebook posts: {e}")
                if args.debug:
                    logger.exception("Detailed error:")
                sys.exit(1)
        
        # Now try getting events (this will be empty for Facebook until we implement LLM parsing)
        events = scraper.get_events(snapshot_id=args.snapshot_id) if args.source == 'facebook' else scraper.get_events()
        logger.info(f"Found {len(events)} events from {scraper.name()}")
        
        if args.debug and args.source != 'facebook':
            for event in events:
                logger.info(f"Event: {event.title}")
                logger.info(f"URL: {event.source_url}")
                logger.info("-" * 80)
        
        if args.live and (len(events) > 0 or args.source == 'facebook'):
            logger.info("Data successfully cached")
        
    except CacheError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fetching events from {scraper.name()}: {e}")
        if args.debug:
            logger.exception("Detailed error:")
        sys.exit(1)

if __name__ == "__main__":
    main() 