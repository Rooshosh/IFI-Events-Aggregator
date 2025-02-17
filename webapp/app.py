import os
import sys
import sqlite3
from datetime import datetime
from flask import Flask, render_template

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.event import Event

app = Flask(__name__)

def get_db_path():
    """Get the path to the database file"""
    return os.path.join(os.path.dirname(__file__), '..', 'events.db')

@app.route('/')
def index():
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

if __name__ == '__main__':
    app.run(debug=True) 