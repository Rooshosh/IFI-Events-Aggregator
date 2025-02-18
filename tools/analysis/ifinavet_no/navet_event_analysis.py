from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin

@dataclass
class EventCardInfo:
    """Information available from the event card"""
    title: str
    company: str
    description: str
    date: str
    time: str
    capacity: int
    url: str
    is_preliminary: bool  # True if description is "Mer info kommer"

def analyze_event_cards(html_file: str) -> Dict:
    """Analyze the structure and content of event cards"""
    with open(html_file, 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    analysis = {
        'total_events': 0,
        'preliminary_events': 0,  # Events with "Mer info kommer"
        'event_classes': [],
        'date_formats': [],
        'time_formats': [],
        'companies': [],
        'event_types': [],
        'url_patterns': [],
        'sample_events': {
            'detailed': None,  # Full info event
            'preliminary': None  # "Mer info kommer" event
        }
    }
    
    # Find all event items
    event_items = soup.find_all('div', class_=lambda x: x and 'event-list-item' in x)
    analysis['total_events'] = len(event_items)
    
    # Temporary sets for collecting unique values
    event_classes = set()
    date_formats = set()
    time_formats = set()
    companies = set()
    event_types = set()
    url_patterns = set()
    
    for event in event_items:
        wrapper = event.find('div', class_='event-list-item-wrapper')
        if not wrapper:
            continue
            
        # Get event URL
        onclick = wrapper.get('onclick', '')
        if 'location.href=' in onclick:
            url = onclick.split("'")[1]
            url_patterns.add(url)
        
        # Extract event details
        title = event.find('h3', class_='event-list-item-title')
        description = event.find('p')
        company_logo = event.find('img')
        
        # Check if preliminary
        is_preliminary = description and 'Mer info kommer' in description.text.strip()
        if is_preliminary:
            analysis['preliminary_events'] += 1
        
        # Analyze event type
        if title:
            title_text = title.text.strip()
            if 'Workshop' in title_text:
                event_types.add('Workshop')
            elif 'Bedriftspresentasjon' in title_text:
                event_types.add('Bedriftspresentasjon')
        
        # Extract meta information
        meta_items = event.find_all('div', class_='event-list-item-meta')
        meta_info = {}
        for meta in meta_items:
            if 'icon-clock2' in str(meta):
                time_text = meta.find('span', class_=None).text.strip()
                time_formats.add(time_text)
                meta_info['time'] = time_text
            elif 'icon-calendar' in str(meta):
                date_text = meta.find('span', class_=None).text.strip()
                date_formats.add(date_text)
                meta_info['date'] = date_text
            elif 'icon-users' in str(meta):
                meta_info['capacity'] = meta.find('span', class_=None).text.strip()
        
        if company_logo:
            companies.add(company_logo.get('alt', ''))
        
        # Store sample events
        event_info = EventCardInfo(
            title=title.text.strip() if title else '',
            company=company_logo.get('alt', '') if company_logo else '',
            description=description.text.strip() if description else '',
            date=meta_info.get('date', ''),
            time=meta_info.get('time', ''),
            capacity=int(meta_info.get('capacity', '0')),
            url=url if 'url' in locals() else '',
            is_preliminary=is_preliminary
        )
        
        if is_preliminary and not analysis['sample_events']['preliminary']:
            analysis['sample_events']['preliminary'] = event_info
        elif not is_preliminary and not analysis['sample_events']['detailed']:
            analysis['sample_events']['detailed'] = event_info
    
    # Convert sets to sorted lists
    analysis['event_types'] = sorted(event_types)
    analysis['date_formats'] = sorted(date_formats)
    analysis['time_formats'] = sorted(time_formats)
    analysis['companies'] = sorted(companies)
    analysis['url_patterns'] = sorted(url_patterns)
    
    # Convert sample events to dict for JSON serialization
    if analysis['sample_events']['detailed']:
        analysis['sample_events']['detailed'] = vars(analysis['sample_events']['detailed'])
    if analysis['sample_events']['preliminary']:
        analysis['sample_events']['preliminary'] = vars(analysis['sample_events']['preliminary'])
    
    return analysis

def main():
    # Ensure the analysis directory exists
    Path('analysis').mkdir(exist_ok=True)
    
    # Run analysis
    html_file = 'navet-evets-2025-var.html'
    analysis = analyze_event_cards(html_file)
    
    # Save analysis results
    output_file = 'analysis/navet_detailed_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"Analysis complete! Found {analysis['total_events']} events")
    print(f"Preliminary events (Mer info kommer): {analysis['preliminary_events']}")
    print(f"Detailed events: {analysis['total_events'] - analysis['preliminary_events']}")
    print("\nEvent Types:", ', '.join(analysis['event_types']))
    print("\nCompanies (first 5):", ', '.join(analysis['companies'][:5]))
    print("\nURL Pattern examples:")
    for url in analysis['url_patterns'][:3]:  # Show first 3 examples
        print(f"  - {url}")
    
    if analysis['sample_events']['detailed']:
        print("\nSample Detailed Event:")
        for k, v in analysis['sample_events']['detailed'].items():
            print(f"  {k}: {v}")
    
    print(f"\nDetailed results saved to {output_file}")

if __name__ == '__main__':
    main() 