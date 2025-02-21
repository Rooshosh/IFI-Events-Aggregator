"""Event model definition using SQLAlchemy ORM."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, DateTime, event, JSON
from sqlalchemy.orm import validates
from sqlalchemy import event as sa_event
import json

from ..db.model import Base
from ..utils.timezone import ensure_oslo_timezone, DEFAULT_TIMEZONE, now_oslo

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
        fetched_at: When this event's data was fetched from the source
        capacity: Total number of spots available (optional)
        spots_left: Number of spots still available (optional)
        registration_opens: When registration opens (optional)
        registration_url: URL for registration if different from source_url (optional)
        food: Description of food/refreshments if provided (optional)
        attachment: URL to the event's primary image/attachment
        author: Name of the student club or person that created the event (optional)
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
    created_at = Column(DateTime(timezone=True), default=now_oslo)
    fetched_at = Column(DateTime(timezone=True))  # When the event data was fetched from source
    capacity = Column(Integer)
    spots_left = Column(Integer)
    registration_opens = Column(DateTime(timezone=True))
    registration_url = Column(String)
    food = Column(String)
    attachment = Column(String)  # URL to the event's primary image/attachment
    author = Column(String)  # Student club or person that created the event
    
    def __init__(self, **kwargs):
        """Initialize an Event with the given attributes."""
        # Handle old attachments field if present
        if 'attachments' in kwargs:
            attachments = kwargs.pop('attachments')
            if attachments:
                if isinstance(attachments, list) and attachments:
                    kwargs['attachment'] = attachments[0]
                elif isinstance(attachments, str):
                    kwargs['attachment'] = attachments
        
        # Ensure timezone-aware datetimes and convert to Oslo time
        for field in ['start_time', 'end_time', 'registration_opens', 'created_at', 'fetched_at']:
            if field in kwargs:
                kwargs[field] = ensure_oslo_timezone(kwargs[field])
        
        super().__init__(**kwargs)
    
    @validates('start_time', 'end_time', 'registration_opens', 'created_at', 'fetched_at')
    def validate_datetime(self, key, value):
        """Ensure all datetime fields are in Europe/Oslo timezone."""
        return ensure_oslo_timezone(value)
    
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
            fetched_at=data.get('fetched_at'),
            capacity=data.get('capacity'),
            spots_left=data.get('spots_left'),
            registration_opens=data.get('registration_opens'),
            registration_url=data.get('registration_url'),
            food=data.get('food'),
            attachment=data.get('attachment'),
            author=data.get('author')
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
            'fetched_at': self.fetched_at,
            'capacity': self.capacity,
            'spots_left': self.spots_left,
            'registration_opens': self.registration_opens,
            'registration_url': self.registration_url,
            'food': self.food,
            'attachment': self.attachment,
            'author': self.author
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
        if self.author:
            lines.append(f"Author: {self.author}")
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
        if self.attachment:
            lines.append(f"Attachment: {self.attachment}")
        
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
    for field in ['start_time', 'end_time', 'registration_opens', 'created_at', 'fetched_at']:
        if hasattr(target, field) and getattr(target, field) is not None:
            setattr(target, field, ensure_oslo_timezone(getattr(target, field)))

@sa_event.listens_for(Event, 'before_insert')
@sa_event.listens_for(Event, 'before_update')
def receive_before_save(mapper, connection, target):
    """Ensure timezone information before saving to database"""
    for field in ['start_time', 'end_time', 'registration_opens', 'created_at', 'fetched_at']:
        if hasattr(target, field) and getattr(target, field) is not None:
            setattr(target, field, ensure_oslo_timezone(getattr(target, field))) 