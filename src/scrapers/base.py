from abc import ABC, abstractmethod
from typing import List
from ..models.event import Event

class BaseScraper(ABC):
    """Base class for event scrapers"""
    
    @abstractmethod
    def name(self) -> str:
        """Get the name of the scraper/source"""
        pass
    
    @abstractmethod
    def get_events(self) -> List[Event]:
        """Get events from the source"""
        pass 