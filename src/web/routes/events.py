from datetime import datetime
from flask import Blueprint, render_template
from sqlalchemy import select
from ...models.event import Event
from ...db import get_db, close_db

# Create the blueprint
events_bp = Blueprint('events', __name__)

@events_bp.route('/')
def index():
    """Main page showing all upcoming events"""
    db = get_db()
    try:
        # Query for all upcoming events
        stmt = select(Event).where(
            Event.end_time > datetime.now()
        ).order_by(Event.start_time.asc())
        
        events = db.execute(stmt).scalars().all()
        return render_template('index.html', events=events)
    finally:
        close_db()

@events_bp.route('/test-500')
def test_500():
    """Route to test 500 error page"""
    # Deliberately raise an exception
    raise Exception("This is a test error to view the 500 error page") 