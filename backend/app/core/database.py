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
from app.core.metrics import (
    db_queries_total,
    db_query_duration_seconds,
    db_connection_pool_size,
    db_connection_pool_overflow
)
from sqlalchemy import event
import time

# Lazy initialization - don't create engine at module level
_engine: Optional[create_engine] = None
_SessionLocal: Optional[sessionmaker] = None

# Base class for models (can be created immediately)
Base = declarative_base()


def _setup_db_metrics(engine):
    """Setup SQLAlchemy event listeners for database metrics"""
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time"""
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query metrics"""
        if conn.info.get('query_start_time'):
            start_time = conn.info['query_start_time'].pop()
            duration = time.time() - start_time
            
            # Extract query type (SELECT, INSERT, UPDATE, DELETE)
            query_type = statement.strip().split()[0].upper() if statement.strip() else "UNKNOWN"
            # Normalize to lowercase for labels
            operation = query_type.lower()
            
            # Try to extract table name from statement (basic parsing)
            table = "unknown"
            if operation in ['select', 'insert', 'update', 'delete']:
                # Simple table name extraction (works for most cases)
                words = statement.strip().split()
                if len(words) > 1:
                    if operation == 'select':
                        # SELECT ... FROM table
                        from_idx = -1
                        for i, word in enumerate(words):
                            if word.upper() == 'FROM':
                                from_idx = i
                                break
                        if from_idx >= 0 and from_idx + 1 < len(words):
                            table = words[from_idx + 1].lower().strip(';')
                    elif operation == 'insert':
                        # INSERT INTO table
                        into_idx = -1
                        for i, word in enumerate(words):
                            if word.upper() == 'INTO':
                                into_idx = i
                                break
                        if into_idx >= 0 and into_idx + 1 < len(words):
                            table = words[into_idx + 1].lower().strip(';')
                    elif operation in ['update', 'delete']:
                        # UPDATE table / DELETE FROM table
                        if operation == 'update':
                            table = words[1].lower().strip(';')
                        else:
                            # DELETE FROM table
                            from_idx = -1
                            for i, word in enumerate(words):
                                if word.upper() == 'FROM':
                                    from_idx = i
                                    break
                            if from_idx >= 0 and from_idx + 1 < len(words):
                                table = words[from_idx + 1].lower().strip(';')
            
            # Record metrics
            db_queries_total.labels(operation=operation, table=table).inc()
            db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)
    
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Update connection pool metrics on connect"""
        pool = engine.pool
        # Update pool size metrics
        db_connection_pool_size.labels(state="active").set(pool.checkedout())
        db_connection_pool_size.labels(state="idle").set(pool.size() - pool.checkedout())
        db_connection_pool_overflow.set(pool.overflow())
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Update connection pool metrics on checkout"""
        pool = engine.pool
        # Update pool size metrics
        db_connection_pool_size.labels(state="active").set(pool.checkedout())
        db_connection_pool_size.labels(state="idle").set(pool.size() - pool.checkedout())
        db_connection_pool_overflow.set(pool.overflow())
    
    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Update connection pool metrics on checkin"""
        pool = engine.pool
        # Update pool size metrics
        db_connection_pool_size.labels(state="active").set(pool.checkedout())
        db_connection_pool_size.labels(state="idle").set(pool.size() - pool.checkedout())
        db_connection_pool_overflow.set(pool.overflow())


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
            connect_args={
                "connect_timeout": 5,  # 5 second timeout for connection
                "options": "-c statement_timeout=5000"  # 5 second timeout for queries (PostgreSQL)
            } if "postgresql" in settings.database_url else {
                "timeout": 5  # For SQLite
            }
        )
        
        # Explicitly set SQLAlchemy logger level
        sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
        if not settings.log_sqlalchemy:
            sqlalchemy_logger.setLevel(logging.WARNING)
            sqlalchemy_logger.propagate = False
        
        # Add event listeners for database metrics
        _setup_db_metrics(_engine)
    
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

