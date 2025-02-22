"""Scraper for Facebook group posts using BrightData's API."""

from datetime import datetime, timedelta
import logging
import time
from typing import List, Optional, Dict, Any
import requests
import json
from .base import BaseScraper
from ..models.event import Event
from ..utils.cache import CacheManager, CacheConfig, CacheError
from ..utils.decorators import cached_request
from ..utils.timezone import now_oslo, ensure_oslo_timezone
from ..config.sources import SOURCES
from ..utils.llm import init_openai, is_event_post, parse_event_details
from ..db import get_db
from sqlalchemy import func

logger = logging.getLogger(__name__)

class FacebookGroupScraper(BaseScraper):
    """
    Scraper for Facebook group posts using BrightData's API.
    
    This scraper uses BrightData's 'Facebook - Posts by group URL' dataset
    to fetch posts from the IFI Students Facebook group, then uses an LLM
    to identify and parse events from these posts.
    """
    
    def __init__(self, cache_config: CacheConfig = None):
        # Get configuration from sources
        config = SOURCES['facebook']
        brightdata_config = config.settings['brightdata']
        openai_config = config.settings['openai']
        
        self.base_url = config.base_url
        self.headers = {
            "Authorization": f"Bearer {brightdata_config['api_key']}",
            "Content-Type": "application/json",
        }
        self.params = {
            "dataset_id": brightdata_config['dataset_id'],
            "include_errors": "true",
        }
        self.group_url = brightdata_config['group_url']
        self.days_to_fetch = brightdata_config.get('days_to_fetch', 1)  # Default to 1 if not specified
        
        self.cache_config = cache_config or CacheConfig()
        self.cache_manager = CacheManager(self.cache_config.cache_dir)
        self.max_poll_attempts = 20  # Up to ~11.5 minutes total (90s + 19*30s)
        self.poll_interval = 30  # seconds
        self.initial_wait = 90  # seconds
        
        # Initialize OpenAI client (without caching)
        init_openai(openai_config['api_key'])
        self.openai_config = openai_config
    
    def name(self) -> str:
        """Return the name of the scraper."""
        return SOURCES['facebook'].name
    
    def _extract_post_id(self, url: str) -> Optional[str]:
        """Extract the post ID from a Facebook post URL."""
        if not url:
            return None
        try:
            return url.split('/posts/')[-1].strip('/')
        except Exception:
            logger.warning(f"Could not extract post ID from URL: {url}")
            return None

    def _get_event_urls_for_timeframe(self, num_days: int = 1) -> List[str]:
        """
        Get source URLs of events from the last N days.
        
        Args:
            num_days: Number of days to look back (default: 1 for today only)
        """
        db = get_db()
        try:
            # Get date range in Oslo timezone
            end_date = now_oslo().date()
            start_date = end_date - timedelta(days=num_days - 1)
            
            # Query for events in date range
            events = db.query(Event).filter(
                Event.source_name == self.name(),
                Event.created_at >= start_date
            ).all()
            
            return [event.source_url for event in events if event.source_url]
        finally:
            db.close()

    def _trigger_scrape(self) -> Optional[str]:
        """
        Trigger a new scrape of the Facebook group.
        
        Returns:
            snapshot_id if successful, None otherwise.
        """
        try:
            # Get date range in Oslo timezone
            end_date = now_oslo()
            start_date = end_date - timedelta(days=self.days_to_fetch - 1)
            
            # Format dates for API in MM-DD-YYYY format
            start_date_str = start_date.strftime("%m-%d-%Y")
            end_date_str = end_date.strftime("%m-%d-%Y")
            
            # Get URLs from the specified timeframe and extract post IDs
            urls = self._get_event_urls_for_timeframe(num_days=self.days_to_fetch)
            posts_to_exclude = [self._extract_post_id(url) for url in urls if url and self._extract_post_id(url)]
            
            data = [
                {
                    "url": self.group_url,
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "posts_to_not_include": posts_to_exclude
                }
            ]
            
            # Debug logging
            logger.info("Making request with:")
            logger.info(f"URL: {self.base_url}/trigger")
            logger.info(f"Headers: {self.headers}")
            logger.info(f"Params: {self.params}")
            logger.info(f"Data: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/trigger",
                headers=self.headers,
                params=self.params,
                json=data
            )
            
            # Debug response
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response text: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            if "snapshot_id" in result:
                logger.info(f"Successfully triggered scrape with snapshot_id: {result['snapshot_id']}")
                return result["snapshot_id"]
            else:
                logger.error(f"No snapshot_id in response: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Other error: {str(e)}")
            return None
    
    def _check_status(self, snapshot_id: str) -> bool:
        """
        Check the status of a scrape.
        Returns True if complete, False otherwise.
        """
        try:
            response = requests.get(
                f"{self.base_url}/progress/{snapshot_id}",
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Log the current status
            logger.debug(f"Scrape status for {snapshot_id}: {result}")
            
            # Check status field in response
            if isinstance(result, dict) and 'status' in result:
                status = result['status']
                logger.info(f"Current status: {status}")
                return status == "ready"
            
            # Fallback for old format
            return result == "ready"
            
        except Exception as e:
            logger.error(f"Error checking status for snapshot {snapshot_id}: {e}")
            return False
    
    def _fetch_posts_from_snapshot(self, snapshot_id: str) -> str:
        """
        Fetch posts directly from an existing snapshot ID.
        This is useful when we know a scrape has already completed.
        """
        try:
            response = requests.get(
                f"{self.base_url}/snapshot/{snapshot_id}",
                headers=self.headers,
                params={"format": "json"}
            )
            
            # Debug logging for request
            logger.info(f"Fetching snapshot with:")
            logger.info(f"URL: {self.base_url}/snapshot/{snapshot_id}")
            logger.info(f"Headers: {self.headers}")
            logger.info(f"Params: {{'format': 'json'}}")
            
            # Handle empty snapshots (returns 400 with "Snapshot is empty" message)
            if response.status_code == 400 and response.text.strip() == "Snapshot is empty":
                logger.info(f"Snapshot {snapshot_id} is empty, returning empty list")
                return json.dumps([])
            
            # For all other responses, check status code
            response.raise_for_status()
            results = response.json()
            
            logger.info(f"Successfully retrieved {len(results)} posts from snapshot {snapshot_id}")
            return json.dumps(results)
            
        except Exception as e:
            logger.error(f"Error retrieving results for snapshot {snapshot_id}: {e}")
            raise
    
    @cached_request(cache_key="latest_posts")
    def _fetch_posts(self, url: str = None, snapshot_id: str = None) -> str:
        """
        Fetch posts from the Facebook group.
        
        Args:
            url: Dummy parameter to satisfy the cached_request decorator.
                 Not actually used since we're using cache_key.
            snapshot_id: Optional snapshot ID to fetch from directly.
                        If provided, skips triggering a new scrape.
        """
        # If snapshot_id is provided, fetch directly from it
        if snapshot_id:
            return self._fetch_posts_from_snapshot(snapshot_id)
            
        # Otherwise, do the normal scrape process
        url = url or f"{self.base_url}/trigger"
        
        # Trigger new scrape
        snapshot_id = self._trigger_scrape()
        if not snapshot_id:
            raise Exception("Failed to trigger scrape")
        
        logger.info(f"Waiting initial {self.initial_wait} seconds for scrape to complete...")
        time.sleep(self.initial_wait)
        
        # Poll for completion
        attempts = 0
        while attempts < self.max_poll_attempts:
            if self._check_status(snapshot_id):
                # Get the results
                return self._fetch_posts_from_snapshot(snapshot_id)
            
            logger.info(f"Still waiting... (attempt {attempts + 1}/{self.max_poll_attempts})")
            time.sleep(self.poll_interval)
            attempts += 1
        
        raise Exception("Scrape timed out or failed to retrieve results")
    
    def _parse_post_to_event(self, post: Dict[str, Any]) -> Optional[Event]:
        """
        Use LLM to parse a Facebook post into an Event object.
        Returns None if the post is not about an event.
        """
        # First check if this is an event post
        content = post.get('content', '')
        
        # Add post date for correct date interpretation
        enriched_content = (
            f"Post metadata:\n"
            f"- Posted on: {post.get('date_posted', '')}\n"
            f"\nPost content:\n{content}"
        )
        
        is_event, explanation = is_event_post(enriched_content, self.openai_config)
        
        if not is_event:
            logger.debug(f"Post not detected as event: {explanation}")
            return None
        
        # Parse event details with enriched content
        event_data = parse_event_details(enriched_content, post.get('url', ''), self.openai_config)
        if not event_data:
            logger.error("Failed to parse event details")
            return None
            
        # Create Event object
        try:
            # Convert datetime strings to datetime objects with timezone
            start_time = ensure_oslo_timezone(datetime.fromisoformat(event_data['start_time']))
            end_time = None
            if event_data.get('end_time'):
                try:
                    end_time = ensure_oslo_timezone(datetime.fromisoformat(event_data['end_time']))
                except (ValueError, TypeError):
                    # If end_time is invalid, keep it as None
                    end_time = None
            
            # Get attachments (combine all relevant sources)
            attachment = None
            
            # First try to get an image URL from attachments
            if post.get('attachments'):
                for att in post['attachments']:
                    if isinstance(att, dict):
                        # Prefer actual image URLs over Facebook event links
                        if 'url' in att and 'attachment_url' not in att:  # Skip if it's a Facebook event
                            attachment = att['url']
                            break
                        elif isinstance(att, str):
                            attachment = att
                            break
            
            # If no image found in attachments, try post_external_image
            if not attachment and post.get('post_external_image'):
                if isinstance(post['post_external_image'], dict) and 'url' in post['post_external_image']:
                    attachment = post['post_external_image']['url']
                elif isinstance(post['post_external_image'], str):
                    attachment = post['post_external_image']
            
            # Finally, try post_external_link if no images found
            if not attachment and post.get('post_external_link'):
                attachment = post['post_external_link']
            
            # Convert post date to datetime with timezone
            created_at = None
            if post.get('date_posted'):
                try:
                    created_at = ensure_oslo_timezone(datetime.fromisoformat(post['date_posted']))
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date_posted: {post.get('date_posted')}")
            
            event = Event(
                title=event_data['title'],
                description=event_data['description'],
                start_time=start_time,
                end_time=end_time,
                location=event_data.get('location'),
                source_url=post.get('url', ''),
                source_name=self.name(),
                author=post.get('user_username_raw'),  # Direct mapping from post author
                attachment=attachment,  # Primary attachment URL
                created_at=created_at  # Post creation date
            )
            
            # Add food info to description if available
            if event_data.get('food'):
                event.description += f"\n\nServering: {event_data['food']}"
            
            # Add registration info to description if available
            if event_data.get('registration_info'):
                event.description += f"\n\nPåmelding: {event_data['registration_info']}"
            
            return event
            
        except Exception as e:
            logger.error(f"Error creating Event object: {e}")
            return None
    
    def get_events(self, snapshot_id: str = None) -> List[Event]:
        """
        Get events from Facebook group posts.
        
        Args:
            snapshot_id: Optional snapshot ID to fetch from directly
        """
        try:
            # Fetch posts (using cache if available)
            posts_json = self._fetch_posts(
                url=self.base_url + "/trigger",
                snapshot_id=snapshot_id
            )
            posts = json.loads(posts_json)
            
            # Filter out "no results" records (they have url=null and usually a warning message)
            valid_posts = [post for post in posts if post.get('url') is not None]
            if len(valid_posts) < len(posts):
                logger.info(f"Filtered out {len(posts) - len(valid_posts)} 'no results' records")
                if not valid_posts:
                    logger.info("No valid posts found in response")
                    return []
            
            # Find the date range of the fetched posts
            post_dates = []
            for post in valid_posts:
                try:
                    if post.get('date_posted'):
                        post_date = ensure_oslo_timezone(datetime.fromisoformat(post['date_posted'])).date()
                        post_dates.append(post_date)
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date_posted: {post.get('date_posted')}")
                    continue
            
            if not post_dates:
                logger.warning("No valid dates found in posts")
                return []
            
            # Get the date range
            start_date = min(post_dates)
            end_date = max(post_dates)
            logger.info(f"Posts span from {start_date} to {end_date}")
            
            # Get URLs of events we already have in the database for this date range
            db = get_db()
            try:
                # Use date() function on created_at for proper date comparison
                events = db.query(Event).filter(
                    Event.source_name == self.name(),
                    Event.created_at.isnot(None),  # Ensure we have a date
                    func.date(Event.created_at) >= start_date,
                    func.date(Event.created_at) <= end_date
                ).all()
                known_urls = {event.source_url for event in events if event.source_url}
            finally:
                db.close()
            
            # Filter out posts we already have in our database
            new_posts = [post for post in valid_posts if post.get('url') not in known_urls]
            if len(new_posts) < len(valid_posts):
                logger.info(f"Filtered out {len(valid_posts) - len(new_posts)} already known posts")
                if not new_posts:
                    logger.info("No new posts to process")
                    return []
            
            # Get the fetch timestamp
            meta = self.cache_manager.get_metadata(self.name(), 'latest_posts')
            fetch_time = datetime.fromisoformat(meta['cached_at']) if meta else now_oslo()
            
            # Parse posts into events (only new ones)
            events = []
            for post in new_posts:
                try:
                    event = self._parse_post_to_event(post)
                    if event:
                        event.fetched_at = fetch_time
                        event.source_name = self.name()
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing post: {e}")
                    continue
            
            logger.info(f"Found {len(events)} new events in {len(new_posts)} new posts")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events from {self.name()}: {e}")
            return [] 