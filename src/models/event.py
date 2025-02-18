"""Event model definition using SQLAlchemy ORM."""

from datetime import datetime
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy import Column, Integer, String, Text, DateTime, event
from sqlalchemy.orm import validates
from sqlalchemy import event as sa_event

from ..db.model import Base

def ensure_timezone(dt: datetime) -> datetime:
    """Ensure datetime is in Europe/Oslo timezone"""
    if dt is None:
        return None
    oslo_tz = ZoneInfo("Europe/Oslo")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=oslo_tz)
    return dt.astimezone(oslo_tz)

class Event(Base):
    """
    Event model representing an event from any source.
    
    This model uses SQLAlchemy ORM for database operations. The database is automatically
    recreated when running `python scripts/events.py fetch`, which makes it easy to modify
    fields during development.

    To modify fields:
    1. Add a field: Add a new Column definition to this class
    2. Remove a field: Delete the Column definition
    3. Modify a field: Update the Column definition
    4. After any change: Run `fetch` command to recreate the database

    Remember to:
    - Update relevant scrapers if adding new fields they should populate
    - Update any code that directly references modified/removed fields
    - Consider adding validation using the @validates decorator if needed
    
    Fields:
        id: Unique identifier (auto-generated)
        title: Event title
        description: Event description
        start_time: When the event starts
        end_time: When the event ends (optional)
        location: Where the event takes place (optional)
        source_url: URL to the event's source page (optional)
        source_name: Name of the source (e.g., 'peoply.app', 'ifinavet.no')
        created_at: When this event was first created in our database
        capacity: Total number of spots available (optional)
        spots_left: Number of spots still available (optional)
        registration_opens: When registration opens (optional)
        registration_url: URL for registration if different from source_url (optional)
        food: Description of food/refreshments if provided (optional)
    """
    __tablename__ = 'events'
    
    # Required fields
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    
    # Optional fields
    end_time = Column(DateTime(timezone=True))
    location = Column(String)
    source_url = Column(String)
    source_name = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Europe/Oslo")))
    capacity = Column(Integer)
    spots_left = Column(Integer)
    registration_opens = Column(DateTime(timezone=True))
    registration_url = Column(String)
    food = Column(String)
    
    def __init__(self, **kwargs):
        """Initialize an Event with the given attributes."""
        # Ensure timezone-aware datetimes and convert to Oslo time
        if 'start_time' in kwargs:
            kwargs['start_time'] = ensure_timezone(kwargs['start_time'])
        if 'end_time' in kwargs:
            kwargs['end_time'] = ensure_timezone(kwargs['end_time'])
        if 'registration_opens' in kwargs:
            kwargs['registration_opens'] = ensure_timezone(kwargs['registration_opens'])
        if 'created_at' in kwargs:
            kwargs['created_at'] = ensure_timezone(kwargs['created_at'])
        
        super().__init__(**kwargs)
    
    @validates('start_time', 'end_time', 'registration_opens', 'created_at')
    def validate_datetime(self, key, value):
        """Ensure all datetime fields are in Europe/Oslo timezone."""
        return ensure_timezone(value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create an Event from a dictionary."""
        return cls(
            title=data['title'],
            description=data['description'],
            start_time=data['start_time'],
            end_time=data.get('end_time'),
            location=data.get('location'),
            source_url=data.get('source_url'),
            source_name=data.get('source_name'),
            id=data.get('id'),
            created_at=data.get('created_at'),
            capacity=data.get('capacity'),
            spots_left=data.get('spots_left'),
            registration_opens=data.get('registration_opens'),
            registration_url=data.get('registration_url'),
            food=data.get('food')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'location': self.location,
            'source_url': self.source_url,
            'source_name': self.source_name,
            'created_at': self.created_at,
            'capacity': self.capacity,
            'spots_left': self.spots_left,
            'registration_opens': self.registration_opens,
            'registration_url': self.registration_url,
            'food': self.food
        }
    
    def __str__(self) -> str:
        """Default string representation with basic event information."""
        return f"{self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    def to_detailed_string(self) -> str:
        """Detailed string representation with all available event information."""
        lines = [
            "-" * 80,
            f"Title: {self.title}",
            f"Start: {self.start_time.strftime('%Y-%m-%d %H:%M')}",
            f"End: {self.end_time.strftime('%Y-%m-%d %H:%M') if self.end_time else 'Not specified'}",
            f"Location: {self.location or 'Not specified'}",
            f"Source: {self.source_name or 'Unknown'}",
            f"URL: {self.source_url or 'Not available'}"
        ]
        
        # Add optional information if available
        if self.capacity is not None:
            lines.append(f"Capacity: {self.capacity}")
        if self.spots_left is not None:
            lines.append(f"Spots Left: {self.spots_left}")
        if self.food:
            lines.append(f"Food: {self.food}")
        if self.registration_opens:
            lines.append(f"Registration Opens: {self.registration_opens.strftime('%Y-%m-%d %H:%M')}")
        if self.registration_url and self.registration_url != self.source_url:
            lines.append(f"Registration URL: {self.registration_url}")
        
        # Add description at the end
        if self.description:
            lines.extend(["", "Description:", self.description])
        
        return "\n".join(lines)
    
    def to_summary_string(self) -> str:
        """Summary string representation with key event information."""
        summary = [f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"]
        
        if self.location:
            summary.append(f"at {self.location}")
        if self.capacity is not None and self.spots_left is not None:
            summary.append(f"({self.spots_left}/{self.capacity} spots available)")
        elif self.capacity is not None:
            summary.append(f"(Capacity: {self.capacity})")
        
        return " ".join(summary)

# SQLAlchemy event listeners to handle timezone conversion
@sa_event.listens_for(Event, 'load')
def receive_load(target, context):
    """Ensure timezone information when loading from database"""
    if target.start_time:
        target.start_time = ensure_timezone(target.start_time)
    if target.end_time:
        target.end_time = ensure_timezone(target.end_time)
    if target.registration_opens:
        target.registration_opens = ensure_timezone(target.registration_opens)
    if target.created_at:
        target.created_at = ensure_timezone(target.created_at)

@sa_event.listens_for(Event, 'before_insert')
@sa_event.listens_for(Event, 'before_update')
def receive_before_save(mapper, connection, target):
    """Ensure timezone information before saving to database"""
    if target.start_time:
        target.start_time = ensure_timezone(target.start_time)
    if target.end_time:
        target.end_time = ensure_timezone(target.end_time)
    if target.registration_opens:
        target.registration_opens = ensure_timezone(target.registration_opens)
    if target.created_at:
        target.created_at = ensure_timezone(target.created_at) 