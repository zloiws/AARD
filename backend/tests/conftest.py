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
    # Ensure clean schema for tests: use SQLAlchemy metadata drop/create.
    # Avoid using `DROP SCHEMA public` to prevent statement_timeout issues on some DBs.
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        # Ignore drop errors and try to create tables anyway
        pass
    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # If creation fails, tests will surface the error
        pass
    # Optionally seed Ollama servers into test DB if requested via env var (useful for real-LLM tests)
    try:
        if os.environ.get("SEED_OLLAMA_SERVERS") == "1":
            try:
                # Import and run seeding script which uses the same DB session configuration
                from backend.scripts.seed_ollama_servers import main as _seed_main
                _seed_main()
            except Exception:
                # Don't fail tests if seeding fails; tests will report lack of servers
                pass
    except Exception:
        pass
    # Try to enable vector extension if using PostgreSQL (best-effort)
    try:
        if getattr(engine.dialect, "name", "") == "postgresql":
            try:
                with engine.connect() as conn:
                    conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
            except Exception:
                # ignore if extension cannot be created in CI/local environments
                pass
    except Exception:
        pass
    # Check whether extension was created and expose via env var for tests
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');"))
            exists = bool(res.scalar())
            if exists:
                os.environ["VECTOR_EXTENSION_AVAILABLE"] = "1"
            else:
                os.environ["VECTOR_EXTENSION_AVAILABLE"] = "0"
    except Exception:
        os.environ["VECTOR_EXTENSION_AVAILABLE"] = "0"
    
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

