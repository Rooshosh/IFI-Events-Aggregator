from bs4 import BeautifulSoup
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class EventPageInfo:
    """Information available from the event detail page"""
    title: str
    description: str
    food: Optional[str]
    location: Optional[str]
    registration_info: Optional[str]
    spots_left: Optional[int]

def analyze_event_page(html_content: str) -> Dict:
    """Analyze the structure of an individual event page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    analysis = {
        'content_sections': [],  # Different content section types
        'food_location': None,  # Where food info is found
        'registration_section': None,  # Registration info location
        'location_info': None,  # Location information
    }
    
    # Find all content sections
    content_sections = soup.find_all('div', class_='content-section')
    for i, section in enumerate(content_sections):
        section_info = {
            'index': i,
            'classes': section.get('class', []),
            'has_food_info': 'Burritos' in section.text,
            'has_registration': 'påmelding' in section.text.lower(),
            'text_preview': section.text[:100] + '...' if len(section.text) > 100 else section.text
        }
        analysis['content_sections'].append(section_info)
        
        # Mark sections containing key information
        if section_info['has_food_info']:
            analysis['food_location'] = i
        if section_info['has_registration']:
            analysis['registration_section'] = i
        if 'Ole-Johan' in section.text or 'Gaustadalléen' in section.text:
            analysis['location_info'] = i
    
    return analysis

def main():
    # Ensure the analysis directory exists
    Path('analysis').mkdir(exist_ok=True)
    
    # Sample event page HTML (you'll need to provide this)
    sample_html = """
    <!-- Insert sample event page HTML here -->
    """
    
    # Run analysis
    analysis = analyze_event_page(sample_html)
    
    # Save analysis results
    output_file = 'analysis/navet_page_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("Content Sections Found:", len(analysis['content_sections']))
    print("\nFood Information Location:", 
          f"Section {analysis['food_location']}" if analysis['food_location'] is not None else "Not found")
    print("Registration Information:", 
          f"Section {analysis['registration_section']}" if analysis['registration_section'] is not None else "Not found")
    print("Location Information:", 
          f"Section {analysis['location_info']}" if analysis['location_info'] is not None else "Not found")
    
    print("\nSection Details:")
    for section in analysis['content_sections']:
        print(f"\nSection {section['index']}:")
        print(f"  Classes: {', '.join(section['classes'])}")
        print(f"  Has Food Info: {section['has_food_info']}")
        print(f"  Has Registration: {section['has_registration']}")
        print(f"  Preview: {section['text_preview']}")
    
    print(f"\nDetailed results saved to {output_file}")

if __name__ == '__main__':
    main() 