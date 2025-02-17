from flask import Flask, render_template, jsonify, send_file
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# Database setup
def init_db():
    with sqlite3.connect('events.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                location TEXT,
                source_url TEXT,
                source_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Initialize database on startup
init_db()

@app.route('/')
def index():
    with sqlite3.connect('events.db') as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, title, description, start_time, end_time, location, source_url
            FROM events
            ORDER BY start_time ASC
        ''')
        events = c.fetchall()
        # Convert to list of dicts for easier template handling
        events = [
            {
                'id': e[0],
                'title': e[1],
                'description': e[2],
                'start_time': datetime.strptime(e[3], '%Y-%m-%d %H:%M:%S'),
                'end_time': datetime.strptime(e[4], '%Y-%m-%d %H:%M:%S') if e[4] else None,
                'location': e[5],
                'source_url': e[6]
            }
            for e in events
        ]
        return render_template('index.html', events=events)

if __name__ == '__main__':
    app.run(debug=True)
