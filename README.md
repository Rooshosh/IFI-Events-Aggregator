# IFI Events Aggregator

A Python application that aggregates and displays events from various UiO IFI (Department of Informatics) sources.

## Features

- Event scraping from multiple sources (currently Peoply.app)
- Automatic deduplication of events
- Web interface to view upcoming events
- Timezone-aware event handling
- Smart event merging

## Project Structure

```
IFI-Events-Aggregator/
├── src/                    # Main package code
│   ├── models/            # Data models
│   ├── scrapers/          # Event scrapers
│   └── utils/             # Utility functions
├── webapp/                 # Web application
│   ├── static/            # Static files
│   ├── templates/         # HTML templates
│   └── app.py             # Flask application
├── scripts/                # CLI tools
│   ├── update_events.py   # Script to update events
│   └── deduplicate.py     # Script to deduplicate events
└── tests/                  # Test files
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Update events from all sources:
   ```bash
   python scripts/update_events.py
   ```

2. Run deduplication if needed:
   ```bash
   python scripts/deduplicate.py
   ```

3. Start the web application:
   ```bash
   python webapp/app.py
   ```
   Then visit http://127.0.0.1:5000 in your browser.

## Event Sources

Currently supported:
- Peoply.app - Events from student organizations at IFI

## Development

The project uses:
- Flask for the web interface
- SQLite for data storage
- Python's datetime with timezone support
- Requests for API calls

To add a new event source:
1. Create a new scraper in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods
3. Add the scraper to the list in `scripts/update_events.py`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 