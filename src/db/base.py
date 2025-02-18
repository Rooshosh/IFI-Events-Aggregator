"""SQLAlchemy base configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from pathlib import Path
import os

# Create base class for declarative models
Base = declarative_base()

# Define database paths
DB_PATH = Path(__file__).parent.parent.parent / 'events.db'

def get_db_url():
    """Get the database URL based on environment."""
    is_testing = os.environ.get('TESTING') == 'true'
    
    if is_testing:
        # Use in-memory SQLite for testing
        return "sqlite:///:memory:"
    else:
        return f"sqlite:///{DB_PATH}"

# Initialize engine as None
engine = None

def get_engine():
    """Get or create SQLAlchemy engine based on current environment."""
    global engine
    if engine is None:
        engine = create_engine(
            get_db_url(),
            echo=False,
            connect_args={
                "check_same_thread": False,
                "detect_types": 3  # Enable datetime and timestamp type detection
            },
            poolclass=StaticPool
        )
    return engine

# Create session factory
session_factory = sessionmaker()

# Create thread-safe session registry
Session = scoped_session(session_factory)

def init_db():
    """Initialize database, creating all tables."""
    # Import all models to ensure they're registered
    from ..models.event import Event  # noqa
    
    # Bind session factory to current engine
    session_factory.configure(bind=get_engine())
    
    # Create all tables
    Base.metadata.create_all(get_engine())

def get_db():
    """Get a new database session."""
    if not Session.registry.has():
        # Only configure if no session exists
        Session.configure(bind=get_engine())
    return Session()

def close_db():
    """Remove the current session."""
    Session.remove()

def cleanup_test_db():
    """Clean up test database. Should only be called in test environment."""
    if os.environ.get('TESTING') == 'true':
        global engine
        # Remove existing session
        Session.remove()
        # Drop all tables
        Base.metadata.drop_all(get_engine())
        # Reset engine to None
        engine = None
        # Create fresh tables with new engine
        Base.metadata.create_all(get_engine())
    else:
        raise RuntimeError("cleanup_test_db() should only be called in test environment") 