import importlib
import logging
from typing import List, Type
from ..models.event import Event
from .base import BaseScraper
from ..config.sources import get_enabled_sources, SourceConfig

logger = logging.getLogger(__name__)

class SourceManager:
    """Manages event sources and their scrapers"""
    
    @staticmethod
    def get_scraper_class(config: SourceConfig) -> Type[BaseScraper]:
        """
        Dynamically import and return the scraper class from its string path
        Example path: 'src.scrapers.peoply.PeoplyScraper'
        """
        try:
            module_path, class_name = config.scraper_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load scraper class {config.scraper_class}: {e}")
            raise
    
    @staticmethod
    def initialize_scraper(config: SourceConfig) -> BaseScraper:
        """Initialize a scraper from its configuration"""
        scraper_class = SourceManager.get_scraper_class(config)
        return scraper_class(**config.settings) if config.settings else scraper_class()
    
    @staticmethod
    def get_events_from_source(config: SourceConfig) -> List[Event]:
        """Get events from a single source"""
        try:
            scraper = SourceManager.initialize_scraper(config)
            logger.info(f"Fetching events from {config.name}")
            events = scraper.scrape_events()
            logger.info(f"Found {len(events)} events from {config.name}")
            return events
        except Exception as e:
            logger.error(f"Error fetching events from {config.name}: {e}")
            return []
    
    @staticmethod
    def get_all_events() -> List[Event]:
        """Get events from all enabled sources"""
        all_events = []
        for source_id, config in get_enabled_sources().items():
            try:
                events = SourceManager.get_events_from_source(config)
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Failed to get events from {source_id}: {e}")
        return all_events 