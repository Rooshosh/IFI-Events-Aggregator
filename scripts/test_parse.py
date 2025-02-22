#!/usr/bin/env python3

"""
Test script for parsing a single Facebook post from cache.
Usage: 
    python test_parse.py --url <post_url>  # Parse specific post by URL
    python test_parse.py --list            # List all available posts
    python test_parse.py --url <post_url> --save  # Parse and save to database
"""

import sys
from pathlib import Path
import json
import logging
import argparse

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.scrapers.facebook import FacebookGroupScraper
from src.utils.cache import CacheConfig
from src.db import init_db, get_db, close_db
from src.utils.deduplication import check_duplicate_before_insert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_post_by_url(posts, url):
    """Find a post in the cache by its URL"""
    for post in posts:
        if post.get('url') == url:
            return post
    return None

def save_event_to_db(event):
    """Save an event to the database, handling duplicates"""
    try:
        db = get_db()
        # Check for duplicates
        duplicate = check_duplicate_before_insert(event)
        if duplicate:
            logger.info("Found duplicate event, merging...")
            db.merge(duplicate)
            logger.info("Event merged successfully")
        else:
            db.add(event)
            logger.info("New event added to database")
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving event to database: {e}")
        return False
    finally:
        close_db()

def main():
    """Parse a single post from cache"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test parsing a single Facebook post from cache')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--url', type=str, help='URL of the post to parse')
    group.add_argument('--list', action='store_true', help='List all available posts with their URLs')
    parser.add_argument('--save', action='store_true', help='Save the parsed event to the database')
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = FacebookGroupScraper(CacheConfig())
    
    # Load cached posts
    cache_path = Path(__file__).parent.parent / 'data' / 'cache' / 'facebook_group' / 'latest_posts.json'
    with open(cache_path) as f:
        posts = json.load(f)
    
    # List all posts if requested
    if args.list:
        logger.info(f"\nAvailable posts ({len(posts)} total):")
        for post in posts:
            preview = post.get('content', '')[:100] + '...' if len(post.get('content', '')) > 100 else post.get('content', '')
            logger.info(f"\nURL: {post.get('url', '')}")
            logger.info(f"Posted on: {post.get('date_posted', '')}")
            logger.info(f"Content: {preview}")
        return
    
    # If no URL provided, show usage
    if not args.url:
        parser.print_help()
        return
    
    # Find post by URL
    post = find_post_by_url(posts, args.url)
    if not post:
        logger.error(f"No post found with URL: {args.url}")
        logger.info("Use --list to see all available posts and their URLs")
        return
    
    # Show the raw post
    logger.info("\nRaw post data:")
    logger.info(f"Content: {post.get('content', '')}")
    logger.info(f"Posted on: {post.get('date_posted', '')}")
    logger.info(f"URL: {post.get('url', '')}")
    logger.info("-" * 80)
    
    # Parse the post
    event = scraper._parse_post_to_event(post)
    
    if event:
        logger.info("Parsed event:")
        logger.info(f"Title: {event.title}")
        logger.info(f"Start time: {event.start_time}")
        logger.info(f"End time: {event.end_time}")
        logger.info(f"Location: {event.location}")
        logger.info(f"Description: {event.description}")
        
        # Save to database if requested
        if args.save:
            logger.info("\nSaving event to database...")
            init_db()  # Initialize database
            if save_event_to_db(event):
                logger.info("Event saved successfully")
            else:
                logger.error("Failed to save event")
    else:
        logger.info("Post was not parsed as an event")

if __name__ == "__main__":
    main() 