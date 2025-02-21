"""Scraper for Facebook group posts using BrightData's API."""

from datetime import datetime
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
        self.num_posts = brightdata_config['num_posts']
        
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
    
    def _trigger_scrape(self) -> Optional[str]:
        """
        Trigger a new scrape of the Facebook group.
        Returns the snapshot_id if successful, None otherwise.
        """
        try:
            data = [
                {
                    "url": self.group_url,
                    "num_of_posts": self.num_posts,
                    "start_date": "",
                    "end_date": ""
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
    
    def _get_results(self, snapshot_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve the results of a completed scrape.
        Returns the list of posts if successful, None otherwise.
        """
        try:
            response = requests.get(
                f"{self.base_url}/snapshot/{snapshot_id}",
                headers=self.headers,
                params={"format": "json"}
            )
            response.raise_for_status()
            results = response.json()
            
            logger.info(f"Successfully retrieved results for snapshot {snapshot_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving results for snapshot {snapshot_id}: {e}")
            return None
    
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
        is_event, explanation = is_event_post(content, self.openai_config)
        
        if not is_event:
            logger.debug(f"Post not detected as event: {explanation}")
            return None
        
        # Parse event details
        event_data = parse_event_details(content, post.get('url', ''), self.openai_config)
        if not event_data:
            logger.error("Failed to parse event details")
            return None
            
        # Create Event object
        try:
            # Convert datetime strings to datetime objects with timezone
            start_time = ensure_oslo_timezone(datetime.fromisoformat(event_data['start_time']))
            end_time = None
            if event_data.get('end_time'):
                end_time = ensure_oslo_timezone(datetime.fromisoformat(event_data['end_time']))
            
            event = Event(
                title=event_data['title'],
                description=event_data['description'],
                start_time=start_time,
                end_time=end_time,
                location=event_data.get('location'),
                source_url=post.get('url', ''),
                source_name=self.name()
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
        """Get events from Facebook group posts."""
        try:
            # Fetch posts (using cache if available)
            posts_json = self._fetch_posts(
                url=self.base_url + "/trigger",
                snapshot_id=snapshot_id
            )
            posts = json.loads(posts_json)
            
            # Get the fetch timestamp
            meta = self.cache_manager.get_metadata(self.name(), 'latest_posts')
            fetch_time = datetime.fromisoformat(meta['cached_at']) if meta else now_oslo()
            
            # Parse posts into events
            events = []
            for post in posts:
                try:
                    event = self._parse_post_to_event(post)
                    if event:
                        event.fetched_at = fetch_time
                        event.source_name = self.name()
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing post: {e}")
                    continue
            
            logger.info(f"Found {len(events)} events in {len(posts)} posts")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events from {self.name()}: {e}")
            return [] 