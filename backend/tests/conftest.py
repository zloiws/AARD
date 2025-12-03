"""
Pytest configuration and fixtures
"""
import sys
from pathlib import Path
import pytest
from sqlalchemy.orm import Session

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal, Base, engine


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a database session for testing"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()

