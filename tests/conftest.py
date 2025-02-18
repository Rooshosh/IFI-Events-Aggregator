"""Shared pytest fixtures."""

import os
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.db import db_manager
from src.models.event import Event

@pytest.fixture(autouse=True)
def test_env():
    """Ensure we're in test environment for all tests."""
    os.environ['TESTING'] = 'true'
    yield
    os.environ.pop('TESTING', None)

@pytest.fixture
def db():
    """Provide a database session that's cleaned up after each test."""
    db_manager.init_db()
    db_manager.cleanup_test_db()  # Ensure clean state before test
    with db_manager.session() as session:
        yield session
    db_manager.cleanup_test_db()  # Clean up after test

@pytest.fixture
def test_event():
    """Provide a test event with Oslo timezone."""
    oslo_tz = ZoneInfo("Europe/Oslo")
    return Event(
        title="Test Event",
        description="Test Description",
        start_time=datetime.now(oslo_tz),
        end_time=datetime.now(oslo_tz),
        location="Test Location",
        source_url="http://test.com",
        source_name="test_source"
    )

@pytest.fixture
def populated_db(db, test_event):
    """Provide a database session with a test event already added."""
    db.add(test_event)
    db.commit()
    return db 