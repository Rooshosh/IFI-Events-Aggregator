from dataclasses import dataclass
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class SourceConfig:
    """Configuration for an event source"""
    name: str
    enabled: bool
    base_url: str
    scraper_class: str  # Full path to scraper class
    settings: Optional[Dict[str, Any]] = None

# OpenAI configuration for event parsing
OPENAI_CONFIG = {
    'api_key': os.getenv('OPENAI_API_KEY'),  # OpenAI API key from environment
    'model': 'gpt-4o-mini',  # Model that works with the API
    'temperature': 0.3,  # Lower temperature for more consistent outputs
    'max_tokens': 1000
}
    
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
                'api_key': os.getenv('BRIGHTDATA_API_KEY'),
                'dataset_id': 'gd_lz11l67o2cb3r0lkj3',  # Brightdata dataset identifier
                'group_url': 'https://www.facebook.com/groups/ifistudenter'
            },
            'openai': OPENAI_CONFIG
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