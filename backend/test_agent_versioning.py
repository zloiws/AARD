"""
Test script for agent versioning
"""
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.core.database import SessionLocal
from app.services.agent_service import AgentService
from app.models.agent import AgentStatus


def test_agent_versioning():
    """Test agent versioning functionality"""
    print("\n" + "="*60)
    print("Agent Versioning Tests")
    print("="*60)
    
    db = SessionLocal()
    try:
        service = AgentService(db)
        
        # Create base agent
        print("\n1. Creating base agent...")
        base_agent = service.create_agent(
            name=f"version_test_{uuid4().hex[:8]}",
            description="Base agent for versioning test",
            system_prompt="You are a test agent",
            capabilities=["test", "versioning"],
            created_by="test_script"
        )
        print(f"✓ Created base agent: {base_agent.name} (v{base_agent.version})")
        
        # Create version 2
        print("\n2. Creating version 2...")
        v2 = service.create_agent_version(
            agent_id=base_agent.id,
            description="Version 2 with updated description",
            system_prompt="You are an improved test agent"
        )
        print(f"✓ Created v{v2.version}: {v2.name}")
        print(f"  Parent: {v2.parent_agent_id == base_agent.id}")
        print(f"  Description updated: {v2.description != base_agent.description}")
        
        # Create version 3
        print("\n3. Creating version 3...")
        v3 = service.create_agent_version(
            agent_id=base_agent.id,
            capabilities=["test", "versioning", "enhanced"]
        )
        print(f"✓ Created v{v3.version}: {v3.name}")
        print(f"  Capabilities: {v3.capabilities}")
        
        # Get all versions
        print("\n4. Getting all versions...")
        all_versions = service.get_agent_versions(base_agent.id)
        print(f"✓ Found {len(all_versions)} versions:")
        for v in all_versions:
            print(f"  - v{v.version}: {v.name} (status: {v.status})")
        
        # Test rollback
        print("\n5. Testing rollback to version 1...")
        rollback_agent = service.rollback_to_version(v3.id, target_version=1)
        print(f"✓ Rolled back to v1, created v{rollback_agent.version}")
        print(f"  New agent: {rollback_agent.name}")
        print(f"  Description matches v1: {rollback_agent.description == base_agent.description}")
        
        # Verify version chain
        print("\n6. Verifying version chain...")
        final_versions = service.get_agent_versions(base_agent.id)
        print(f"✓ Total versions after rollback: {len(final_versions)}")
        versions_list = [v.version for v in final_versions]
        print(f"  Versions: {sorted(versions_list)}")
        
        # Cleanup - pause all versions
        print("\n7. Cleaning up...")
        for agent in final_versions:
            service.pause_agent(agent.id)
        print(f"✓ All test agents paused")
        
        print("\n" + "="*60)
        print("✓ All versioning tests passed!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_agent_versioning()
    sys.exit(0 if success else 1)

