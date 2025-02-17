from datetime import datetime
from typing import List
import requests
import logging
from .base import BaseScraper
from ..models.event import Event

logger = logging.getLogger(__name__)

class PeoplyScraper(BaseScraper):
    """Scraper for Peoply.app events using their API"""
    
    def __init__(self):
        self.base_url = "https://api.peoply.app"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def name(self) -> str:
        return "peoply.app"
    
    def _get_api_url(self) -> str:
        """Generate the URL for peoply.app events API with the current date"""
        current_time = datetime.utcnow()
        time_str = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        encoded_time = time_str.replace(':', '%3A')
        return f"{self.base_url}/events?afterDate={encoded_time}&orderBy=startDate"
    
    def scrape_events(self) -> List[Event]:
        """Get events from peoply.app API"""
        try:
            url = self._get_api_url()
            logger.info(f"Fetching events from API: {url}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            api_events = response.json()
            logger.info(f"Found {len(api_events)} events from API")
            
            events = []
            for api_event in api_events:
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
            logger.error(f"Error fetching Peoply events: {e}")
            return [] 