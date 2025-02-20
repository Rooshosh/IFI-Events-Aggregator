"""Utility decorators for caching and other cross-cutting concerns."""

import functools
from typing import Optional, Callable, Any
from urllib.parse import urlparse
from .cache import CacheManager, CacheConfig, CacheError
import logging

logger = logging.getLogger(__name__)

class CacheMissError(Exception):
    """Raised when cache is missing and live data fetch is not explicitly enabled."""
    pass

def cached_request(cache_key: Optional[str] = None):
    """
    Decorator for caching HTTP requests.
    
    Args:
        cache_key: Optional key to use for caching. If not provided,
                  will be generated from the URL parameter.
    
    The decorated function must:
    1. Have a 'url' parameter (positional or keyword)
    2. Be in a class that has cache_config and cache_manager attributes
    
    Example:
        @cached_request()
        def fetch_page(self, url: str) -> str:
            response = requests.get(url)
            return response.text
        
        @cached_request(cache_key="events_list")
        def fetch_events_page(self, url: str) -> str:
            response = requests.get(url)
            return response.text
            
    Raises:
        CacheMissError: When cache is missing and live data fetch is not explicitly enabled
    """
    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> str:
            # Get URL from args or kwargs
            url = kwargs.get('url')
            if url is None and args:
                url = args[0]
            if url is None:
                raise ValueError("URL parameter is required")
            
            # Get cache identifier
            identifier = cache_key
            if not identifier:
                parsed = urlparse(url)
                # Replace all slashes with underscores for consistent cache file names
                path = parsed.path.strip('/')
                identifier = path if path else 'root'
                identifier = identifier.replace('/', '_')
            
            # Check if we should use live data
            if not hasattr(self, 'cache_config'):
                force_live = True  # No cache config means always live
            else:
                force_live = self.cache_config.should_use_live(self.name())
            
            # Try to load from cache first if caching is enabled and we're not forcing live
            if (not force_live and
                hasattr(self, 'cache_config') and 
                hasattr(self, 'cache_manager') and 
                self.cache_config.is_cache_enabled(self.name())):
                try:
                    cached_content = self.cache_manager.load(self.name(), identifier)
                    if cached_content:
                        logger.debug(f"Loading cached content for {url}")
                        return cached_content
                except CacheError as e:
                    # If cache doesn't exist and we're not explicitly requesting live data,
                    # raise an error instead of silently falling back
                    if not force_live:
                        raise CacheMissError(
                            f"Cache miss for {url} and live data fetch not enabled. "
                            "Use --force-live or --live flag if you want to fetch live data."
                        ) from e
            
            # Fetch live data
            logger.info(f"Fetching fresh content from {url}")
            content = func(self, *args, **kwargs)
            
            # Cache the response if caching is enabled
            if (hasattr(self, 'cache_config') and 
                hasattr(self, 'cache_manager') and 
                self.cache_config.is_cache_enabled(self.name())):
                self.cache_manager.save(
                    self.name(),
                    identifier,
                    content,
                    metadata={'url': url}
                )
            
            return content
        return wrapper
    return decorator

def cached_method(cache_key: str):
    """
    Decorator for caching method results.
    
    Args:
        cache_key: Key to use for caching the result.
    
    The decorated method must be in a class that has cache_config
    and cache_manager attributes.
    
    Example:
        @cached_method("parsed_events")
        def parse_events(self, html: str) -> List[Event]:
            # Parse events from HTML
            return events
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            # Try to load from cache first if caching is enabled
            if (hasattr(self, 'cache_config') and 
                hasattr(self, 'cache_manager') and 
                self.cache_config.is_cache_enabled(self.name())):
                try:
                    cached_content = self.cache_manager.load(self.name(), cache_key)
                    if cached_content:
                        logger.debug(f"Loading cached result for {func.__name__}")
                        return cached_content
                except CacheError:
                    # Cache doesn't exist, check if we should compute
                    if not self.cache_config.should_use_live(self.name()):
                        raise CacheMissError(
                            f"No cache found for {func.__name__} and live data fetch not enabled. "
                            "Use --force-live or --live flag if you want to fetch live data."
                        )
                    logger.debug(f"No cache found for {func.__name__}, computing result")
            
            # Only compute if we're allowed to use live data
            if not self.cache_config.should_use_live(self.name()):
                raise CacheMissError(
                    f"Cache is disabled for {self.name()} and live data fetch not enabled. "
                    "Use --force-live or --live flag if you want to fetch live data."
                )
            
            # Compute result
            logger.info(f"Computing fresh result for {func.__name__}")
            result = func(self, *args, **kwargs)
            
            # Cache the result if caching is enabled
            if (hasattr(self, 'cache_config') and 
                hasattr(self, 'cache_manager') and 
                self.cache_config.is_cache_enabled(self.name())):
                self.cache_manager.save(
                    self.name(),
                    cache_key,
                    result,
                    metadata={'function': func.__name__}
                )
            
            return result
        return wrapper
    return decorator 