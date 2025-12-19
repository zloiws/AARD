"""Debug script for ServiceRegistry tests"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.execution_context import ExecutionContext
from app.core.service_registry import get_service_registry
from app.services.prompt_service import PromptService

db = SessionLocal()
try:
    registry = get_service_registry()
    
    print("Test 1: get_service_by_db")
    try:
        service1 = registry.get_service_by_db(PromptService, db)
        print(f"  ✅ Service created: {service1}")
        print(f"  Service.db == db: {service1.db == db}")
        print(f"  Service type: {type(service1)}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest 2: get_service with context")
    try:
        context = ExecutionContext.from_db_session(db)
        service2 = registry.get_service(PromptService, context)
        print(f"  ✅ Service created: {service2}")
        print(f"  Service.db == context.db: {service2.db == context.db}")
        print(f"  Service.db == db: {service2.db == db}")
        print(f"  Service type: {type(service2)}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
finally:
    db.close()
