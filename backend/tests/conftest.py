"""
Pytest configuration and fixtures
"""
import sys
from pathlib import Path
import pytest
from sqlalchemy.orm import Session
import os

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal, Base, engine


@pytest.fixture(scope="function")
def db() -> Session:
    """Create a database session for testing"""
    # Disable tracing during tests to avoid background exporters touching DB before schema is created
    os.environ.setdefault("ENABLE_TRACING", "false")
    # Ensure a clean database schema for each test
    # Import all models so they are registered with Base.metadata
    try:
        import app.models  # noqa: F401
    except Exception:
        pass
    # Ensure clean schema for tests: drop and recreate public schema to avoid
    # dependent-object ordering issues (CASCADE ensures foreign keys removed).
    # This operation is safe in test environments where database is ephemeral.
    try:
        with engine.connect() as conn:
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            # Use driver-level SQL execution for DDL strings
            conn.exec_driver_sql("DROP SCHEMA public CASCADE;")
            conn.exec_driver_sql("CREATE SCHEMA public;")
    except Exception:
        # Fallback to metadata-based drop/create if schema operations are not permitted
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    else:
        # After recreating schema, create tables
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

