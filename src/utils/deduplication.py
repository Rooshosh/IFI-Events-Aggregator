from datetime import datetime, timedelta
import sqlite3
import logging
from typing import Optional, List, Tuple
from difflib import SequenceMatcher
from ..models.event import Event

logger = logging.getLogger(__name__)

class DuplicateConfig:
    """Configuration for duplicate detection"""
    def __init__(
        self,
        title_similarity_threshold: float = 0.85,  # How similar titles need to be (0-1)
        time_window_minutes: int = 120,  # How close in time events need to be
        require_same_location: bool = False,  # Whether location must match
        require_exact_time: bool = False,  # Whether times must match exactly
        ignore_case: bool = True,  # Whether to ignore case in string comparisons
        normalize_whitespace: bool = True,  # Whether to normalize whitespace in strings
    ):
        self.title_similarity_threshold = title_similarity_threshold
        self.time_window_minutes = time_window_minutes
        self.require_same_location = require_same_location
        self.require_exact_time = require_exact_time
        self.ignore_case = ignore_case
        self.normalize_whitespace = normalize_whitespace

def normalize_string(text: str, config: DuplicateConfig) -> str:
    """Normalize string based on config"""
    if not text:
        return ""
    if config.ignore_case:
        text = text.lower()
    if config.normalize_whitespace:
        text = ' '.join(text.split())
    return text

def calculate_title_similarity(title1: str, title2: str, config: DuplicateConfig) -> float:
    """
    Calculate similarity between two titles.
    Currently uses a simple ratio, but could be enhanced with better algorithms.
    """
    title1 = normalize_string(title1, config)
    title2 = normalize_string(title2, config)
    
    return SequenceMatcher(None, title1, title2).ratio()

def are_events_duplicate(event1: Event, event2: Event, config: DuplicateConfig = DuplicateConfig()) -> bool:
    """
    Check if two events are duplicates based on the given configuration.
    Returns True if events are considered duplicates, False otherwise.
    """
    # Check title similarity
    title_similarity = calculate_title_similarity(event1.title, event2.title, config)
    if title_similarity < config.title_similarity_threshold:
        return False
    
    # Check times
    if config.require_exact_time:
        if event1.start_time != event2.start_time or event1.end_time != event2.end_time:
            return False
    else:
        time_window = timedelta(minutes=config.time_window_minutes)
        if abs(event1.start_time - event2.start_time) > time_window:
            return False
    
    # Check location if required
    if config.require_same_location:
        loc1 = normalize_string(event1.location or "", config)
        loc2 = normalize_string(event2.location or "", config)
        if loc1 != loc2:
            return False
    
    return True

def merge_events(event1: Event, event2: Event) -> Event:
    """
    Merge two events that are considered duplicates.
    Takes the most complete information from both events.
    """
    # Always keep the earlier created event's ID if available
    id_to_keep = None
    if event1.created_at and event2.created_at:
        id_to_keep = event1.id if event1.created_at < event2.created_at else event2.id
    else:
        id_to_keep = event1.id or event2.id
    
    # Merge descriptions if they're different
    description = event1.description
    if event2.description and event2.description != event1.description:
        description = f"{event1.description}\n\nAlternative description:\n{event2.description}"
    
    # Take the most precise location
    location = event1.location or event2.location
    
    # Combine source information
    source_urls = list(filter(None, [event1.source_url, event2.source_url]))
    source_names = list(filter(None, [event1.source_name, event2.source_name]))
    
    # Take the earliest registration opening time
    registration_opens = None
    if event1.registration_opens and event2.registration_opens:
        registration_opens = min(event1.registration_opens, event2.registration_opens)
    else:
        registration_opens = event1.registration_opens or event2.registration_opens
    
    # Take the first registration URL
    registration_urls = list(filter(None, [event1.registration_url, event2.registration_url]))
    
    # Take the most complete capacity information
    capacity = event1.capacity or event2.capacity
    spots_left = event1.spots_left or event2.spots_left
    food = event1.food or event2.food
    
    return Event(
        id=id_to_keep,
        title=event1.title,  # Keep the title from the first event
        description=description,
        start_time=min(event1.start_time, event2.start_time),
        end_time=max(event1.end_time, event2.end_time),
        location=location,
        source_url=source_urls[0] if source_urls else None,  # Keep first source URL
        source_name=', '.join(source_names) if len(source_names) > 1 else (source_names[0] if source_names else None),
        created_at=min(event1.created_at, event2.created_at) if (event1.created_at and event2.created_at) else (event1.created_at or event2.created_at),
        capacity=capacity,
        spots_left=spots_left,
        food=food,
        registration_opens=registration_opens,
        registration_url=registration_urls[0] if registration_urls else None
    )

