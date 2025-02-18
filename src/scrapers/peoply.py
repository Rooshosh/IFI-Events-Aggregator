from datetime import datetime
from typing import List
import requests
import logging
import json
from .base import BaseScraper
from ..models.event import Event
from ..utils.cache import CacheManager, CacheConfig, CacheError
from ..utils.decorators import cached_request, cached_method
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from ..utils.timezone import now_oslo

logger = logging.getLogger(__name__)

class PeoplyScraper(BaseScraper):
    """Scraper for peoply.app events"""
    
    def __init__(self, cache_config: CacheConfig = None):
        self.base_url = "https://api.peoply.app"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.cache_config = cache_config or CacheConfig()
        self.cache_manager = CacheManager(self.cache_config.cache_dir)
    
    def name(self) -> str:
        return "peoply.app"
    
    def _get_api_url(self) -> str:
        """Generate the URL for peoply.app events API with the current date"""
        # Convert Oslo time to UTC for the API
        current_time = now_oslo().astimezone(ZoneInfo("UTC"))
        time_str = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        encoded_time = time_str.replace(':', '%3A')
        return f"{self.base_url}/events?afterDate={encoded_time}&orderBy=startDate"
    
    @cached_request(cache_key="events_list")
    def _fetch_json(self, url: str) -> str:
        """Fetch JSON content with caching support"""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.text  # Return raw response text
    
    def get_events(self) -> List[Event]:
        """Get events from peoply.app API"""
        try:
            # Fetch events from API (using cache if available)
            raw_response = self._fetch_json(self._get_api_url())
            api_events = json.loads(raw_response)
            logger.info(f"Found {len(api_events)} events from API")
            
            events = []
            for api_event in api_events[:10]:  # Limit to 10 most recent events
                try:
                    # Convert API event to our format
                    event = Event(
                        title=api_event['title'],
                        description=api_event['description'],
                        start_time=datetime.fromisoformat(api_event['startDate'].replace('Z', '+00:00')),
                        end_time=(
                            datetime.fromisoformat(api_event['endDate'].replace('Z', '+00:00'))
                            if api_event['endDate']
                            else datetime.fromisoformat(api_event['startDate'].replace('Z', '+00:00'))
                        ),
                        location=api_event['locationName'],
                        source_url=f"https://peoply.app/events/{api_event['urlId']}",
                        source_name=self.name()
                    )
                    
                    # Add additional location details if available
                    if api_event.get('freeformAddress'):
                        event.location = f"{api_event['locationName']}, {api_event['freeformAddress']}"
                    
                    # Add categories to description
                    categories = [cat['category']['name'] for cat in api_event.get('eventCategories', [])]
                    if categories:
                        event.description = f"{event.description}\n\nCategories: {', '.join(categories)}"
                    
                    # Add organizer info to description
                    for arranger in api_event.get('eventArrangers', []):
                        if arranger.get('role') == 'ADMIN':
                            if arranger['arranger'].get('organization'):
                                org = arranger['arranger']['organization']
                                event.description = f"Organized by: {org['name']}\n\n{event.description}"
                            elif arranger['arranger'].get('user'):
                                user = arranger['arranger']['user']
                                event.description = f"Organized by: {user['firstName']} {user['lastName']}\n\n{event.description}"
                            break
                    
                    events.append(event)
                    logger.info(f"Successfully parsed event: {event.title} ({event.start_time} - {event.end_time})")
                
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    continue
            
            return events

        except Exception as e:
            logger.error(f"Error fetching events from {self.name()}: {e}")
            return [] 