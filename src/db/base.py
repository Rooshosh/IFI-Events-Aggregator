"""SQLAlchemy base configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from pathlib import Path

# Create base class for declarative models
Base = declarative_base()

# Database URL (SQLite file in project root)
DB_PATH = Path(__file__).parent.parent.parent / 'events.db'
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with SQLite configuration
# echo=False disables SQL logging
# poolclass=StaticPool ensures single connection for threading
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Create session factory
session_factory = sessionmaker(bind=engine)

# Create thread-safe session registry
Session = scoped_session(session_factory)

def init_db():
    """Initialize database, creating all tables."""
    # Import all models to ensure they're registered
    from ..models.event import Event  # noqa
    
    # Create all tables
    Base.metadata.create_all(engine)

def get_db():
    """Get a new database session."""
    return Session()

def close_db():
    """Remove the current session."""
    Session.remove() 