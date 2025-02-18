"""SQLAlchemy base configuration."""

# Re-export everything through the session manager
from .session import db_manager, DB_PATH
from .model import Base

# Maintain backward compatibility
def init_db():
    """Initialize database, creating all tables."""
    db_manager.init_db()

def get_db():
    """Get a new database session."""
    return db_manager.get_session()

def close_db():
    """Remove the current session."""
    db_manager.close_session()

def cleanup_test_db():
    """Clean up test database. Should only be called in test environment."""
    db_manager.cleanup_test_db() 