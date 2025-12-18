import pytest
from app.core.database import SessionLocal, Base, engine
from app.services.system_setting_service import SystemSettingService
import os

# Ensure models are imported and database schema exists for script tests
try:
    import app.models  # noqa: F401
except Exception:
    pass

# Create all tables if they don't exist (best-effort for test environment)
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    # If DB is not available or creation fails, tests may still run and surface errors
    pass


@pytest.fixture
def service():
    """
    Fixture to provide SystemSettingService for scripts tests.
    Uses a real DB session from SessionLocal and ensures cleanup.
    """
    db = SessionLocal()
    service = SystemSettingService(db)
    try:
        yield service
    finally:
        try:
            db.close()
        except Exception:
            pass


