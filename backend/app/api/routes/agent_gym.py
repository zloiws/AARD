"""
API routes for Agent Gym (testing and benchmarking)
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.agent_gym_service import AgentGymService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/agent-gym", tags=["agent-gym"])


# Request/Response models
class CreateTestRequest(BaseModel):
    """Request to create a test"""
    name: str
    agent_id: str
    test_type: str
    input_data: dict
    expected_output: Optional[dict] = None
    validation_rules: Optional[dict] = None
    timeout_seconds: int = 60
    max_retries: int = 0
    required_tools: Optional[List[str]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    created_by: Optional[str] = None


class TestResponse(BaseModel):
    """Test response model"""
    id: str
    name: str
    description: Optional[str]
    test_type: str
    agent_id: str
    input_data: Optional[dict]
    expected_output: Optional[dict]
    validation_rules: Optional[dict]
    timeout_seconds: int
    max_retries: int
    required_tools: Optional[List[str]]
    created_by: Optional[str]
    created_at: str
    tags: Optional[List[str]]


class RunTestRequest(BaseModel):
    """Request to run a test"""
    run_by: Optional[str] = None
    notes: Optional[str] = None


class TestRunResponse(BaseModel):
    """Test run response model"""
    id: str
    test_id: str
    agent_id: str
    agent_version: Optional[int]
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    output_data: Optional[dict]
    validation_passed: Optional[str]
    validation_details: Optional[dict]
    tokens_used: Optional[int]
    llm_calls: Optional[int]
    tool_calls: Optional[int]
    error_message: Optional[str]
    error_type: Optional[str]


class CreateBenchmarkRequest(BaseModel):
    """Request to create a benchmark"""
    name: str
    benchmark_type: str
    agent_ids: List[str]
    tasks: List[dict]
    iterations: int = 1
    timeout_seconds: int = 300
    parallel_execution: bool = False
    metrics: Optional[List[str]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    created_by: Optional[str] = None


class BenchmarkResponse(BaseModel):
    """Benchmark response model"""
    id: str
    name: str
    description: Optional[str]
    benchmark_type: str
    agent_ids: List[str]
    tasks: List[dict]
    iterations: int
    timeout_seconds: int
    parallel_execution: str
    metrics: Optional[List[str]]
    created_by: Optional[str]
    created_at: str
    tags: Optional[List[str]]


class BenchmarkRunResponse(BaseModel):
    """Benchmark run response model"""
    id: str
    benchmark_id: str
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    agent_results: dict
    summary: Optional[dict]
    error_message: Optional[str]
    error_type: Optional[str]


@router.post("/tests", response_model=TestResponse)
async def create_test(
    request: CreateTestRequest,
    db: Session = Depends(get_db)
):
    """Create a new agent test"""
    try:
        gym_service = AgentGymService(db)
        test = gym_service.create_test(
            name=request.name,
            agent_id=UUID(request.agent_id),
            test_type=request.test_type,
            input_data=request.input_data,
            expected_output=request.expected_output,
            validation_rules=request.validation_rules,
            timeout_seconds=request.timeout_seconds,
            max_retries=request.max_retries,
            required_tools=request.required_tools,
            description=request.description,
            tags=request.tags,
            created_by=request.created_by
        )
        
        return TestResponse(
            id=str(test.id),
            name=test.name,
            description=test.description,
            test_type=test.test_type,
            agent_id=str(test.agent_id),
            input_data=test.input_data,
            expected_output=test.expected_output,
            validation_rules=test.validation_rules,
            timeout_seconds=test.timeout_seconds,
            max_retries=test.max_retries,
            required_tools=test.required_tools,
            created_by=test.created_by,
            created_at=test.created_at.isoformat(),
            tags=test.tags
        )
    except Exception as e:
        logger.error(f"Error creating test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests", response_model=List[TestResponse])
async def list_tests(
    agent_id: Optional[str] = None,
    test_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List agent tests"""
    try:
        from app.models.agent_test import AgentTest
        from sqlalchemy import and_
        
        query = db.query(AgentTest)
        
        if agent_id:
            query = query.filter(AgentTest.agent_id == UUID(agent_id))
        if test_type:
            query = query.filter(AgentTest.test_type == test_type)
        
        tests = query.all()
        
        return [
            TestResponse(
                id=str(t.id),
                name=t.name,
                description=t.description,
                test_type=t.test_type,
                agent_id=str(t.agent_id),
                input_data=t.input_data,
                expected_output=t.expected_output,
                validation_rules=t.validation_rules,
                timeout_seconds=t.timeout_seconds,
                max_retries=t.max_retries,
                required_tools=t.required_tools,
                created_by=t.created_by,
                created_at=t.created_at.isoformat(),
                tags=t.tags
            )
            for t in tests
        ]
    except Exception as e:
        logger.error(f"Error listing tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}", response_model=TestResponse)
