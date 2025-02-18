# IFI Events Aggregator

A Python application that aggregates and displays events from various UiO IFI (Department of Informatics) sources.

## Features

- Event scraping from multiple sources:
  - Peoply.app - Events from student organizations
  - Navet (ifinavet.no) - Company presentations and career events
- Smart caching system for efficient data retrieval
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
│   ├── utils/             # Utility functions
│   ├── config/            # Configuration modules
│   └── db/                # Database handling
├── webapp/                # Web application
│   ├── static/            # Static files
│   ├── templates/         # HTML templates
│   └── app.py            # Flask application
├── scripts/               # CLI tools
│   ├── update_events.py  # Update all events
│   ├── deduplicate.py    # Deduplicate events
│   └── fetch_cache.py    # Manage source caching
├── tests/                 # Test files
│   └── scrapers/         # Scraper tests
└── tools/                 # Development tools
    └── analysis/         # Data analysis tools
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

## Development vs Production

### Development Mode
During development, run the application with debug mode enabled:
```bash
FLASK_ENV=development python run.py
```

This enables:
- Detailed error pages with tracebacks
- Interactive debugger
- Automatic code reloading
- Test routes (e.g., /test-500 for error page testing)

### Production Deployment
For production deployment:

1. Disable debug mode:
   ```bash
   python run.py  # or FLASK_ENV=production python run.py
   ```

2. Use a production WSGI server:
   ```bash
   pip install gunicorn  # Install Gunicorn
   gunicorn -w 4 'src.web:app'  # Run with 4 worker processes
   ```

3. Security considerations:
   - Remove or disable test routes (like test-500)
   - Configure proper logging instead of showing errors to users
   - Set appropriate file permissions
   - Use HTTPS
   - Set secure headers
   - Configure proper user authentication

4. Environment variables:
   - Set `FLASK_ENV=production`
   - Configure any sensitive data through environment variables

## Usage

### Basic Usage

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

### Cache Management

The application includes a smart caching system to reduce API calls and web scraping:

1. Fetch and cache data from a specific source:
   ```bash
   python scripts/fetch_cache.py navet  # For Navet events
   python scripts/fetch_cache.py peoply  # For Peoply events
   ```

2. Force live data fetch (bypass cache):
   ```bash
   python scripts/fetch_cache.py navet --force-live
   ```

Cache configuration can be customized in `src/config/cache.py`.

## Event Sources

Currently supported:
- Peoply.app - Events from student organizations at IFI
- ifinavet.no - Company presentations and career events from Navet

## Development

The project uses:
- Flask for the web interface
- SQLite for data storage
- Python's datetime with timezone support
- Requests for API calls
- BeautifulSoup4 for web scraping
- Custom caching system for efficient data retrieval

To add a new event source:
1. Create a new scraper in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods
3. Add the scraper to the list in `scripts/update_events.py`
4. Add appropriate tests in `tests/scrapers/`

## Testing

Run the test suite:
```bash
python -m unittest discover tests
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 