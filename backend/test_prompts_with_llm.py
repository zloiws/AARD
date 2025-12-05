"""Test prompt management system with LLM"""
import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prompt_service import PromptService
from app.models.prompt import PromptType
from app.services.ollama_service import OllamaService
from app.core.model_selector import ModelSelector

def check_llm_availability():
    """Check if LLM is available"""
    print("=== Checking LLM Availability ===\n")
    db: Session = SessionLocal()
    try:
        # Check for active servers
        servers = OllamaService.get_all_active_servers(db)
        print(f"Active Ollama servers: {len(servers)}")
        for server in servers:
            print(f"  - {server.name} ({server.url})")
        
        if not servers:
            print("  ⚠ No active servers found!")
            return None, None
        
        # Get planning model
        model_selector = ModelSelector(db)
        planning_model = model_selector.get_planning_model()
        
        if not planning_model:
            print("  ⚠ No planning model found!")
            return None, None
        
        server = model_selector.get_server_for_model(planning_model)
        if not server:
            print("  ⚠ No server found for planning model!")
            return None, None
        
        print(f"\n✓ LLM available:")
        print(f"  Model: {planning_model.model_name}")
        print(f"  Server: {server.name} ({server.get_api_url()})")
        return planning_model, server
        
    finally:
        db.close()

async def test_llm_reflection():
    """Test reflection with LLM"""
    print("\n=== Testing LLM Reflection ===\n")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Get or create test prompt
        prompt = service.get_active_prompt("test_analysis", PromptType.SYSTEM)
        if not prompt:
            prompt = service.create_prompt(
                name="test_analysis",
                prompt_text="You are an expert at task analysis. Analyze the task and create a strategy.",
                prompt_type=PromptType.SYSTEM,
                level=0
            )
        
        print(f"Testing with prompt: {prompt.name} (id: {prompt.id})")
        
        # Test 1: Analyze successful performance
        print("\n1. Analyzing successful performance...")
        analysis = await service.analyze_prompt_performance(
            prompt_id=prompt.id,
            task_description="Create a plan for building a web application",
            result={
                "strategy": {
                    "approach": "Iterative development",
                    "steps": ["Design", "Implement", "Test"]
                }
            },
            success=True,
            execution_metadata={
                "duration_ms": 2000,
                "stage": "analysis",
                "response_length": 500
            }
        )
        
        if analysis:
            print(f"   ✓ Analysis type: {analysis.get('type')}")
            improvements = analysis.get('improvements', [])
            print(f"   ✓ Improvements: {len(improvements)}")
            if improvements:
                for i, imp in enumerate(improvements[:3], 1):
                    print(f"      {i}. {imp[:80]}...")
        else:
            print("   ✗ Analysis returned None")
        
        # Test 2: Analyze failed performance
        print("\n2. Analyzing failed performance...")
        analysis = await service.analyze_prompt_performance(
            prompt_id=prompt.id,
            task_description="Create a plan for building a web application",
            result="Timeout error: Request took too long",
            success=False,
            execution_metadata={
                "error_type": "TimeoutError",
                "stage": "analysis",
                "duration_ms": 60000
            }
        )
        
        if analysis:
            print(f"   ✓ Analysis type: {analysis.get('type')}")
            if analysis.get('type') == 'failure_analysis':
                failure_analysis = analysis.get('analysis', {})
                print(f"   ✓ Error type: {failure_analysis.get('error_type', 'unknown')}")
                suggested_fix = analysis.get('suggested_fix')
                if suggested_fix:
                    print(f"   ✓ Suggested fix available")
        else:
            print("   ✗ Analysis returned None")
        
        print("\n✓ LLM Reflection tests completed!")
        
    finally:
        db.close()

