from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List

def analyze_event_structure(html_file: str) -> Dict:
    """Analyze the structure of events in the HTML file"""
    with open(html_file, 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    analysis = {
        'total_events': 0,
        'event_classes': set(),
        'date_formats': set(),
        'time_formats': set(),
        'companies': set(),
        'event_types': set(),  # Workshop, Bedriftspresentasjon, etc.
        'sample_event': None,
        'events_by_month': {},
        'capacity_range': {'min': float('inf'), 'max': 0}
    }
    
    # Find all event items
    event_items = soup.find_all('div', class_=lambda x: x and 'event-list-item' in x)
    analysis['total_events'] = len(event_items)
    
    for event in event_items:
        # Collect event classes
        analysis['event_classes'].add(event.get('class', [''])[0])
        
        # Extract event details
        title = event.find('h3', class_='event-list-item-title')
        if title:
            title_text = title.text.strip()
            # Analyze event types
            if 'Workshop' in title_text:
                analysis['event_types'].add('Workshop')
            elif 'Bedriftspresentasjon' in title_text:
                analysis['event_types'].add('Bedriftspresentasjon')
        
        # Extract company
        company_logo = event.find('img')
        if company_logo:
            analysis['companies'].add(company_logo.get('alt', ''))
        
        # Extract date and time formats
        meta_items = event.find_all('div', class_='event-list-item-meta')
        for meta in meta_items:
            if 'icon-clock2' in str(meta):
                time_text = meta.find('span', class_=None).text.strip()
                analysis['time_formats'].add(time_text)
            elif 'icon-calendar' in str(meta):
                date_text = meta.find('span', class_=None).text.strip()
                analysis['date_formats'].add(date_text)
            elif 'icon-users' in str(meta):
                capacity = int(meta.find('span', class_=None).text.strip())
                analysis['capacity_range']['min'] = min(analysis['capacity_range']['min'], capacity)
                analysis['capacity_range']['max'] = max(analysis['capacity_range']['max'], capacity)
        
        # Store first event as sample
        if analysis['sample_event'] is None:
            analysis['sample_event'] = {
                'title': title_text if title else '',
                'company': company_logo.get('alt', '') if company_logo else '',
                'description': event.find('p').text.strip() if event.find('p') else '',
                'meta': {m.find('span', class_='sr-only').text.strip(): 
                        m.find('span', class_=None).text.strip() 
                        for m in meta_items if m.find('span', class_='sr-only')}
            }
    
    # Convert sets to lists for JSON serialization
    analysis['event_classes'] = list(analysis['event_classes'])
    analysis['date_formats'] = list(analysis['date_formats'])
    analysis['time_formats'] = list(analysis['time_formats'])
    analysis['companies'] = list(analysis['companies'])
    analysis['event_types'] = list(analysis['event_types'])
    
    return analysis

def main():
    # Ensure the analysis directory exists
    Path('analysis').mkdir(exist_ok=True)
    
    # Run analysis
    html_file = 'navet-evets-2025-var.html'
    analysis = analyze_event_structure(html_file)
    
    # Save analysis results
    output_file = 'analysis/navet_analysis_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"Analysis complete! Found {analysis['total_events']} events")
    print("\nEvent Types:", ', '.join(analysis['event_types']))
    print("\nDate Formats:", ', '.join(analysis['date_formats']))
    print("Time Formats:", ', '.join(analysis['time_formats']))
    print(f"\nCapacity Range: {analysis['capacity_range']['min']}-{analysis['capacity_range']['max']} places")
    print(f"\nDetailed results saved to {output_file}")

if __name__ == '__main__':
    main() 