def deduplicate_database(db_path: str, config: DuplicateConfig = DuplicateConfig()) -> Tuple[int, List[Event]]:
    """
    Deduplicate events in the database.
    Returns tuple of (number of duplicates found, list of merged events)
    """
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        
        # Get all events
        c.execute('''
            SELECT id, title, description, start_time, end_time, 
                   location, source_url, source_name, created_at,
                   food, capacity, spots_left, registration_opens,
                   registration_url
            FROM events
            ORDER BY created_at ASC
        ''')
        
        # Convert to Event objects
        events = []
        for row in c.fetchall():
            try:
                events.append(Event(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    start_time=datetime.fromisoformat(row[3]),
                    end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    location=row[5],
                    source_url=row[6],
                    source_name=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    food=row[9],
                    capacity=row[10],
                    spots_left=row[11],
                    registration_opens=datetime.fromisoformat(row[12]) if row[12] else None,
                    registration_url=row[13]
                ))
            except Exception as e:
                logger.warning(f"Failed to parse event {row[0]}: {e}")
                continue
        
        # Find and merge duplicates
        merged_events = []
        duplicate_count = 0
        processed_ids = set()
        
        for i, event1 in enumerate(events):
            if event1.id in processed_ids:
                continue
                
            current_event = event1
            for j, event2 in enumerate(events[i+1:], i+1):
                if event2.id in processed_ids:
                    continue
                    
                if are_events_duplicate(current_event, event2, config):
                    current_event = merge_events(current_event, event2)
                    processed_ids.add(event2.id)
                    duplicate_count += 1
                    logger.info(f"Found duplicate: '{event2.title}' matches '{event1.title}'")
            
            merged_events.append(current_event)
            processed_ids.add(event1.id)
        
        # Update database with merged events
        c.execute('DELETE FROM events')
        
        for event in merged_events:
            c.execute('''
                INSERT INTO events (
                    id, title, description, start_time, end_time,
                    location, source_url, source_name, created_at,
                    food, capacity, spots_left, registration_opens,
                    registration_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.id,
                event.title,
                event.description,
                event.start_time.isoformat(),
                event.end_time.isoformat() if event.end_time else None,
                event.location,
                event.source_url,
                event.source_name,
                event.created_at.isoformat() if event.created_at else None,
                event.food,
                event.capacity,
                event.spots_left,
                event.registration_opens.isoformat() if event.registration_opens else None,
                event.registration_url
            ))
        
        conn.commit()
        
        return duplicate_count, merged_events

def check_duplicate_before_insert(new_event: Event, db_path: str, config: DuplicateConfig = DuplicateConfig()) -> Optional[Event]:
    """
    Check if an event already exists in the database before inserting.
    Returns merged event if duplicate found, None otherwise.
    """
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        
        # Get potential duplicates within time window
        time_window = timedelta(minutes=config.time_window_minutes)
        start_time_min = (new_event.start_time - time_window).isoformat()
        start_time_max = (new_event.start_time + time_window).isoformat()
        
        c.execute('''
            SELECT id, title, description, start_time, end_time,
                   location, source_url, source_name, created_at,
                   food, capacity, spots_left, registration_opens,
                   registration_url
            FROM events
            WHERE start_time BETWEEN ? AND ?
        ''', (start_time_min, start_time_max))
        
        for row in c.fetchall():
            try:
                existing_event = Event(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    start_time=datetime.fromisoformat(row[3]),
                    end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    location=row[5],
                    source_url=row[6],
                    source_name=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    food=row[9],
                    capacity=row[10],
                    spots_left=row[11],
                    registration_opens=datetime.fromisoformat(row[12]) if row[12] else None,
                    registration_url=row[13]
                )
                
                if are_events_duplicate(new_event, existing_event, config):
                    return merge_events(existing_event, new_event)
            except Exception as e:
                logger.warning(f"Failed to parse event {row[0]}: {e}")
                continue
    
    return None 