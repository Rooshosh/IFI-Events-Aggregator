import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_peoply_events():
    """
    Scrape events from peoply.app
    Returns a list of event dictionaries
    """
    try:
        # The base URL for IFI events on peoply.app
        url = "https://peoply.app/ifi-uio"  # This URL might need to be updated
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []
        
        # This is a placeholder for the actual scraping logic
        # You'll need to inspect the peoply.app HTML structure and adjust accordingly
        event_elements = soup.find_all('div', class_='event-card')  # Update this selector
        
        for element in event_elements:
            try:
                event = {
                    'title': element.find('h3').text.strip(),
                    'description': element.find('div', class_='description').text.strip(),
                    'start_time': parse_date(element.find('time')['datetime']),
                    'end_time': None,  # Add logic to parse end time if available
                    'location': element.find('div', class_='location').text.strip(),
                    'source_url': element.find('a')['href'],
                    'source_name': 'peoply.app'
                }
                events.append(event)
            except Exception as e:
                logger.error(f"Error parsing event: {str(e)}")
                continue
        
        return events
    
    except requests.RequestException as e:
        logger.error(f"Error fetching events: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return []

def parse_date(date_str):
    """
    Parse date string from peoply.app format to datetime object
    This is a placeholder - adjust the format string based on actual date format
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError as e:
        logger.error(f"Error parsing date {date_str}: {str(e)}")
        return None

def save_events_to_db(events):
    """
    Save scraped events to the SQLite database
    """
    try:
        with sqlite3.connect('events.db') as conn:
            c = conn.cursor()
            for event in events:
                # Check if event already exists (basic de-duplication)
                c.execute('''
                    SELECT id FROM events 
                    WHERE title = ? AND start_time = ?
                ''', (event['title'], event['start_time']))
                
                if not c.fetchone():
                    c.execute('''
                        INSERT INTO events (
                            title, description, start_time, end_time,
                            location, source_url, source_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event['title'],
                        event['description'],
                        event['start_time'],
                        event['end_time'],
                        event['location'],
                        event['source_url'],
                        event['source_name']
                    ))
            
            conn.commit()
            logger.info(f"Successfully saved {len(events)} events to database")
    
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while saving events: {str(e)}")

def update_events():
    """
    Main function to scrape and update events
    """
    events = scrape_peoply_events()
    if events:
        save_events_to_db(events)
        return len(events)
    return 0

if __name__ == '__main__':
    update_events() 