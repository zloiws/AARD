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


@pytest.fixture(scope="function")
def client(db: Session):
    """Create test client with database dependency override"""
    import sys
    import importlib.util
    from pathlib import Path
    
    # Ensure backend directory is in path
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    # Import main module directly
    main_path = backend_dir / "main.py"
    spec = importlib.util.spec_from_file_location("main", main_path)
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    app = main_module.app
    
    from fastapi.testclient import TestClient
    from app.core.database import get_db
    
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

