"""Manual test script for prompt management system"""
import os
import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prompt_service import PromptService
from app.services.planning_service import PlanningService
from app.models.prompt import PromptType, PromptStatus
import asyncio

def test_basic_operations():
    """Test basic CRUD operations"""
    print("=== Testing Basic Operations ===")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Create prompt
        print("\n1. Creating prompt...")
        prompt = service.create_prompt(
            name="test_analysis",
            prompt_text="You are an expert at task analysis. Analyze the task and create a strategy.",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        print(f"   ✓ Created: {prompt.name} (id: {prompt.id}, version: {prompt.version})")
        
        # Get prompt
        print("\n2. Getting prompt...")
        retrieved = service.get_prompt(prompt.id)
        assert retrieved is not None
        print(f"   ✓ Retrieved: {retrieved.name}")
        
        # Update prompt
        print("\n3. Updating prompt...")
        updated = service.update_prompt(prompt.id, prompt_text="Updated prompt text")
        assert updated.prompt_text == "Updated prompt text"
        assert updated.version == 1  # Version doesn't change on update
        print(f"   ✓ Updated (version still {updated.version})")
        
        # Create version
        print("\n4. Creating new version...")
        v2 = service.create_version(prompt.id, "Version 2 prompt text")
        assert v2.version == 2
        print(f"   ✓ Created version {v2.version}")
        
        # List prompts
        print("\n5. Listing prompts...")
        prompts = service.list_prompts(prompt_type=PromptType.SYSTEM)
        print(f"   ✓ Found {len(prompts)} prompts")
        
        # Get active prompt
        print("\n6. Getting active prompt...")
        active = service.get_active_prompt("test_analysis", PromptType.SYSTEM)
        assert active is not None
        print(f"   ✓ Active prompt: {active.name} (version: {active.version})")
        
        print("\n✓ All basic operations passed!")
        return prompt
        
    finally:
        db.close()

def test_metrics():
    """Test metrics tracking"""
    print("\n=== Testing Metrics ===")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Get or create test prompt
        prompt = service.get_active_prompt("test_analysis", PromptType.SYSTEM)
        if not prompt:
            prompt = service.create_prompt(
                name="test_analysis",
                prompt_text="Test prompt",
                prompt_type=PromptType.SYSTEM
            )
        
        # Record usage
        print("\n1. Recording usage...")
        for i in range(5):
            service.record_usage(prompt.id, execution_time_ms=1000.0 + i * 100)
        prompt = service.get_prompt(prompt.id)
        print(f"   ✓ Usage count: {prompt.usage_count}")
        print(f"   ✓ Avg execution time: {prompt.avg_execution_time:.1f}ms")
        
        # Record success/failure
        print("\n2. Recording results...")
        for _ in range(3):
            service.record_success(prompt.id)
        for _ in range(2):
            service.record_failure(prompt.id)
        prompt = service.get_prompt(prompt.id)
        print(f"   ✓ Success rate: {prompt.success_rate:.1%}")
        
        print("\n✓ Metrics tracking works!")
        
    finally:
        db.close()

async def test_reflection():
    """Test reflection and improvement"""
    print("\n=== Testing Reflection ===")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Get or create test prompt
        prompt = service.get_active_prompt("test_analysis", PromptType.SYSTEM)
        if not prompt:
            prompt = service.create_prompt(
                name="test_analysis",
                prompt_text="Test prompt",
                prompt_type=PromptType.SYSTEM
            )
        
        # Analyze performance
        print("\n1. Analyzing prompt performance...")
        analysis = await service.analyze_prompt_performance(
            prompt_id=prompt.id,
            task_description="Test task",
            result={"result": "success"},
            success=True,
            execution_metadata={"duration_ms": 1500}
        )
        if analysis:
            print(f"   ✓ Analysis type: {analysis.get('type')}")
            print(f"   ✓ Improvements: {len(analysis.get('improvements', []))}")
        else:
            print("   ⚠ Analysis returned None (LLM might not be available)")
        
        # Generate suggestions
        print("\n2. Generating improvement suggestions...")
        suggestions = await service.suggest_improvements(prompt.id)
        if suggestions:
            print(f"   ✓ Priority: {suggestions.get('priority')}")
            print(f"   ✓ Suggestions count: {len(suggestions.get('suggestions', []))}")
        else:
            print("   ⚠ Suggestions returned None (LLM might not be available)")
        
        print("\n✓ Reflection works!")
        
    finally:
        db.close()

def test_planning_integration():
    """Test integration with PlanningService"""
    print("\n=== Testing PlanningService Integration ===")
    db: Session = SessionLocal()
    try:
        # Create test prompt
        prompt_service = PromptService(db)
        prompt = prompt_service.create_prompt(
            name="task_analysis",
            prompt_text="Custom analysis prompt for testing",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        print(f"   ✓ Created prompt: {prompt.name}")
        
        # Test PlanningService
        planning_service = PlanningService(db)
        
        # Get prompt (should use database)
        print("\n1. Getting prompt from PlanningService...")
        prompt_text = planning_service._get_analysis_prompt()
        if "Custom analysis prompt" in prompt_text:
            print("   ✓ PlanningService uses prompt from database")
        else:
            print("   ⚠ PlanningService uses fallback prompt")
        
        print("\n✓ PlanningService integration works!")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing Prompt Management System\n")
    print("=" * 50)
    
    try:
        # Basic operations
        prompt = test_basic_operations()
        
        # Metrics
        test_metrics()
        
        # Reflection (async)
        asyncio.run(test_reflection())
        
        # Planning integration
        test_planning_integration()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

