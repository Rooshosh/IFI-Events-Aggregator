# Tests

This directory contains test files for the IFI Events Aggregator project. The directory structure mirrors the `src` directory to make it easy to:
- Find tests for specific components
- Maintain a clear organization
- Add new tests in the future

## Directory Structure

```
tests/
├── config/       # Tests for configuration modules
├── db/          # Tests for database operations
├── models/      # Tests for data models
├── scrapers/    # Tests for event scrapers
├── utils/       # Tests for utility functions
└── web/         # Tests for web interface
```

## Running Tests

To run all tests:
```bash
python -m unittest discover tests
```

To run tests for a specific module:
```bash
python -m unittest tests/scrapers/test_navet.py
```

## Writing New Tests

When adding new functionality to the project:
1. Create a test file in the corresponding directory
2. Name the file `test_*.py` (e.g., `test_events.py` for testing events functionality)
3. Follow the existing test patterns for consistency 