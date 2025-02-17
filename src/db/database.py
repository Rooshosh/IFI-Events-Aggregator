import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models.event import Event

logger = logging.getLogger(__name__)

# Database connection
DB_PATH = Path(__file__).parent.parent.parent / 'events.db'

def get_db_connection() -> sqlite3.Connection:
    """Get a database connection"""
    return sqlite3.connect(str(DB_PATH))

def init_db():
    """Initialize the database and create necessary tables"""
    # Delete existing database if it exists
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                location TEXT,
                food TEXT,
                capacity INTEGER,
                spots_left INTEGER,
                source_url TEXT,
                source_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logger.info("Database initialized successfully")

class Database:
    """Database management class"""
    
    def __init__(self):
        self.conn = get_db_connection()
    
    def close(self):
        """Close the database connection"""
        self.conn.close()
    
    def merge_event(self, event: Event) -> None:
        """Merge an event into the database, updating if it exists or inserting if new"""
        # Check for existing event with same title and start time
        cursor = self.conn.execute('''
            SELECT id FROM events 
            WHERE title = ? AND start_time = ? AND source_name = ?
        ''', (event.title, event.start_time.isoformat(), event.source_name))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing event
            self.conn.execute('''
                UPDATE events SET
                    description = ?,
                    end_time = ?,
                    location = ?,
                    food = ?,
                    capacity = ?,
                    spots_left = ?,
                    source_url = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (
                event.description,
                event.end_time.isoformat() if event.end_time else None,
                event.location,
                event.food,
                event.capacity,
                event.spots_left,
                event.source_url,
                datetime.now().isoformat(),
                existing[0]
            ))
            logger.debug(f"Updated event: {event.title}")
        else:
            # Insert new event
            self.conn.execute('''
                INSERT INTO events (
                    title, description, start_time, end_time,
                    location, food, capacity, spots_left,
                    source_url, source_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.title,
                event.description,
                event.start_time.isoformat(),
                event.end_time.isoformat() if event.end_time else None,
                event.location,
                event.food,
                event.capacity,
                event.spots_left,
                event.source_url,
                event.source_name
            ))
            logger.debug(f"Inserted new event: {event.title}")
        
        self.conn.commit()

_db_instance: Optional[Database] = None

def get_db() -> Database:
    """Get the database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance 