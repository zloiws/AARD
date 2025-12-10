"""
Datetime utilities for AARD platform
Provides timezone-aware datetime functions to replace deprecated datetime.utcnow()
"""
from datetime import datetime, timezone
from typing import Callable


def utc_now() -> datetime:
    """
    Get current UTC time (replacement for deprecated datetime.utcnow())
    
    Returns:
        datetime: Current UTC time with timezone awareness
        
    Example:
        >>> from app.utils.datetime_utils import utc_now
        >>> now = utc_now()
        >>> print(now.tzinfo)
        UTC
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Get current UTC time as ISO format string
    
    Returns:
        str: Current UTC time in ISO format
        
    Example:
        >>> from app.utils.datetime_utils import utc_now_iso
        >>> timestamp = utc_now_iso()
        >>> print(timestamp)
        2025-12-10T10:00:00.123456+00:00
    """
    return datetime.now(timezone.utc).isoformat()


def utc_now_callable() -> Callable[[], datetime]:
    """
    Get a callable that returns current UTC time
    For use in SQLAlchemy Column defaults
    
    Returns:
        Callable: Function that returns current UTC time
        
    Example:
        >>> from app.utils.datetime_utils import utc_now_callable
        >>> created_at = Column(DateTime, default=utc_now_callable())
    """
    return lambda: datetime.now(timezone.utc)
