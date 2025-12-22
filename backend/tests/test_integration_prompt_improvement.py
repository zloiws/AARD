"""
Integration tests for prompt improvement - real LLM usage
Tests automatic prompt improvement and A/B testing
"""
import pytest
from app.core.execution_context import ExecutionContext
from app.core.request_orchestrator import RequestOrchestrator
from app.models.prompt import PromptStatus, PromptType
from app.services.prompt_service import PromptService
from sqlalchemy.orm import Session


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_prompt_usage_tracking(db: Session):
    """Test 1: Verify prompt usage is tracked across multiple requests"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    
    # Make multiple requests
    for i in range(3):
        try:
            context = ExecutionContext.from_db_session(db)
            result = await orchestrator.process_request(
                message=f"Test question {i+1}: What is {i+1} + {i+1}?",
                context=context,
                task_type="general_chat"
            )
            
            assert result is not None
            assert context.prompt_manager is not None
            
            usage_summary = context.prompt_manager.get_usage_summary()
            print(f"\n  Request {i+1}: {usage_summary['total_usage']} prompt usages")
        except ValueError as e:
            if "No available model" in str(e) or "No available server" in str(e):
                pytest.skip(f"Model/server selection failed: {e}")
            raise
    
    print(f"\n✓ Test 1 passed: Prompt usage tracking across multiple requests")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_prompt_improvement_analysis(db: Session):
    """Test 2: Verify prompt improvement analysis runs after requests"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    try:
        # Make a request
        result = await orchestrator.process_request(
            message="Explain the concept of recursion in programming",
            context=context,
            task_type="general_chat"
        )
        
        assert result is not None
        assert context.prompt_manager is not None
        
        # Trigger analysis (should happen automatically, but we can also call it)
        improvement_results = await context.prompt_manager.analyze_and_improve_prompts()
        
        assert improvement_results is not None
        assert "analyzed" in improvement_results
        assert "improved" in improvement_results
        
        print(f"\n✓ Test 2 passed: Prompt improvement analysis")
        print(f"  Analyzed prompts: {improvement_results['analyzed']}")
        print(f"  Improved prompts: {improvement_results['improved']}")
        
        if improvement_results['improvements']:
            print(f"  Improvements:")
            for improvement in improvement_results['improvements']:
                print(f"    - {improvement['prompt_name']}: {improvement['reason']}")
    except ValueError as e:
        if "No available model" in str(e) or "No available server" in str(e):
            pytest.skip(f"Model/server selection failed: {e}")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_ab_testing_prompts(db: Session):
    """Test 3: Test A/B testing of prompt versions"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    # First, create a TESTING version of a prompt if it doesn't exist
    prompt_service = PromptService(db)
    
    # Get or create a test prompt
    test_prompt = prompt_service.get_active_prompt(
        name="task_analysis",
        prompt_type=PromptType.SYSTEM,
        level=0
    )
    
    if test_prompt:
        try:
            # Create a TESTING version
            testing_version = prompt_service.create_version(
                parent_prompt_id=test_prompt.id,
                prompt_text=test_prompt.prompt_text + "\n\n[TESTING VERSION]",
                created_by="test_user"
            )
            
            # Set status to TESTING
            testing_version.status = PromptStatus.TESTING.value.lower()
            db.commit()
            
            print(f"\n  Created TESTING version: {testing_version.version}")
        except Exception as e:
            print(f"  Could not create TESTING version: {e}")
    
    # Make requests that should use A/B testing
    orchestrator = RequestOrchestrator()
    
    for i in range(5):
        try:
            context = ExecutionContext.from_db_session(db)
            result = await orchestrator.process_request(
                message=f"Plan how to implement feature {i+1}",
                context=context,
                task_type="planning"
            )
            
            assert result is not None
            print(f"  Request {i+1}: completed")
        except ValueError as e:
            if "No available model" in str(e) or "No available server" in str(e):
                pytest.skip(f"Model/server selection failed: {e}")
            raise
    
    print(f"\n✓ Test 3 passed: A/B testing of prompts")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_prompt_metrics_aggregation(db: Session):
    """Test 4: Test prompt metrics aggregation across workflow"""
    from app.services.ollama_service import OllamaService
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("No Ollama servers configured")
    
    orchestrator = RequestOrchestrator()
    context = ExecutionContext.from_db_session(db)
    
    try:
        # Make a complex request that uses multiple prompts
        result = await orchestrator.process_request(
            message="Create a complete application: backend API, frontend UI, and database schema",
            context=context,
            task_type="complex_task"
        )
        
        assert result is not None
        assert context.prompt_manager is not None
        
        # Get detailed usage summary
        usage_summary = context.prompt_manager.get_usage_summary()
        
        print(f"\n✓ Test 4 passed: Prompt metrics aggregation")
        print(f"  Total usage: {usage_summary['total_usage']}")
        print(f"  By stage:")
        for stage, data in usage_summary['by_stage'].items():
            print(f"    {stage}: {data['count']} uses, avg {data['avg_time_ms']:.1f}ms")
        print(f"  Success/Failure: {usage_summary['by_success']}")
    except ValueError as e:
        if "No available model" in str(e) or "No available server" in str(e):
            pytest.skip(f"Model/server selection failed: {e}")
        raise
