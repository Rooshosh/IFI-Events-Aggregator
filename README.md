# IFI Events

A Python application that aggregates and displays events from various UiO IFI (Department of Informatics) sources.

## Features

- Event scraping from multiple sources:
  - Peoply.app - Events from student organizations
  - Navet (ifinavet.no) - Company presentations and career events
- Smart caching system for efficient data retrieval
- Automatic deduplication of events
- Web interface to view upcoming events
- Timezone-aware event handling
- SQLAlchemy ORM for robust database operations

## Components

The project consists of several key components:

- **Event Scrapers**: Modules for fetching events from different sources (using BeautifulSoup4 and Requests)
- **Web Interface**: Flask-based web application for viewing events
- **CLI Tools**: Command-line tools for managing events and system maintenance
- **Storage**: SQLAlchemy-powered SQLite database with smart event merging and caching system
- **Test Suite**: Comprehensive tests for all components

## Quick Start

1. Set up environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run in development mode:
   ```bash
   FLASK_ENV=development python run.py
   ```

3. Run tests:
   ```bash
   python -m unittest discover tests
   ```

## Documentation

- Each Python module contains detailed documentation in its docstrings
- For CLI tools, use the `--help` flag (e.g., `python scripts/events.py --help`)
- The web interface includes inline help and tooltips

## Development

### Database Operations

The project uses SQLAlchemy ORM for database operations:

- Event data model is defined in `src/models/event.py`
- Database configuration is in `src/db/base.py`
- During development, the database is automatically recreated when running `python scripts/events.py fetch`
- See docstrings in the code for detailed usage examples and field modification instructions

### Adding a New Event Source

1. Create a new scraper in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods
3. Add the scraper to the list in `scripts/events.py`
4. Add appropriate tests

### Production Deployment

1. Use a production WSGI server:
   ```bash
   pip install gunicorn
   FLASK_ENV=production gunicorn -w 4 'src.web:app'
   ```

2. Security checklist:
   - Configure proper logging
   - Set appropriate file permissions
   - Use HTTPS
   - Set secure headers
   - Configure user authentication if needed
   - Set environment variables for sensitive data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 