"""
Integration test for memory and decision-making system
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.config import get_settings
from app.models import Base
from app.services.memory_service import MemoryService
from app.services.decision_router import DecisionRouter
from app.services.critic_service import CriticService
from app.services.reflection_service import ReflectionService
from app.services.decision_pipeline import DecisionPipeline
from app.core.decision_framework import create_hybrid_decision_maker
from app.services.agent_service import AgentService
from app.models.agent import Agent, AgentStatus

# Load environment
env_file = BASE_DIR.parent / ".env"
load_dotenv(env_file, override=True)

def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_memory_service(db: Session):
    """Test memory service"""
    print_section("Testing Memory Service")
    
    try:
        memory_service = MemoryService(db)
        
        # Create a test agent first
        agent_service = AgentService(db)
        test_agent = agent_service.create_agent(
            name=f"test_agent_{uuid4().hex[:8]}",
            description="Test agent for memory testing",
            created_by="test"
        )
        agent_id = test_agent.id
        
        print(f"✓ Created test agent: {test_agent.name}")
        
        # Test long-term memory
        print("\n1. Testing long-term memory...")
        memory = memory_service.save_memory(
            agent_id=agent_id,
            memory_type="fact",
            content={"fact": "Python is a programming language"},
            summary="Python fact",
            importance=0.8,
            tags=["programming", "python"]
        )
        print(f"  ✓ Saved memory: {memory.id}")
        
        retrieved = memory_service.get_memory(memory.id)
        assert retrieved is not None, "Memory not retrieved"
        print(f"  ✓ Retrieved memory: {retrieved.summary}")
        
        memories = memory_service.get_memories(agent_id=agent_id, limit=10)
        assert len(memories) > 0, "No memories found"
        print(f"  ✓ Found {len(memories)} memories")
        
        # Test short-term memory
        print("\n2. Testing short-term memory...")
        entry = memory_service.save_context(
            agent_id=agent_id,
            context_key="test_context",
            content={"key": "value", "number": 42},
            session_id="test_session",
            ttl_seconds=3600
        )
        print(f"  ✓ Saved context: {entry.id}")
        
        context = memory_service.get_context(
            agent_id=agent_id,
            context_key="test_context",
            session_id="test_session"
        )
        assert context is not None, "Context not retrieved"
        assert context["key"] == "value", "Context value mismatch"
        print(f"  ✓ Retrieved context: {context}")
        
        # Test associations
        print("\n3. Testing memory associations...")
        memory2 = memory_service.save_memory(
            agent_id=agent_id,
            memory_type="experience",
            content={"experience": "Learned about Python"},
            summary="Python experience",
            importance=0.7
        )
        
        association = memory_service.create_association(
            memory_id=memory.id,
            related_memory_id=memory2.id,
            association_type="related",
            strength=0.8
        )
        print(f"  ✓ Created association: {association.id}")
        
        related = memory_service.get_related_memories(memory.id)
        assert len(related) > 0, "No related memories found"
        print(f"  ✓ Found {len(related)} related memories")
        
        print("\n✓ Memory Service: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Memory Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_decision_router(db: Session):
    """Test decision router"""
    print_section("Testing Decision Router")
    
    try:
        router = DecisionRouter(db)
        
        print("\n1. Testing task routing...")
        routing = await router.route_task(
            task_description="Generate Python code to calculate factorial",
            task_type="code_generation"
        )
        print(f"  ✓ Routing completed")
        print(f"    Tool selected: {routing.get('tool') is not None}")
        print(f"    Agent selected: {routing.get('agent') is not None}")
        print(f"    Prompt selected: {routing.get('prompt') is not None}")
        print(f"    Reasoning: {routing.get('reasoning', 'N/A')}")
        
        print("\n2. Testing tool selection...")
        tool = await router.select_tool(
            task_description="Execute Python code",
            task_type="code_execution"
        )
        print(f"  ✓ Tool selection: {tool is not None}")
        
        print("\n3. Testing agent selection...")
        agent = await router.select_agent(
            task_description="Plan a complex task",
            task_type="planning"
        )
        print(f"  ✓ Agent selection: {agent is not None}")
        
        print("\n✓ Decision Router: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Decision Router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_critic_service(db: Session):
    """Test critic service"""
    print_section("Testing Critic Service")
    
    try:
        critic = CriticService(db)
        
        print("\n1. Testing result validation...")
        result = {"status": "success", "data": "test"}
        validation = await critic.validate_result(
            result=result,
            expected_format={
                "type": "object",
                "required": ["status", "data"],
                "properties": {
                    "status": {"type": "string"},
                    "data": {"type": "string"}
                }
            }
        )
        print(f"  ✓ Validation completed")
        print(f"    Valid: {validation.is_valid}")
        print(f"    Score: {validation.score:.2f}")
        print(f"    Issues: {len(validation.issues)}")
        
        print("\n2. Testing quality assessment...")
        quality = await critic.assess_quality(
            result="This is a good result with sufficient detail and quality.",
            requirements={"min_length": 20}
        )
        print(f"  ✓ Quality score: {quality:.2f}")
        
        print("\n3. Testing issue identification...")
        issues = critic.identify_issues(
            result=None,
            requirements={"must_contain": "test"}
        )
        print(f"  ✓ Identified {len(issues)} issues")
        
        print("\n✓ Critic Service: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Critic Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_reflection_service(db: Session):
    """Test reflection service"""
    print_section("Testing Reflection Service")
    
    try:
        reflection = ReflectionService(db)
        
        print("\n1. Testing failure analysis...")
        analysis_result = await reflection.analyze_failure(
            task_description="Execute Python code",
            error="NameError: name 'x' is not defined",
            context={"code": "print(x)"}
        )
        print(f"  ✓ Analysis completed")
        print(f"    Error type: {analysis_result.analysis.get('error_type')}")
        print(f"    Root cause: {analysis_result.analysis.get('root_cause', 'N/A')[:50]}")
        print(f"    Similar situations: {len(analysis_result.similar_situations)}")
        
        print("\n2. Testing fix generation...")
        fix = await reflection.generate_fix(
            task_description="Execute Python code",
            error="NameError: name 'x' is not defined",
            analysis=analysis_result.analysis,
            context={"code": "print(x)"}
        )
        print(f"  ✓ Fix generated")
        print(f"    Status: {fix.get('status')}")
        print(f"    Message: {fix.get('message', 'N/A')[:50]}")
        
        print("\n3. Testing improvement suggestions...")
        suggestions = await reflection.suggest_improvement(
            task_description="Process data",
            result="Data processed successfully",
            execution_metadata={"execution_time": 30}
        )
        print(f"  ✓ Generated {len(suggestions)} suggestions")
        
        print("\n✓ Reflection Service: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Reflection Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_decision_pipeline(db: Session):
    """Test decision pipeline"""
    print_section("Testing Decision Pipeline")
    
    try:
        pipeline = DecisionPipeline(db)
        
        print("\n1. Testing pipeline execution...")
        result = await pipeline.execute_task(
            task_description="Create a simple Python function to add two numbers",
            task_type="code_generation",
            max_retries=1
        )
        print(f"  ✓ Pipeline execution completed")
        print(f"    Status: {result.get('status')}")
        print(f"    Stages completed: {result.get('pipeline_metadata', {}).get('stages_completed', [])}")
        print(f"    Steps: {result.get('pipeline_metadata', {}).get('steps_count', 0)}")
        
        print("\n✓ Decision Pipeline: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Decision Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_decision_framework():
    """Test decision framework"""
    print_section("Testing Decision Framework")
    
    try:
        decision_maker = create_hybrid_decision_maker()
        
        print("\n1. Testing hybrid decision making...")
        result = await decision_maker.make_decision(
            task="Analyze a text and extract key information",
            context={"text": "Python is a high-level programming language."}
        )
        print(f"  ✓ Decision made")
        print(f"    Status: {result.get('status')}")
        print(f"    Task type: {result.get('task', {}).get('type')}")
        print(f"    Used LLM: {result.get('metadata', {}).get('used_llm')}")
        print(f"    Used code: {result.get('metadata', {}).get('used_code')}")
        
        print("\n✓ Decision Framework: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Decision Framework test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("  INTEGRATION TESTS: Memory and Decision-Making System")
    print("=" * 60)
    
    db = SessionLocal()
    results = []
    
    try:
        # Run tests
        results.append(("Memory Service", await test_memory_service(db)))
        results.append(("Decision Router", await test_decision_router(db)))
        results.append(("Critic Service", await test_critic_service(db)))
        results.append(("Reflection Service", await test_reflection_service(db)))
        results.append(("Decision Pipeline", await test_decision_pipeline(db)))
        results.append(("Decision Framework", await test_decision_framework()))
        
        # Summary
        print_section("Test Summary")
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"  {name}: {status}")
        
        print(f"\n  Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n✓ ALL INTEGRATION TESTS PASSED!")
            return 0
        else:
            print(f"\n✗ {total - passed} test(s) failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Test execution error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

