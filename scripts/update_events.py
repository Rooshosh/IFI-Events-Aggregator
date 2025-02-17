import logging
import os
import sys
import sqlite3
from typing import List

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.event import Event
from src.scrapers.manager import SourceManager
from src.utils.deduplication import check_duplicate_before_insert, DuplicateConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db(db_path: str):
    """Initialize the database and create the events table if it doesn't exist."""
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    location TEXT,
                    source_url TEXT,
                    source_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

def save_events_to_db(events: List[Event], db_path: str):
    """Save events to the database, checking for duplicates"""
    try:
        config = DuplicateConfig()  # Use default config for duplicate detection
        
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            new_count = 0
            duplicate_count = 0
            
            for event in events:
                # Check for duplicates
                merged_event = check_duplicate_before_insert(event, db_path, config)
                if merged_event:
                    # Update existing event with merged data
                    c.execute('''
                        UPDATE events
                        SET title = ?, description = ?, start_time = ?, end_time = ?,
                            location = ?, source_url = ?, source_name = ?
                        WHERE id = ?
                    ''', (
                        merged_event.title,
                        merged_event.description,
                        merged_event.start_time.isoformat(),
                        merged_event.end_time.isoformat() if merged_event.end_time else None,
                        merged_event.location,
                        merged_event.source_url,
                        merged_event.source_name,
                        merged_event.id
                    ))
                    duplicate_count += 1
                else:
                    # Insert new event
                    c.execute('''
                        INSERT INTO events (
                            title, description, start_time, end_time,
                            location, source_url, source_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.title,
                        event.description,
                        event.start_time.isoformat(),
                        event.end_time.isoformat() if event.end_time else None,
                        event.location,
                        event.source_url,
                        event.source_name
                    ))
                    new_count += 1
            
            conn.commit()
            logger.info(f"Added {new_count} new events and updated {duplicate_count} existing events")
    
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while saving events: {str(e)}")

def update_events():
    """Update events from all enabled sources"""
    # Initialize database
    db_path = os.path.join(os.path.dirname(__file__), '..', 'events.db')
    init_db(db_path)
    
    # Get events from all enabled sources
    events = SourceManager.get_all_events()
    if events:
        save_events_to_db(events, db_path)
        logger.info(f"Finished processing {len(events)} total events")
    else:
        logger.warning("No events found from any source")

if __name__ == '__main__':
    update_events() 