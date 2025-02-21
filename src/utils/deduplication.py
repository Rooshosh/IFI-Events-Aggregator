from datetime import datetime, timedelta
import sqlite3
import logging
from typing import Optional, List, Tuple, Any, Dict, Callable
from difflib import SequenceMatcher
from sqlalchemy import inspect, DateTime
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
        require_same_source: bool = True,  # Whether events must be from the same source
    ):
        self.title_similarity_threshold = title_similarity_threshold
        self.time_window_minutes = time_window_minutes
        self.require_same_location = require_same_location
        self.require_exact_time = require_exact_time
        self.ignore_case = ignore_case
        self.normalize_whitespace = normalize_whitespace
        self.require_same_source = require_same_source

# Special merge strategies for specific fields
EVENT_MERGE_STRATEGIES: Dict[str, Callable[[Event, Event], Any]] = {
    'id': lambda e1, e2: (e1.id if (e1.created_at and e2.created_at and e1.created_at < e2.created_at) 
                         else (e2.id if e2.created_at else e1.id)),
    'description': lambda e1, e2: (
        f"{e1.description}\n\nAlternative description:\n{e2.description}"
        if (e2.description and e2.description != e1.description)
        else e1.description
    ),
    'start_time': lambda e1, e2: min(e1.start_time, e2.start_time),
    'end_time': lambda e1, e2: max(e1.end_time, e2.end_time) if (e1.end_time and e2.end_time) else (e1.end_time or e2.end_time),
    'created_at': lambda e1, e2: min(e1.created_at, e2.created_at) if (e1.created_at and e2.created_at) else (e1.created_at or e2.created_at),
    'registration_opens': lambda e1, e2: min(e1.registration_opens, e2.registration_opens) if (e1.registration_opens and e2.registration_opens) else (e1.registration_opens or e2.registration_opens),
    'source_name': lambda e1, e2: (
        ', '.join([e1.source_name, e2.source_name]) 
        if (e1.source_name and e2.source_name and e1.source_name != e2.source_name)
        else (e1.source_name or e2.source_name)
    )
}

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
    # Check source if required
    if config.require_same_source:
        if not event1.source_name or not event2.source_name or event1.source_name != event2.source_name:
            return False
    
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
    Always uses data from the newer event (based on fetched_at timestamp).
    If fetched_at is the same, keeps existing data.
    
    Args:
        event1: First event (typically the existing one in the database)
        event2: Second event (typically the new one being considered)
    
    Returns:
        Event: Merged event object
    """
    # Determine which event is newer
    event1_time = event1.fetched_at or datetime.min.replace(tzinfo=event1.start_time.tzinfo)
    event2_time = event2.fetched_at or datetime.min.replace(tzinfo=event2.start_time.tzinfo)
    
    # If event2 is newer, use all its data
    if event2_time > event1_time:
        # Keep the id and created_at from event1 if it exists
        event2.id = event1.id if event1.id else event2.id
        event2.created_at = event1.created_at if event1.created_at else event2.created_at
        return event2
    
    # If same timestamp or event1 is newer, keep event1
    return event1

def _get_event_columns() -> List[str]:
    """Get all column names from the Event model"""
    return [c.key for c in inspect(Event).mapper.column_attrs]

def _get_datetime_columns() -> List[str]:
    """Get names of all datetime columns from the Event model"""
    return [c.key for c in inspect(Event).mapper.column_attrs 
            if isinstance(c.columns[0].type, DateTime)]

def _build_select_query(columns: List[str], where_clause: str = "") -> str:
    """Build a SELECT query for events"""
    return f"""
        SELECT {', '.join(columns)}
        FROM events
        {where_clause}
    """

def _row_to_event(row: Tuple[Any, ...], columns: List[str]) -> Optional[Event]:
    """Convert a database row to an Event object"""
    try:
        # Create dict of column names to values
        values = {}
        datetime_columns = _get_datetime_columns()
        
        for i, column in enumerate(columns):
            value = row[i]
            # Handle datetime fields
            if value and column in datetime_columns:
                value = datetime.fromisoformat(value)
            values[column] = value
        return Event(**values)
    except Exception as e:
        logger.warning(f"Failed to parse event {row[0] if row else 'unknown'}: {e}")
        return None

def _find_and_merge_duplicates(events: List[Event], config: DuplicateConfig) -> Tuple[List[Event], int]:
    """
    Find and merge duplicates in a list of events.
    Returns (merged_events, duplicate_count).
    """
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
    
    return merged_events, duplicate_count

def deduplicate_database(db_path: str, config: DuplicateConfig = DuplicateConfig()) -> Tuple[int, List[Event]]:
    """
    Deduplicate events in the database.
    Returns tuple of (number of duplicates found, list of merged events)
    """
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        
        # Get all columns and build query
        columns = _get_event_columns()
        query = _build_select_query(columns, "ORDER BY created_at ASC")
        
        # Get all events
        c.execute(query)
        
        # Convert to Event objects
        events = []
        for row in c.fetchall():
            event = _row_to_event(row, columns)
            if event:
                events.append(event)
        
        # Find and merge duplicates
        merged_events, duplicate_count = _find_and_merge_duplicates(events, config)
        
        # Update database with merged events
        c.execute('DELETE FROM events')
        
        # Build insert query using same columns
        placeholders = ', '.join(['?' for _ in columns])
        insert_query = f"""
            INSERT INTO events ({', '.join(columns)})
            VALUES ({placeholders})
        """
        
        # Insert merged events
        for event in merged_events:
            values = []
            for column in columns:
                value = getattr(event, column)
                # Convert datetime to string
                if isinstance(value, datetime):
                    value = value.isoformat()
                values.append(value)
            c.execute(insert_query, values)
        
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
        
        # Get all columns and build query
        columns = _get_event_columns()
        query = _build_select_query(
            columns,
            "WHERE start_time BETWEEN ? AND ?"
        )
        
        c.execute(query, (start_time_min, start_time_max))
        
        # Check each potential duplicate
        for row in c.fetchall():
            existing_event = _row_to_event(row, columns)
            if existing_event and are_events_duplicate(new_event, existing_event, config):
                return merge_events(existing_event, new_event)
    
    return None 