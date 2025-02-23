from datetime import datetime
from flask import Blueprint, render_template, request, make_response
from sqlalchemy import select, or_
from icalendar import Calendar, Event as ICalEvent
from ...models.event import Event
from ...db import db_manager
from ...utils.timezone import now_oslo

# Create the blueprint
events_bp = Blueprint('events', __name__)

@events_bp.route('/')
def index():
    """Main page showing all upcoming events"""
    with db_manager.session() as db:
        # Query for all upcoming events
        now = now_oslo()
        stmt = select(Event).where(
            or_(
                Event.end_time > now,  # Event hasn't ended yet
                Event.start_time > now  # Event hasn't started yet (for events with no end time)
            )
        ).order_by(Event.start_time.asc())
        
        # Get all events - filtering will be handled by JavaScript
        events = db.execute(stmt).scalars().all()
        return render_template('index.html', events=events)

@events_bp.route('/calendar.ics')
def ics_feed():
    """Generate ICS calendar feed of upcoming events"""
    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//IFI Events//ifi.uio.no//')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'IFI Events')
    cal.add('x-wr-caldesc', 'Events at the Department of Informatics, University of Oslo')
    
    with db_manager.session() as db:
        # Query for upcoming events
        now = now_oslo()
        stmt = select(Event).where(
            or_(
                Event.end_time > now,  # Event hasn't ended yet
                Event.start_time > now  # Event hasn't started yet (for events with no end time)
            )
        ).order_by(Event.start_time.asc())
        
        events = db.execute(stmt).scalars().all()
        
        for event in events:
            # Create calendar event
            cal_event = ICalEvent()
            cal_event.add('summary', event.title)
            cal_event.add('dtstart', event.start_time)
            if event.end_time:
                cal_event.add('dtend', event.end_time)
            
            # Build description
            description = []
            if event.description:
                description.append(event.description)
            if event.food:
                description.append(f"🍽️ Food: {event.food}")
            if event.capacity:
                capacity_info = f"👥 Capacity: {event.capacity}"
                if event.spots_left is not None:
                    capacity_info += f" (Spots left: {event.spots_left})"
                description.append(capacity_info)
            if event.source_url:
                description.append(f"\nEvent link: {event.source_url}")
            if event.registration_url and event.registration_url != event.source_url:
                description.append(f"Registration: {event.registration_url}")
            
            cal_event.add('description', '\n\n'.join(description))
            
            if event.location:
                cal_event.add('location', event.location)
            
            # Add source URL as URL property
            if event.source_url:
                cal_event.add('url', event.source_url)
            
            # Add unique ID
            cal_event.add('uid', f"{event.id}@{request.host}")
            
            # Add to calendar
            cal.add_component(cal_event)
    
    # Generate response
    response = make_response(cal.to_ical())
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'inline; filename=ifi-events.ics'
    return response

@events_bp.route('/test-500')
def test_500():
    """Route to test 500 error page"""
    # Deliberately raise an exception
    raise Exception("This is a test error to view the 500 error page") 