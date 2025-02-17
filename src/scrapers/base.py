from abc import ABC, abstractmethod
from typing import List
from ..models.event import Event

class BaseScraper(ABC):
    """Base class for all event scrapers"""
    
    @abstractmethod
    def scrape_events(self) -> List[Event]:
        """
        Scrape events from the source.
        Returns a list of Event objects.
        """
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Return the name of the scraper/event source"""
        pass 