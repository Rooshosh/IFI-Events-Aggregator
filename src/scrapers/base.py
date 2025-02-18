"""Base scraper class that all scrapers must inherit from."""

from typing import List
import json
from ..models.event import Event

class BaseScraper:
    """Base class for all scrapers."""
    
    def name(self) -> str:
        """Return the name of the scraper (e.g., 'peoply.app', 'ifinavet.no')."""
        raise NotImplementedError("Subclasses must implement name()")
    
    def get_events(self) -> List[Event]:
        """Get events from the source. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement get_events()")
    
    def _deserialize_events(self, json_str: str) -> List[Event]:
        """Deserialize JSON string into list of Event objects."""
        events_data = json.loads(json_str)
        return [Event.from_dict(event_data) for event_data in events_data] 