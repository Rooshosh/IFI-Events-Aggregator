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
from ..utils.timezone import now_oslo
from ..config.sources import SOURCES

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
        self.max_poll_attempts = 12  # 2 minutes total with 10-second intervals
        self.poll_interval = 10  # seconds
    
    def name(self) -> str:
        """Return the name of the scraper."""
        return SOURCES['facebook'].name
    
    def _trigger_scrape(self) -> Optional[str]:
        """
        Trigger a new scrape of the Facebook group.
        Returns the snapshot_id if successful, None otherwise.
        """
        try:
            data = [{
                "url": self.group_url,
                "num_of_posts": self.num_posts,
                "start_date": "",
                "end_date": ""
            }]
            
            response = requests.post(
                f"{self.base_url}/trigger",
                headers=self.headers,
                params=self.params,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            if "snapshot_id" in result:
                logger.info(f"Successfully triggered scrape with snapshot_id: {result['snapshot_id']}")
                return result["snapshot_id"]
            else:
                logger.error(f"No snapshot_id in response: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error triggering scrape: {e}")
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
            
            # Return True if status is "ready"
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
    
    @cached_request(cache_key="latest_posts")
    def _fetch_posts(self) -> str:
        """
        Fetch posts from the Facebook group.
        This method handles the complete process:
        1. Trigger the scrape
        2. Poll until complete
        3. Retrieve and return results
        
        The response is cached using the cached_request decorator.
        """
        # Trigger new scrape
        snapshot_id = self._trigger_scrape()
        if not snapshot_id:
            raise Exception("Failed to trigger scrape")
        
        # Poll for completion
        attempts = 0
        while attempts < self.max_poll_attempts:
            if self._check_status(snapshot_id):
                # Get the results
                results = self._get_results(snapshot_id)
                if results:
                    # Convert results to string for caching
                    return json.dumps(results)
                break
            
            logger.info(f"Waiting for scrape completion (attempt {attempts + 1}/{self.max_poll_attempts})")
            time.sleep(self.poll_interval)
            attempts += 1
        
        raise Exception("Scrape timed out or failed to retrieve results")
    
    def _parse_post_to_event(self, post: Dict[str, Any]) -> Optional[Event]:
        """
        Use LLM to parse a Facebook post into an Event object.
        Returns None if the post is not about an event.
        """
        # TODO: Implement LLM parsing
        pass
    
    def get_events(self) -> List[Event]:
        """Get events from Facebook group posts."""
        try:
            # Fetch posts (using cache if available)
            posts_json = self._fetch_posts()
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