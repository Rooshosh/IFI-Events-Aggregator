from datetime import datetime, timedelta
import logging
from typing import Optional, List, Tuple, Any, Dict, Callable
from difflib import SequenceMatcher
from ..models.event import Event
from ..db import get_db, close_db, init_db

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
        # If both events have the same source, keep it
        e1.source_name if e1.source_name == e2.source_name
        # If only one has a source, use that one
        else (e1.source_name or e2.source_name)
        # If they have different sources, join them (this should rarely happen due to require_same_source)
    ),
    'attachments': lambda e1, e2: (
        list(set(e1.attachments or []) | set(e2.attachments or []))  # Combine unique attachments from both events
        if (e1.attachments or e2.attachments)
        else []
    ),
    'author': lambda e1, e2: (
        f"{e1.author}, {e2.author}"
        if (e1.author and e2.author and e1.author != e2.author)
        else (e1.author or e2.author)
    )
}

def merge_events(event1: Event, event2: Event) -> Event:
    """
    Merge two events that are considered duplicates.
    Always uses data from the newer event (based on fetched_at timestamp) as a base,
    but applies special merge strategies for certain fields.
    
    Args:
        event1: First event (typically the existing one in the database)
        event2: Second event (typically the new one being considered)
    
    Returns:
        Event: Merged event object
    """
    # Determine which event is newer
    event1_time = event1.fetched_at or datetime.min.replace(tzinfo=event1.start_time.tzinfo)
    event2_time = event2.fetched_at or datetime.min.replace(tzinfo=event2.start_time.tzinfo)
    
    # Create a copy of the newer event as the base
    base_event = event2 if event2_time > event1_time else event1
    other_event = event1 if event2_time > event1_time else event2
    
    # Preserve source_name if both events are from the same source
    source_name = None
    if base_event.source_name == other_event.source_name:
        source_name = base_event.source_name
    
    # Apply special merge strategies
    for field, strategy in EVENT_MERGE_STRATEGIES.items():
        try:
            merged_value = strategy(base_event, other_event)
            setattr(base_event, field, merged_value)
        except Exception as e:
            logger.warning(f"Failed to apply merge strategy for {field}: {e}")
    
    # Ensure source_name is preserved if both events were from the same source
    if source_name:
        base_event.source_name = source_name
    
    return base_event

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

def deduplicate_database(config: DuplicateConfig = DuplicateConfig(), source_name: Optional[str] = None) -> Tuple[int, List[Event]]:
    """
    Deduplicate events in the database, optionally filtering by source.
    Returns tuple of (number of duplicates found, list of merged events)
    """
    init_db()  # Ensure database is initialized
    db = get_db()
    try:
        # Get all events, optionally filtered by source
        query = db.query(Event)
        if source_name:
            logger.info(f"Deduplicating events with source_name={source_name}")
            query = query.filter(Event.source_name == source_name)
        events = query.order_by(Event.created_at.asc()).all()
        logger.info(f"Found {len(events)} events to process")
        
        # Find and merge duplicates
        merged_events, duplicate_count = _find_and_merge_duplicates(events, config)
        logger.info(f"After merging: {len(merged_events)} events")
        
        # If we're deduplicating a specific source, ensure all merged events keep that source
        if source_name:
            for event in merged_events:
                event.source_name = source_name
        
        # Delete all events (filtered by source if specified)
        delete_query = db.query(Event)
        if source_name:
            delete_query = delete_query.filter(Event.source_name == source_name)
        deleted_count = delete_query.delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_count} events")
        
        # Clear session to remove any stale references
        db.expunge_all()
        
        # Add merged events back to database as new instances
        for event in merged_events:
            # Create a new Event instance with the same data, excluding SQLAlchemy's internal attributes and id
            event_data = {k: v for k, v in event.__dict__.items() 
                        if not k.startswith('_') and k != 'id'}
            new_event = Event(**event_data)
            db.add(new_event)
        
        # Commit all changes
        db.commit()
        
        return duplicate_count, merged_events
        
    finally:
        close_db()

def check_duplicate_before_insert(new_event: Event, config: DuplicateConfig = DuplicateConfig()) -> Optional[Event]:
    """
    Check if an event already exists in the database before inserting.
    Returns merged event if duplicate found, None otherwise.
    """
    db = get_db()
    try:
        # Get potential duplicates within time window
        time_window = timedelta(minutes=config.time_window_minutes)
        start_time_min = new_event.start_time - time_window
        start_time_max = new_event.start_time + time_window
        
        # Query potential duplicates
        potential_duplicates = db.query(Event).filter(
            Event.start_time.between(start_time_min, start_time_max)
        ).all()
        
        # Check each potential duplicate
        for existing_event in potential_duplicates:
            if are_events_duplicate(new_event, existing_event, config):
                return merge_events(existing_event, new_event)
        
        return None
        
    finally:
        close_db() 