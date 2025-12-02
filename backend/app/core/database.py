"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
import logging

from app.core.config import get_settings
from app.core.logging_config import LoggingConfig

# Lazy initialization - don't create engine at module level
_engine: Optional[create_engine] = None
_SessionLocal: Optional[sessionmaker] = None

# Base class for models (can be created immediately)
Base = declarative_base()


def get_engine():
    """Get or create database engine (lazy initialization)"""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Configure logging before creating engine
        LoggingConfig.configure()
        
        # Disable echo - we control logging through LoggingConfig
        # Only enable if explicitly requested
        echo = settings.log_sqlalchemy
        
        _engine = create_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=echo,  # Controlled by log_sqlalchemy setting
        )
        
        # Explicitly set SQLAlchemy logger level
        sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
        if not settings.log_sqlalchemy:
            sqlalchemy_logger.setLevel(logging.WARNING)
            sqlalchemy_logger.propagate = False
    return _engine


def get_session_local():
    """Get or create session factory (lazy initialization)"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# For backward compatibility - create module-level attributes
# These will be initialized on first access via __getattr__
def __getattr__(name):
    """Support backward compatibility for engine and SessionLocal"""
    if name == 'engine':
        return get_engine()
    elif name == 'SessionLocal':
        return get_session_local()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

