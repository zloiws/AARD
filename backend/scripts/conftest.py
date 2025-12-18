import pytest

from app.core.database import SessionLocal
from app.services.system_setting_service import SystemSettingService


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


