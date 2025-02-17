from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

def ensure_timezone(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware, converting to UTC if it isn't"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt

@dataclass
class Event:
    """Data class for events to ensure consistent handling"""
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    source_url: Optional[str]
    source_name: Optional[str]
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Ensure all datetime fields are timezone-aware"""
        self.start_time = ensure_timezone(self.start_time)
        self.end_time = ensure_timezone(self.end_time) if self.end_time else None
        self.created_at = ensure_timezone(self.created_at) if self.created_at else None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create an Event from a dictionary"""
        return cls(
            title=data['title'],
            description=data['description'],
            start_time=ensure_timezone(data['start_time']),
            end_time=ensure_timezone(data['end_time']) if data['end_time'] else None,
            location=data.get('location'),
            source_url=data.get('source_url'),
            source_name=data.get('source_name'),
            id=data.get('id'),
            created_at=ensure_timezone(data['created_at']) if data.get('created_at') else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'location': self.location,
            'source_url': self.source_url,
            'source_name': self.source_name,
            'created_at': self.created_at
        } 