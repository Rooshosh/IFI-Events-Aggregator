from dataclasses import dataclass
from typing import Dict, Any
import os
from pathlib import Path

@dataclass
class CacheConfig:
    """Configuration for cache behavior"""
    enabled: bool = True  # Whether caching is enabled globally
    cache_dir: Path = Path(__file__).parent.parent.parent / 'data' / 'cache'
    force_live: bool = False  # When True, bypass cache and fetch live data

    # Per-source cache settings
    source_settings: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.source_settings is None:
            self.source_settings = {
                'navet': {
                    'enabled': True,
                    'force_live': False,
                },
                'peoply': {
                    'enabled': True,
                    'force_live': False,
                }
            }
    
    def is_cache_enabled(self, source_name: str) -> bool:
        """Check if caching is enabled for a specific source"""
        if not self.enabled:
            return False
        source_config = self.source_settings.get(source_name, {})
        return source_config.get('enabled', True)
    
    def should_use_live(self, source_name: str) -> bool:
        """Check if we should bypass cache and use live data"""
        if self.force_live:
            return True
        source_config = self.source_settings.get(source_name, {})
        return source_config.get('force_live', False)
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """Create config from environment variables"""
        return cls(
            enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            cache_dir=Path(os.getenv('CACHE_DIR', str(cls.cache_dir))),
            force_live=os.getenv('FORCE_LIVE', 'false').lower() == 'true'
        ) 