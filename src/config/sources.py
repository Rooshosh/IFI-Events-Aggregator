from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class SourceConfig:
    """Configuration for an event source"""
    name: str
    enabled: bool
    base_url: str
    scraper_class: str  # Full path to scraper class
    settings: Optional[Dict[str, Any]] = None
    
# Default configurations for each source
SOURCES = {
    'peoply': SourceConfig(
        name='peoply.app',
        enabled=True,
        base_url='https://api.peoply.app',
        scraper_class='src.scrapers.peoply.PeoplyScraper',
        settings={}
    ),
    'navet': SourceConfig(
        name='ifinavet.no',
        enabled=True,  # Enabling the scraper
        base_url='https://ifinavet.no',
        scraper_class='src.scrapers.navet.NavetScraper',
        settings={}
    ),
    'facebook': SourceConfig(
        name='facebook.group',
        enabled=True,
        base_url='https://api.brightdata.com/datasets/v3',
        scraper_class='src.scrapers.facebook.FacebookGroupScraper',
        settings={
            'brightdata': {
                'api_key': 'c31afca61c5b7e52a708ac4d5f6fa75d4a406f8da9c91220283e8a68441531cd',
                'dataset_id': 'gd_lz11l67o2cb3r0lkj3',
                'group_url': 'https://www.facebook.com/groups/ifistudenter',
                'num_posts': 10
            }
        }
    )
}

def get_enabled_sources() -> Dict[str, SourceConfig]:
    """Get all enabled sources"""
    return {k: v for k, v in SOURCES.items() if v.enabled}

def enable_source(source_id: str) -> None:
    """Enable a specific source"""
    if source_id in SOURCES:
        SOURCES[source_id].enabled = True

def disable_source(source_id: str) -> None:
    """Disable a specific source"""
    if source_id in SOURCES:
        SOURCES[source_id].enabled = False 