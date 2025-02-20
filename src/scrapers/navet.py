"""Scraper for ifinavet.no events"""

from datetime import datetime, timedelta
import logging
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse
import os
import json
from pathlib import Path
from .base import BaseScraper
from ..models.event import Event
from ..utils.cache import CacheConfig, CacheManager, CacheError
from ..utils.decorators import cached_request, cached_method
from ..utils.timezone import ensure_oslo_timezone

logger = logging.getLogger(__name__)

class NavetScraper(BaseScraper):
    """
    Scraper for ifinavet.no events.
    
    This scraper was developed based on detailed analysis of the Navet website structure.
    The analysis tools and findings are stored in tools/analysis/ifinavet_no/:
    
    Analysis Scripts:
    - navet_structure_analysis.py: Analyzes events listing page structure
    - navet_page_analysis.py: Analyzes individual event page structures
    - navet_event_analysis.py: Analyzes event data formats
    
    Analysis Results:
    - navet_analysis_results.json: Structure analysis results
    - navet_detailed_analysis.json: Event data format findings
    
    The analysis helped:
    1. Understand the HTML structure of event pages
    2. Identify patterns in event data presentation
    3. Determine optimal scraping approach
    4. Document website structure for future updates
    
    Note: If the website structure changes, refer to the analysis tools to:
    - Update the scraper
    - Understand scraping decisions
    - Analyze new features
    """
    
    def __init__(self, cache_config: CacheConfig = None):
        self.base_url = "https://ifinavet.no"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.cache_config = cache_config or CacheConfig()
        self.cache_manager = CacheManager(self.cache_config.cache_dir)
    
    def name(self) -> str:
        return "ifinavet.no"
    
    @cached_request()
    def _fetch_html(self, url: str) -> str:
        """Fetch HTML content with caching support"""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.text
    
    def _parse_date_time(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into a datetime object"""
        # Example: "tirsdag 28.01" and "16:15"
        try:
            # Extract day and month from the date string (format: "tirsdag 28.01")
            # Split on whitespace and take the last part (28.01)
            date_parts = date_str.strip().split()[-1].split('.')
            if len(date_parts) != 2:
                raise ValueError(f"Invalid date format: {date_str}")
            
            day = int(date_parts[0])
            month = int(date_parts[1])
            
            # Extract hours and minutes from time string (format: "16:15")
            time_parts = time_str.strip().split(':')
            if len(time_parts) != 2:
                raise ValueError(f"Invalid time format: {time_str}")
            
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # Construct datetime (using current year as events are typically not more than a year in advance)
            current_year = datetime.now().year
            naive_dt = datetime(current_year, month, day, hour, minute)
            return ensure_oslo_timezone(naive_dt)
            
        except Exception as e:
            logger.error(f"Error parsing date/time: {date_str} {time_str} - {str(e)}")
            raise
    
    def _parse_end_time(self, time_str: str, start_time: datetime) -> datetime:
        """Parse end time string and combine with start date"""
        # Example: "16:15"
        # For Navet events, if no end time is specified, assume 2 hours duration
        try:
            return start_time + timedelta(hours=2)
        except Exception as e:
            logger.error(f"Error parsing end time: {time_str} - {str(e)}")
            raise
    
    def _parse_capacity(self, capacity_str: str) -> Optional[int]:
        """Parse capacity string to integer"""
        try:
            return int(''.join(filter(str.isdigit, capacity_str)))
        except (ValueError, TypeError):
            return None
    
    def _get_event_url(self, onclick: str) -> str:
        """Extract event URL from onclick attribute"""
        # Example: "location.href='/arrangementer/2025/var/bedriftspresentasjon-med-dnb'"
        url_path = onclick.split("'")[1]
        return urljoin(self.base_url, url_path)
    
    @cached_request()
    def _fetch_event_details(self, url: str) -> str:
        """Fetch event details page"""
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.text
    
    def _parse_event_details(self, event: Event, html: str) -> Event:
        """Parse event details from HTML"""
        if not event.source_url:
            logger.warning(f"No source URL available for event: {event.title}")
            return event
            
        try:
            logger.info(f"Fetching details for event: {event.title}")
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the main container
            container = soup.find('div', class_='container')
            if not container:
                logger.warning(f"Could not find container for event: {event.title}")
                return event
            
            # Get event meta information from the card
            card = container.find('div', class_='card')
            if card:
                # Find all event meta rows
                meta_rows = card.find_all('div', class_='row center-xs')
                for row in meta_rows:
                    meta_items = row.find_all('div', class_='event-meta')
                    for meta in meta_items:
                        # Get the icon and value
                        icon = meta.find('span', class_=lambda x: x and x.startswith('icon-'))
                        value_span = meta.find('span', class_=None)
                        if not icon or not value_span:
                            continue
                            
                        icon_class = icon.get('class', [''])[0]
                        value = value_span.text.strip()
                        
                        # Handle different meta types
                        if 'icon-location' in icon_class:
                            event.location = value
                        elif 'icon-spoon-knife' in icon_class:
                            # Keep the food text as is, including emojis
                            event.food = value
                        elif 'icon-users' in icon_class:
                            try:
                                event.spots_left = int(''.join(filter(str.isdigit, value)))
                            except ValueError:
                                logger.warning(f"Could not parse spots left from: {value}")
            
            # Get registration information
            registration_status = card.find('h3', class_='event-status')
            if registration_status:
                status_text = registration_status.text.strip()
                if 'påmelding' in status_text.lower():
                    # Add registration status to description
                    event.description += f"\n\nPåmeldingsstatus: {status_text}"
            
            # Get detailed description from the card
            if card:
                description_parts = []
                
                # Get all text content after h2 (excluding meta information at the top)
                h2 = card.find('h2')
                if h2:
                    # Add the h2 title
                    description_parts.append(h2.text.strip())
                    
                    # Get all following paragraphs and lists
                    for elem in h2.find_next_siblings(['p', 'ul']):
                        if elem.name == 'ul':
                            # For lists, format each item
                            items = [f"- {li.text.strip()}" for li in elem.find_all('li')]
                            description_parts.append('\n'.join(items))
                        else:
                            # For links in paragraphs, include the URL
                            text_parts = []
                            for content in elem.contents:
                                if content.name == 'a':
                                    href = content.get('href', '')
                                    if href and href != content.text:
                                        text_parts.append(f"{content.text} ({href})")
                                    else:
                                        text_parts.append(content.text)
                                else:
                                    text_parts.append(str(content))
                            description_parts.append(''.join(text_parts).strip())
                
                if description_parts:
                    event.description = '\n\n'.join(description_parts)
            
            # Get company information
            company_card = container.find('div', class_='company-card')
            if company_card:
                company_info = company_card.find('div', class_='company-info')
                if company_info:
                    # Get company name
                    company_name = company_info.find('h2')
                    company_desc = company_info.find('p')
                    
                    company_parts = []
                    if company_name:
                        company_parts.append(f"Om {company_name.text.strip()}:")
                    if company_desc:
                        company_parts.append(company_desc.text.strip())
                    
                    if company_parts:
                        event.description += "\n\n" + "\n".join(company_parts)
            
            return event
            
        except Exception as e:
            logger.error(f"Error fetching details for event {event.title}: {e}")
            return event
            
    def get_events(self) -> List[Event]:
        """Get events from ifinavet.no"""
        try:
            # Fetch main page HTML (using cache if available)
            url = f"{self.base_url}/arrangementer/2025/var/"
            html = self._fetch_html(url)
            
            # Get the fetch timestamp from cache metadata
            meta = self.cache_manager.get_metadata(self.name(), 'arrangementer_2025_var')
            fetch_time = datetime.fromisoformat(meta['cached_at']) if meta else now_oslo()
            
            # Process the HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the event list container
            container = soup.find('div', class_='event-list-container')
            if not container:
                logger.error("Could not find event list container")
                return []
            
            # Find all event cards within the container
            event_cards = container.find_all('div', class_='event-list-item-wrapper', recursive=True)
            logger.info(f"Found {len(event_cards)} event cards")
            
            events = []
            for event_card in event_cards:
                event = self._parse_event_card(event_card)
                if event:
                    # Set the fetch time
                    event.fetched_at = fetch_time
                    # Fetch additional details for each event (using cache if available)
                    details_html = self._fetch_html(event.source_url)
                    event = self._parse_event_details(event, details_html)
                    events.append(event)
            
            logger.info(f"Successfully parsed {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events from {self.name()}: {e}")
            return []
    
    def _parse_event_card(self, event_item: BeautifulSoup) -> Optional[Event]:
        """Parse a single event card into an Event object"""
        try:
            # Get basic event information from the description section
            desc_container = event_item.find('div', class_='event-list-item-description')
            if not desc_container:
                logger.warning("Could not find description container")
                return None
            
            # Find the title within the description container
            title_elem = desc_container.find('h3', class_='event-list-item-title')
            if not title_elem:
                logger.warning("Could not find title element")
                return None
            
            # Title is inside an <a> tag
            title_link = title_elem.find('a')
            if not title_link:
                logger.warning("Could not find title link")
                return None
            title = title_link.text.strip()
            
            # Description is in a <p> tag within the same container
            desc_elem = desc_container.find('p')
            if not desc_elem:
                logger.warning(f"Could not find description element for event: {title}")
                description = "Mer info kommer"  # Default for events without description
            else:
                description = desc_elem.text.strip()
            
            # Get meta information from the details section
            details = desc_container.find('div', class_='event-list-item-details')
            if not details:
                logger.warning(f"Could not find details section for event: {title}")
                return None
            
            meta_items = details.find_all('div', class_='event-list-item-meta')
            date_str = None
            time_str = None
            capacity_str = None
            
            for meta in meta_items:
                # Find the non-sr-only span (the one without a class)
                spans = meta.find_all('span')
                value_span = next((span for span in spans if not span.get('class')), None)
                if not value_span:
                    continue
                
                if 'icon-clock2' in str(meta):
                    time_str = value_span.text.strip()
                elif 'icon-calendar' in str(meta):
                    # Handle line break in date
                    date_parts = [text.strip() for text in value_span.stripped_strings]
                    date_str = ' '.join(date_parts)
                elif 'icon-users' in str(meta):
                    capacity_str = value_span.text.strip()
            
            if not all([date_str, time_str]):
                logger.warning(f"Missing date or time information for event: {title}")
                return None
            
            # Parse date and time
            try:
                start_time = self._parse_date_time(date_str, time_str)
                end_time = self._parse_end_time(time_str, start_time)
            except Exception as e:
                logger.error(f"Error parsing date/time for event {title}: {e}")
                return None
            
            # Get event URL from the wrapper div's onclick attribute
            onclick = event_item.get('onclick', '')
            source_url = self._get_event_url(onclick) if onclick else None
            
            # Get company name from the logo alt text
            company_logo = event_item.find('img')
            company_name = company_logo.get('alt', '') if company_logo else None
            
            # Create Event object
            return Event(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=None,  # Location is not available on the card
                source_url=source_url,
                source_name=self.name(),
                capacity=self._parse_capacity(capacity_str) if capacity_str else None
            )
        
        except Exception as e:
            logger.error(f"Error parsing event card: {e}")
            return None
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear the cache. If older_than_days is specified, only clear files older than that.
        Returns the number of files cleared.
        """
        if not self.cache_config.cache_dir.exists():
            return 0
        
        cleared_count = 0
        for cache_file in self.cache_config.cache_dir.glob('*.html'):
            should_clear = True
            meta_file = self._get_cache_meta_path(cache_file)
            
            if older_than_days and meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    fetched_at = datetime.fromisoformat(meta['fetched_at'])
                    age = datetime.now() - fetched_at
                    should_clear = age.days >= older_than_days
                except (json.JSONDecodeError, KeyError, ValueError):
                    # If we can't read the metadata, clear the file
                    pass
            
            if should_clear:
                try:
                    cache_file.unlink()
                    if meta_file.exists():
                        meta_file.unlink()
                    cleared_count += 1
                except OSError as e:
                    logger.error(f"Error clearing cache file {cache_file}: {e}")
        
        return cleared_count 