async def get_test(
    test_id: str,
    db: Session = Depends(get_db)
):
    """Get a test by ID"""
    try:
        from app.models.agent_test import AgentTest
        
        test = db.query(AgentTest).filter(AgentTest.id == UUID(test_id)).first()
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        
        return TestResponse(
            id=str(test.id),
            name=test.name,
            description=test.description,
            test_type=test.test_type,
            agent_id=str(test.agent_id),
            input_data=test.input_data,
            expected_output=test.expected_output,
            validation_rules=test.validation_rules,
            timeout_seconds=test.timeout_seconds,
            max_retries=test.max_retries,
            required_tools=test.required_tools,
            created_by=test.created_by,
            created_at=test.created_at.isoformat(),
            tags=test.tags
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tests/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: str,
    request: CreateTestRequest,
    db: Session = Depends(get_db)
):
    """Update a test"""
    try:
        from app.models.agent_test import AgentTest
        
        test = db.query(AgentTest).filter(AgentTest.id == UUID(test_id)).first()
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        
        # Update fields
        test.name = request.name
        test.description = request.description
        test.test_type = request.test_type
        test.agent_id = UUID(request.agent_id)
        test.input_data = request.input_data
        test.expected_output = request.expected_output
        test.validation_rules = request.validation_rules
        test.timeout_seconds = request.timeout_seconds
        test.max_retries = request.max_retries
        test.required_tools = request.required_tools
        test.tags = request.tags
        
        db.commit()
        db.refresh(test)
        
        return TestResponse(
            id=str(test.id),
            name=test.name,
            description=test.description,
            test_type=test.test_type,
            agent_id=str(test.agent_id),
            input_data=test.input_data,
            expected_output=test.expected_output,
            validation_rules=test.validation_rules,
            timeout_seconds=test.timeout_seconds,
            max_retries=test.max_retries,
            required_tools=test.required_tools,
            created_by=test.created_by,
            created_at=test.created_at.isoformat(),
            tags=test.tags
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/run", response_model=TestRunResponse)
async def run_test(
    test_id: str,
    request: RunTestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run an agent test"""
    try:
        gym_service = AgentGymService(db)
        
        # Run test (can be async in background)
        test_run = await gym_service.run_test(
            test_id=UUID(test_id),
            run_by=request.run_by,
            notes=request.notes
        )
        
        return TestRunResponse(
            id=str(test_run.id),
            test_id=str(test_run.test_id),
            agent_id=str(test_run.agent_id),
            agent_version=test_run.agent_version,
            status=test_run.status,
            started_at=test_run.started_at.isoformat(),
            completed_at=test_run.completed_at.isoformat() if test_run.completed_at else None,
            duration_ms=test_run.duration_ms,
            output_data=test_run.output_data,
            validation_passed=test_run.validation_passed,
            validation_details=test_run.validation_details,
            tokens_used=test_run.tokens_used,
            llm_calls=test_run.llm_calls,
            tool_calls=test_run.tool_calls,
            error_message=test_run.error_message,
            error_type=test_run.error_type
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}/runs", response_model=List[TestRunResponse])
async def get_test_runs(
    test_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get test runs for a test"""
    try:
        gym_service = AgentGymService(db)
        test_runs = gym_service.get_test_runs(
            test_id=UUID(test_id),
            status=status,
            limit=limit
        )
        
        return [
            TestRunResponse(
                id=str(tr.id),
                test_id=str(tr.test_id),
                agent_id=str(tr.agent_id),
                agent_version=tr.agent_version,
                status=tr.status,
                started_at=tr.started_at.isoformat(),
                completed_at=tr.completed_at.isoformat() if tr.completed_at else None,
                duration_ms=tr.duration_ms,
                output_data=tr.output_data,
                validation_passed=tr.validation_passed,
                validation_details=tr.validation_details,
                tokens_used=tr.tokens_used,
                llm_calls=tr.llm_calls,
                tool_calls=tr.tool_calls,
                error_message=tr.error_message,
                error_type=tr.error_type
            )
            for tr in test_runs
        ]
    except Exception as e:
        logger.error(f"Error getting test runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-runs/{test_run_id}", response_model=TestRunResponse)
async def get_test_run(
    test_run_id: str,
    db: Session = Depends(get_db)
):
    """Get a test run by ID"""
    try:
        from app.models.agent_test import AgentTestRun
        
        test_run = db.query(AgentTestRun).filter(AgentTestRun.id == UUID(test_run_id)).first()
        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")
        
        return TestRunResponse(
            id=str(test_run.id),
            test_id=str(test_run.test_id),
            agent_id=str(test_run.agent_id),
            agent_version=test_run.agent_version,
            status=test_run.status,
            started_at=test_run.started_at.isoformat(),
            completed_at=test_run.completed_at.isoformat() if test_run.completed_at else None,
            duration_ms=test_run.duration_ms,
            output_data=test_run.output_data,
            validation_passed=test_run.validation_passed,
            validation_details=test_run.validation_details,
            tokens_used=test_run.tokens_used,
            llm_calls=test_run.llm_calls,
            tool_calls=test_run.tool_calls,
            error_message=test_run.error_message,
            error_type=test_run.error_type
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmarks", response_model=BenchmarkResponse)
async def create_benchmark(
    request: CreateBenchmarkRequest,
    db: Session = Depends(get_db)
):
    """Create a new benchmark"""
    try:
        gym_service = AgentGymService(db)
        benchmark = gym_service.create_benchmark(
            name=request.name,
            benchmark_type=request.benchmark_type,
            agent_ids=[UUID(aid) for aid in request.agent_ids],
            tasks=request.tasks,
            iterations=request.iterations,
            timeout_seconds=request.timeout_seconds,
            parallel_execution=request.parallel_execution,
            metrics=request.metrics,
            description=request.description,
            tags=request.tags,
            created_by=request.created_by
        )
        
        return BenchmarkResponse(
            id=str(benchmark.id),
            name=benchmark.name,
            description=benchmark.description,
            benchmark_type=benchmark.benchmark_type,
            agent_ids=benchmark.agent_ids,
            tasks=benchmark.tasks,
            iterations=benchmark.iterations,
            timeout_seconds=benchmark.timeout_seconds,
            parallel_execution=benchmark.parallel_execution,
            metrics=benchmark.metrics,
            created_by=benchmark.created_by,
            created_at=benchmark.created_at.isoformat(),
            tags=benchmark.tags
        )
    except Exception as e:
        logger.error(f"Error creating benchmark: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmarks", response_model=List[BenchmarkResponse])
async def list_benchmarks(
    benchmark_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List benchmarks"""
    try:
        from app.models.agent_test import AgentBenchmark
        
        query = db.query(AgentBenchmark)
        
        if benchmark_type:
            query = query.filter(AgentBenchmark.benchmark_type == benchmark_type)
        
        benchmarks = query.all()
        
        return [
            BenchmarkResponse(
                id=str(b.id),
                name=b.name,
                description=b.description,
                benchmark_type=b.benchmark_type,
                agent_ids=b.agent_ids,
                tasks=b.tasks,
                iterations=b.iterations,
                timeout_seconds=b.timeout_seconds,
                parallel_execution=b.parallel_execution,
                metrics=b.metrics,
                created_by=b.created_by,
                created_at=b.created_at.isoformat(),
                tags=b.tags
            )
            for b in benchmarks
        ]
    except Exception as e:
        logger.error(f"Error listing benchmarks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmarks/{benchmark_id}/run", response_model=BenchmarkRunResponse)
async def run_benchmark(
    benchmark_id: str,
    request: RunTestRequest,
    db: Session = Depends(get_db)
):
    """Run a benchmark"""
    try:
        gym_service = AgentGymService(db)
        benchmark_run = await gym_service.run_benchmark(
            benchmark_id=UUID(benchmark_id),
            run_by=request.run_by,
            notes=request.notes
        )
        
        return BenchmarkRunResponse(
            id=str(benchmark_run.id),
            benchmark_id=str(benchmark_run.benchmark_id),
            status=benchmark_run.status,
            started_at=benchmark_run.started_at.isoformat(),
            completed_at=benchmark_run.completed_at.isoformat() if benchmark_run.completed_at else None,
            duration_ms=benchmark_run.duration_ms,
            agent_results=benchmark_run.agent_results,
            summary=benchmark_run.summary,
            error_message=benchmark_run.error_message,
            error_type=benchmark_run.error_type
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running benchmark: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmarks/{benchmark_id}/runs")
async def get_benchmark_runs(
    benchmark_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get benchmark runs"""
    try:
        from app.models.agent_test import AgentBenchmarkRun
        
        runs = db.query(AgentBenchmarkRun).filter(
            AgentBenchmarkRun.benchmark_id == UUID(benchmark_id)
        ).order_by(AgentBenchmarkRun.started_at.desc()).limit(limit).all()
        
        return [
            {
                "id": str(r.id),
                "benchmark_id": str(r.benchmark_id),
                "status": r.status,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "duration_ms": r.duration_ms,
                "summary": r.summary,
                "error_message": r.error_message
            }
            for r in runs
        ]
    except Exception as e:
        logger.error(f"Error getting benchmark runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

