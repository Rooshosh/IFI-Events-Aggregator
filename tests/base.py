"""Base test class with common setup and teardown."""

import unittest
import os
from pathlib import Path
import sys

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

class BaseTestCase(unittest.TestCase):
    """Base test case with database setup and teardown."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Set testing environment variable before importing database modules
        os.environ['TESTING'] = 'true'
        
        # Initialize database
        from src.db import db_manager
        db_manager.init_db()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        try:
            from src.db import db_manager
            db_manager.cleanup_test_db()
        finally:
            # Clean up environment
            os.environ.pop('TESTING', None)
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        from src.db import db_manager
        db_manager.cleanup_test_db()  # Ensure clean state for each test
    
    def tearDown(self):
        """Clean up after each test."""
        from src.db import db_manager
        db_manager.close_session()  # Ensure connections are closed 