async def test_llm_suggestions():
    """Test LLM-based improvement suggestions"""
    print("\n=== Testing LLM Suggestions ===\n")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Get or create test prompt with low success rate
        prompt = service.get_active_prompt("test_analysis", PromptType.SYSTEM)
        if not prompt:
            prompt = service.create_prompt(
                name="test_analysis",
                prompt_text="You are an expert at task analysis.",
                prompt_type=PromptType.SYSTEM,
                level=0
            )
        
        # Lower success rate
        print("Setting up test data (lowering success rate)...")
        for _ in range(7):
            service.record_failure(prompt.id)
        for _ in range(3):
            service.record_success(prompt.id)
        
        prompt = service.get_prompt(prompt.id)
        print(f"Current success_rate: {prompt.success_rate:.1%}")
        
        # Generate suggestions
        print("\nGenerating improvement suggestions with LLM...")
        suggestions = await service.suggest_improvements(prompt.id)
        
        if suggestions:
            print(f"   ✓ Priority: {suggestions.get('priority')}")
            print(f"   ✓ Expected effect: {suggestions.get('expected_effect')}")
            
            all_suggestions = suggestions.get('suggestions', [])
            print(f"   ✓ Total suggestions: {len(all_suggestions)}")
            
            # Show suggestions
            print("\n   Suggestions:")
            for i, suggestion in enumerate(all_suggestions[:5], 1):
                if isinstance(suggestion, dict):
                    msg = suggestion.get('message', str(suggestion))
                else:
                    msg = str(suggestion)
                print(f"      {i}. {msg[:100]}...")
            
            # Check if LLM suggestions are included
            analysis = suggestions.get('analysis', {})
            metrics = analysis.get('metrics', {})
            print(f"\n   Metrics analysis:")
            print(f"      - Success rate: {metrics.get('success_rate')}")
            print(f"      - Issues found: {len(metrics.get('issues', []))}")
        else:
            print("   ✗ Suggestions returned None")
        
        print("\n✓ LLM Suggestions tests completed!")
        
    finally:
        db.close()

async def test_llm_version_creation():
    """Test LLM-based improved version creation"""
    print("\n=== Testing LLM Version Creation ===\n")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Get or create test prompt
        prompt = service.get_active_prompt("test_analysis", PromptType.SYSTEM)
        if not prompt:
            prompt = service.create_prompt(
                name="test_analysis",
                prompt_text="You are an expert at task analysis. Analyze the task.",
                prompt_type=PromptType.SYSTEM,
                level=0
            )
        
        print(f"Original prompt (version {prompt.version}):")
        print(f"  {prompt.prompt_text[:100]}...")
        
        # Create improved version with suggestions
        print("\nCreating improved version with LLM...")
        suggestions_list = [
            "Make instructions more specific",
            "Add examples of expected output",
            "Clarify the format of the response"
        ]
        
        improved = await service.create_improved_version(
            prompt_id=prompt.id,
            suggestions=suggestions_list
        )
        
        if improved:
            print(f"   ✓ Created version {improved.version}")
            print(f"   ✓ Status: {improved.status}")
            print(f"   ✓ Parent: {improved.parent_prompt_id == prompt.id}")
            
            print(f"\n   Improved prompt text:")
            print(f"   {improved.prompt_text[:200]}...")
            
            # Check improvement history
            history = improved.improvement_history or []
            version_creations = [h for h in history if h.get('type') == 'version_creation']
            if version_creations:
                print(f"\n   ✓ Improvement metadata saved")
                print(f"      Suggestions used: {len(version_creations[0].get('suggestions_used', []))}")
        else:
            print("   ✗ Improved version creation returned None")
        
        print("\n✓ LLM Version Creation tests completed!")
        
    finally:
        db.close()

async def test_auto_improvement():
    """Test automatic improvement triggering"""
    print("\n=== Testing Auto-Improvement ===\n")
    db: Session = SessionLocal()
    try:
        service = PromptService(db)
        
        # Create test prompt
        prompt = service.create_prompt(
            name="test_auto_improve",
            prompt_text="Test prompt for auto-improvement",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        
        # Lower success rate below threshold
        print("Setting up conditions for auto-improvement...")
        for _ in range(9):
            service.record_failure(prompt.id)
        for _ in range(1):
            service.record_success(prompt.id)
        
        prompt = service.get_prompt(prompt.id)
        print(f"Success rate: {prompt.success_rate:.1%} (threshold: 50%)")
        
        # Trigger auto-improvement
        print("\nTriggering auto-improvement...")
        improved = await service.auto_create_improved_version_if_needed(
            prompt.id,
            success_rate_threshold=0.5
        )
        
        if improved:
            print(f"   ✓ Auto-created version {improved.version}")
            print(f"   ✓ Status: {improved.status}")
        else:
            print("   ⚠ Auto-improvement not triggered (LLM might not be available)")
        
        print("\n✓ Auto-Improvement tests completed!")
        
    finally:
        db.close()

async def main():
    """Run all LLM tests"""
    print("=" * 60)
    print("Testing Prompt Management System with LLM")
    print("=" * 60)
    
    # Check LLM availability
    planning_model, server = check_llm_availability()
    
    if not planning_model or not server:
        print("\n⚠ LLM is not available. Some tests will be skipped.")
        print("To test with LLM:")
        print("1. Ensure Ollama server is running")
        print("2. Add server to database via Settings")
        print("3. Sync models for the server")
        return
    
    try:
        # Run tests
        await test_llm_reflection()
        await test_llm_suggestions()
        await test_llm_version_creation()
        await test_auto_improvement()
        
        print("\n" + "=" * 60)
        print("✓ All LLM tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

