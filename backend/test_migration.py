"""Test migration and API"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, get_db
from sqlalchemy import inspect, text
from app.models import *

def test_migration():
    """Test that migration was applied successfully"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = [
        'tasks', 'artifacts', 'artifact_dependencies',
        'ollama_servers', 'ollama_models',
        'prompts', 'approval_requests', 'evolution_history', 
        'feedback', 'plans'
    ]
    
    print("=" * 60)
    print("Migration Test Results")
    print("=" * 60)
    
    missing = []
    for table in expected_tables:
        if table in tables:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} - MISSING")
            missing.append(table)
    
    print("\n" + "=" * 60)
    if missing:
        print(f"❌ Migration incomplete. Missing tables: {missing}")
        return False
    else:
        print("✅ All tables created successfully!")
        return True

def test_models():
    """Test that models can be imported and used"""
    print("\n" + "=" * 60)
    print("Model Import Test")
    print("=" * 60)
    
    try:
        from app.models.prompt import Prompt, PromptType, PromptStatus
        from app.models.approval import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus
        from app.models.evolution import EvolutionHistory, Feedback, EntityType
        from app.models.plan import Plan, PlanStatus
        
        print("✅ All models imported successfully")
        
        # Test enum values
        print(f"✅ PromptType: {[e.value for e in PromptType]}")
        print(f"✅ ApprovalRequestType: {[e.value for e in ApprovalRequestType]}")
        print(f"✅ EntityType: {[e.value for e in EntityType]}")
        
        return True
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_services():
    """Test that services can be instantiated"""
    print("\n" + "=" * 60)
    print("Service Import Test")
    print("=" * 60)
    
    try:
        db = next(get_db())
        from app.services.approval_service import ApprovalService
        from app.services.artifact_generator import ArtifactGenerator
        from app.core.ollama_client import OllamaClient
        
        approval_service = ApprovalService(db)
        print("✅ ApprovalService created")
        
        ollama_client = OllamaClient()
        artifact_generator = ArtifactGenerator(db, ollama_client)
        print("✅ ArtifactGenerator created")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Error creating services: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 Testing Evolution System Implementation\n")
    
    migration_ok = test_migration()
    models_ok = test_models()
    services_ok = test_services()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Migration: {'✅ PASS' if migration_ok else '❌ FAIL'}")
    print(f"Models: {'✅ PASS' if models_ok else '❌ FAIL'}")
    print(f"Services: {'✅ PASS' if services_ok else '❌ FAIL'}")
    
    if migration_ok and models_ok and services_ok:
        print("\n🎉 All tests passed! System is ready for API testing.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Please check errors above.")
        sys.exit(1)

