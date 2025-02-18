from datetime import datetime
import sqlite3
from flask import Blueprint, render_template
from ...models.event import Event
from ...db.database import get_db_path

# Create the blueprint
events_bp = Blueprint('events', __name__)

@events_bp.route('/')
def index():
    """Main page showing all upcoming events"""
    with sqlite3.connect(get_db_path()) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, title, description, start_time, end_time, location, source_url, source_name
            FROM events
            WHERE end_time > datetime('now')
            ORDER BY start_time ASC
        ''')
        events = c.fetchall()
        # Convert to list of Event objects
        events = [
            Event(
                id=e[0],
                title=e[1],
                description=e[2],
                start_time=datetime.fromisoformat(e[3]),
                end_time=datetime.fromisoformat(e[4]) if e[4] else None,
                location=e[5],
                source_url=e[6],
                source_name=e[7]
            )
            for e in events
        ]
        return render_template('index.html', events=events) 