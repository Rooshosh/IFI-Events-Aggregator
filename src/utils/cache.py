from datetime import datetime
import json
from pathlib import Path
import logging
from typing import Optional, Dict, Any, Union, List

logger = logging.getLogger(__name__)

class CacheError(Exception):
    """Exception raised for cache-related errors"""
    pass

class CacheConfig:
    """Configuration for the caching system"""
    
    def __init__(self, cache_dir: Union[str, Path] = None, enabled_sources: List[str] = None, force_live: bool = False):
        self.cache_dir = Path(cache_dir) if cache_dir else Path('data/cache')
        self.enabled_sources = enabled_sources or []
        self.force_live = force_live
    
    def is_cache_enabled(self, source_name: str) -> bool:
        """Check if caching is enabled for a source"""
        return source_name in self.enabled_sources
        
    def should_use_live(self, source_name: str) -> bool:
        """Check if we should bypass cache and use live data"""
        return self.force_live

class CacheManager:
    """Manager for caching content from different sources"""
    
    def __init__(self, cache_dir: Union[str, Path]):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_source_cache_dir(self, source_name: str) -> Path:
        """Get the cache directory for a specific source"""
        source_dir = self.cache_dir / source_name.replace('.', '_')
        source_dir.mkdir(parents=True, exist_ok=True)
        return source_dir
    
    def get_cache_path(self, source_name: str, identifier: str, suffix: str = None) -> Path:
        """
        Generate a cache file path for a given source and identifier.
        
        Args:
            source_name: Name of the source (e.g., 'peoply.app', 'ifinavet.no')
            identifier: Unique identifier for the cached content
            suffix: Optional file extension (e.g., '.html', '.json'). If not provided,
                   defaults to '.json' for peoply.app and '.html' for other sources.
        """
        # Clean the identifier to be filesystem-friendly
        clean_id = "".join(c if c.isalnum() or c in '-_' else '_' for c in identifier)
        
        # Determine file extension based on source if not provided
        if suffix is None:
            suffix = '.json' if source_name == 'peoply.app' else '.html'
            
        return self.get_source_cache_dir(source_name) / f"{clean_id}{suffix}"
    
    def get_meta_path(self, cache_path: Path) -> Path:
        """Get the path for the cache metadata file"""
        return cache_path.with_suffix('.meta.json')
    
    def save(self, source_name: str, identifier: str, content: str, 
             metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save content to cache with metadata"""
        source_dir = self.get_source_cache_dir(source_name)
        
        # Get appropriate file path with extension
        content_file = self.get_cache_path(source_name, identifier)
        
        # Save content
        content_file.write_text(content, encoding='utf-8')
        
        # Save metadata
        if metadata:
            meta = {
                **metadata,
                'cached_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat()
            }
            meta_file = self.get_meta_path(content_file)
            meta_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
        
        logger.debug(f"Cached content for {source_name}/{identifier}")
    
    def load(self, source_name: str, identifier: str) -> Optional[str]:
        """Load content from cache if it exists"""
        # Get appropriate file path with extension
        content_file = self.get_cache_path(source_name, identifier)
        meta_file = self.get_meta_path(content_file)
        
        # Check if source directory exists and has any cached files
        source_dir = self.get_source_cache_dir(source_name)
        if not source_dir.exists() or not any(f for f in source_dir.glob('*.*') if not f.name.endswith('.meta.json')):
            msg = f"No cache found for {source_name} (cache directory empty or not found). To fetch live data, use --force-live flag."
            logger.error(msg)
            raise CacheError(msg)
        
        # Check if specific content exists
        if not content_file.exists():
            msg = f"No cached data found for {source_name}/{identifier}. To fetch live data, use --force-live flag."
            logger.error(msg)
            raise CacheError(msg)
        
        # Update last accessed time in metadata
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding='utf-8'))
                meta['last_accessed'] = datetime.now().isoformat()
                meta_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
            except json.JSONDecodeError:
                logger.warning(f"Failed to update metadata for {source_name}/{identifier}")
        
        logger.debug(f"Loading cached content for {source_name}/{identifier}")
        return content_file.read_text(encoding='utf-8')
    
    def clear(self, source_name: Optional[str] = None, 
             older_than: Optional[datetime] = None) -> int:
        """Clear cache files based on criteria"""
        cleared_count = 0
        
        if source_name:
            # Clear specific source
            source_dir = self.get_source_cache_dir(source_name)
            if not source_dir.exists():
                return 0
            
            # Find all cache files (both .html and .json, but not .meta.json)
            for cache_file in (f for f in source_dir.glob('*.*') if not f.name.endswith('.meta.json')):
                if self._should_clear(cache_file, older_than):
                    self._clear_cache_files(cache_file)
                    cleared_count += 1
        else:
            # Clear all sources
            for source_dir in self.cache_dir.iterdir():
                if source_dir.is_dir():
                    # Find all cache files (both .html and .json, but not .meta.json)
                    for cache_file in (f for f in source_dir.glob('*.*') if not f.name.endswith('.meta.json')):
                        if self._should_clear(cache_file, older_than):
                            self._clear_cache_files(cache_file)
                            cleared_count += 1
        
        return cleared_count
    
    def _should_clear(self, cache_file: Path, older_than: Optional[datetime]) -> bool:
        """Check if a cache file should be cleared based on criteria"""
        if not older_than:
            return True
        
        meta_file = cache_file.with_suffix('.meta.json')
        if not meta_file.exists():
            return True
        
        try:
            meta = json.loads(meta_file.read_text(encoding='utf-8'))
            cached_at = datetime.fromisoformat(meta['cached_at'])
            return cached_at < older_than
        except (json.JSONDecodeError, KeyError, ValueError):
            return True
    
    def _clear_cache_files(self, cache_file: Path) -> None:
        """Clear a cache file and its metadata"""
        meta_file = cache_file.with_suffix('.meta.json')
        
        try:
            cache_file.unlink()
            if meta_file.exists():
                meta_file.unlink()
        except OSError as e:
            logger.warning(f"Failed to clear cache file {cache_file}: {e}") 