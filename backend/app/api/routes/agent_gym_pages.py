"""
Web pages for Agent Gym
"""
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.core.templates import templates
from app.models.agent_test import AgentTest, AgentTestRun
from app.services.agent_gym_service import AgentGymService
from app.services.agent_service import AgentService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

router = APIRouter()


@router.get("/agent-gym", response_class=HTMLResponse)
async def agent_gym_list(
    request: Request,
    test_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all tests"""
    try:
        gym_service = AgentGymService(db)
        agent_service = AgentService(db)
        
        # Build query
        query = db.query(AgentTest)
        
        if test_type:
            query = query.filter(AgentTest.test_type == test_type)
        if agent_id:
            try:
                query = query.filter(AgentTest.agent_id == UUID(agent_id))
            except ValueError:
                pass
        
        # Get tests with relationships
        tests = query.order_by(AgentTest.created_at.desc()).all()
        
        # Get agents for filter dropdown
        agents = agent_service.list_agents(status="active")
        
        # Get test runs for each test
        test_stats = {}
        for test in tests:
            # Get last run
            last_run = db.query(AgentTestRun).filter(
                AgentTestRun.test_id == test.id
            ).order_by(AgentTestRun.started_at.desc()).first()
            
            # Get total runs count
            total_runs = db.query(func.count(AgentTestRun.id)).filter(
                AgentTestRun.test_id == test.id
            ).scalar() or 0
            
            test_stats[str(test.id)] = {
                "last_run": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
                "last_status": last_run.status if last_run else None,
                "total_runs": total_runs
            }
        
        return templates.TemplateResponse(
            "agent_gym/list.html",
            {
                "request": request,
                "tests": tests,
                "agents": agents,
                "test_stats": test_stats,
                "filters": {
                    "test_type": test_type,
                    "status": status,
                    "agent_id": agent_id
                }
            }
        )
    except Exception as e:
        logger.error(f"Error loading agent gym list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-gym/tests/create", response_class=HTMLResponse)
async def agent_gym_create_test(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create test page"""
    try:
        agent_service = AgentService(db)
        agents = agent_service.list_agents(status="active")
        
        return templates.TemplateResponse(
            "agent_gym/create.html",
            {
                "request": request,
                "agents": agents
            }
        )
    except Exception as e:
        logger.error(f"Error loading create test page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-gym/tests/{test_id}", response_class=HTMLResponse)
async def agent_gym_test_detail(
    request: Request,
    test_id: str,
    db: Session = Depends(get_db)
):
    """Test detail page"""
    try:
        gym_service = AgentGymService(db)
        test = db.query(AgentTest).filter(AgentTest.id == UUID(test_id)).first()
        
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        
        # Get test runs
        runs = gym_service.get_test_runs(test_id=UUID(test_id), limit=50)
        
        # Calculate statistics
        all_runs = gym_service.get_test_runs(test_id=UUID(test_id), limit=1000)
        stats = {
            "total_runs": len(all_runs),
            "passed": sum(1 for r in all_runs if r.status == "passed"),
            "failed": sum(1 for r in all_runs if r.status == "failed"),
            "error": sum(1 for r in all_runs if r.status == "error"),
            "avg_duration_ms": int(sum(r.duration_ms or 0 for r in all_runs) / len(all_runs)) if all_runs else 0,
            "success_rate": (sum(1 for r in all_runs if r.status == "passed") / len(all_runs) * 100) if all_runs else 0
        }
        
        return templates.TemplateResponse(
            "agent_gym/test_detail.html",
            {
                "request": request,
                "test": test,
                "runs": runs,
                "stats": stats
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading test detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-gym/tests/{test_id}/edit", response_class=HTMLResponse)
async def agent_gym_edit_test(
    request: Request,
    test_id: str,
    db: Session = Depends(get_db)
):
    """Edit test page"""
    try:
        agent_service = AgentService(db)
        
        test = db.query(AgentTest).filter(AgentTest.id == UUID(test_id)).first()
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        
        agents = agent_service.list_agents(status="active")
        
        return templates.TemplateResponse(
            "agent_gym/edit.html",
            {
                "request": request,
                "test": test,
                "agents": agents
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading edit test page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-gym/benchmarks", response_class=HTMLResponse)
async def agent_gym_benchmarks_list(
    request: Request,
    benchmark_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all benchmarks"""
    try:
        from app.models.agent_test import AgentBenchmark, AgentBenchmarkRun
        
        query = db.query(AgentBenchmark)
        
        if benchmark_type:
            query = query.filter(AgentBenchmark.benchmark_type == benchmark_type)
        
        benchmarks = query.order_by(AgentBenchmark.created_at.desc()).all()
        
        # Get benchmark runs for each benchmark
        benchmark_stats = {}
        for benchmark in benchmarks:
            # Get last run
            last_run = db.query(AgentBenchmarkRun).filter(
                AgentBenchmarkRun.benchmark_id == benchmark.id
            ).order_by(AgentBenchmarkRun.started_at.desc()).first()
            
            # Get total runs count
            total_runs = db.query(func.count(AgentBenchmarkRun.id)).filter(
                AgentBenchmarkRun.benchmark_id == benchmark.id
            ).scalar() or 0
            
            benchmark_stats[str(benchmark.id)] = {
                "last_run": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
                "last_status": last_run.status if last_run else None,
                "total_runs": total_runs
            }
        
        return templates.TemplateResponse(
            "agent_gym/benchmarks_list.html",
            {
                "request": request,
                "benchmarks": benchmarks,
                "benchmark_stats": benchmark_stats,
                "filters": {
                    "benchmark_type": benchmark_type
                }
            }
        )
    except Exception as e:
        logger.error(f"Error loading benchmarks list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-gym/benchmarks/create", response_class=HTMLResponse)
async def agent_gym_create_benchmark(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create benchmark page"""
    try:
        agent_service = AgentService(db)
        agents = agent_service.list_agents(status="active")
        
        return templates.TemplateResponse(
            "agent_gym/benchmark_create.html",
            {
                "request": request,
                "agents": agents
            }
        )
    except Exception as e:
        logger.error(f"Error loading create benchmark page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-gym/benchmarks/{benchmark_id}", response_class=HTMLResponse)
async def agent_gym_benchmark_detail(
    request: Request,
    benchmark_id: str,
    db: Session = Depends(get_db)
):
    """Benchmark detail page"""
    try:
        from app.models.agent_test import AgentBenchmark, AgentBenchmarkRun
        
        benchmark = db.query(AgentBenchmark).filter(AgentBenchmark.id == UUID(benchmark_id)).first()
        
        if not benchmark:
            raise HTTPException(status_code=404, detail="Benchmark not found")
        
        # Get benchmark runs
        runs = db.query(AgentBenchmarkRun).filter(
            AgentBenchmarkRun.benchmark_id == UUID(benchmark_id)
        ).order_by(AgentBenchmarkRun.started_at.desc()).limit(50).all()
        
        # Calculate statistics
        all_runs = db.query(AgentBenchmarkRun).filter(
            AgentBenchmarkRun.benchmark_id == UUID(benchmark_id)
        ).all()
        stats = {
            "total_runs": len(all_runs),
            "passed": sum(1 for r in all_runs if r.status == "passed"),
            "failed": sum(1 for r in all_runs if r.status == "failed"),
            "error": sum(1 for r in all_runs if r.status == "error"),
            "avg_duration_ms": int(sum(r.duration_ms or 0 for r in all_runs) / len(all_runs)) if all_runs else 0
        }
        
        return templates.TemplateResponse(
            "agent_gym/benchmark_results.html",
            {
                "request": request,
                "benchmark": benchmark,
                "runs": runs,
                "stats": stats
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading benchmark detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

