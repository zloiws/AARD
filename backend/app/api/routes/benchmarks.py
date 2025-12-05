"""
API routes for benchmark management
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.services.benchmark_service import BenchmarkService
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.models.benchmark_result import BenchmarkResult
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])
logger = LoggingConfig.get_logger(__name__)


class BenchmarkTaskResponse(BaseModel):
    """Response model for benchmark task"""
    id: str
    task_type: str
    category: Optional[str]
    name: str
    task_description: str
    expected_output: Optional[str]
    evaluation_criteria: Optional[dict]
    difficulty: Optional[str]
    tags: Optional[List[str]]
    created_at: str
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class BenchmarkResultResponse(BaseModel):
    """Response model for benchmark result"""
    id: str
    benchmark_task_id: str
    model_id: Optional[str]
    server_id: Optional[str]
    execution_time: Optional[float]
    output: Optional[str]
    score: Optional[float]
    metrics: Optional[dict]
    passed: bool
    error_message: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class RunBenchmarkRequest(BaseModel):
    """Request model for running benchmark"""
    task_id: Optional[str] = None
    task_type: Optional[str] = None
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    server_id: Optional[str] = None
    server_url: Optional[str] = None
    limit: Optional[int] = None
    timeout: float = Field(default=60.0, ge=1.0, le=300.0)
    evaluate: bool = Field(default=True, description="Automatically evaluate results")


class ComparisonRequest(BaseModel):
    """Request model for comparing models"""
    model_ids: List[str] = Field(..., min_length=1, description="List of model IDs to compare")
    task_type: Optional[str] = None
    limit: Optional[int] = None


@router.get("/tasks/", response_model=List[BenchmarkTaskResponse])
async def list_benchmark_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of results"),
    db: Session = Depends(get_db)
):
    """List benchmark tasks with optional filters"""
    try:
        service = BenchmarkService(db)
        
        # Convert task_type string to enum
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = BenchmarkTaskType(task_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid task_type: {task_type}")
        
        tasks = service.list_tasks(
            task_type=task_type_enum,
            category=category,
            difficulty=difficulty,
            limit=limit
        )
        
        return [BenchmarkTaskResponse(
            id=str(task.id),
            task_type=task.task_type.value,
            category=task.category,
            name=task.name,
            task_description=task.task_description,
            expected_output=task.expected_output,
            evaluation_criteria=task.evaluation_criteria,
            difficulty=task.difficulty,
            tags=task.tags,
            created_at=task.created_at.isoformat() if task.created_at else None
        ) for task in tasks]
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=BenchmarkTaskResponse)
async def get_benchmark_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific benchmark task"""
    try:
        task = db.query(BenchmarkTask).filter(BenchmarkTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return BenchmarkTaskResponse(
            id=str(task.id),
            task_type=task.task_type.value,
            category=task.category,
            name=task.name,
            task_description=task.task_description,
            expected_output=task.expected_output,
            evaluation_criteria=task.evaluation_criteria,
            difficulty=task.difficulty,
            tags=task.tags,
            created_at=task.created_at.isoformat() if task.created_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/", response_model=List[BenchmarkResultResponse])
async def run_benchmark(
    request: RunBenchmarkRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Run benchmark test(s) for a model"""
    try:
        service = BenchmarkService(db)
        results = []
        
        if request.task_id:
            # Run single task
            result = await service.run_benchmark(
                task_id=UUID(request.task_id),
                model_id=UUID(request.model_id) if request.model_id else None,
                model_name=request.model_name,
                server_id=UUID(request.server_id) if request.server_id else None,
                server_url=request.server_url,
                timeout=request.timeout
            )
            
            # Evaluate if requested
            if request.evaluate:
                result = await service.evaluate_result(result.id, use_llm=False)
            
            results = [result]
        else:
            # Run suite
            task_type_enum = None
            if request.task_type:
                try:
                    task_type_enum = BenchmarkTaskType(request.task_type)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid task_type: {request.task_type}")
            
            results = await service.run_suite(
                task_type=task_type_enum,
                model_id=UUID(request.model_id) if request.model_id else None,
                model_name=request.model_name,
                server_id=UUID(request.server_id) if request.server_id else None,
                server_url=request.server_url,
                limit=request.limit,
                timeout=request.timeout
            )
            
            # Evaluate all results if requested
            if request.evaluate:
                for result in results:
                    try:
                        await service.evaluate_result(result.id, use_llm=False)
                    except Exception as e:
                        logger.warning(f"Error evaluating result {result.id}: {e}")
        
        return [BenchmarkResultResponse(
            id=str(r.id),
            benchmark_task_id=str(r.benchmark_task_id),
            model_id=str(r.model_id) if r.model_id else None,
            server_id=str(r.server_id) if r.server_id else None,
            execution_time=r.execution_time,
            output=r.output,
            score=r.score,
            metrics=r.metrics,
            passed=r.passed,
            error_message=r.error_message,
            created_at=r.created_at.isoformat() if r.created_at else None
        ) for r in results]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error running benchmark: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/", response_model=List[BenchmarkResultResponse])
async def list_benchmark_results(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of results"),
    db: Session = Depends(get_db)
):
    """List benchmark results with optional filters"""
    try:
        query = db.query(BenchmarkResult)
        
        if task_id:
            query = query.filter(BenchmarkResult.benchmark_task_id == UUID(task_id))
        if model_id:
            query = query.filter(BenchmarkResult.model_id == UUID(model_id))
        
        query = query.order_by(BenchmarkResult.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        results = query.all()
        
        return [BenchmarkResultResponse(
            id=str(r.id),
            benchmark_task_id=str(r.benchmark_task_id),
            model_id=str(r.model_id) if r.model_id else None,
            server_id=str(r.server_id) if r.server_id else None,
            execution_time=r.execution_time,
            output=r.output,
            score=r.score,
            metrics=r.metrics,
            passed=r.passed,
            error_message=r.error_message,
            created_at=r.created_at.isoformat() if r.created_at else None
        ) for r in results]
        
    except Exception as e:
        logger.error(f"Error listing results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{result_id}", response_model=BenchmarkResultResponse)
async def get_benchmark_result(
    result_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific benchmark result"""
    try:
        result = db.query(BenchmarkResult).filter(BenchmarkResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
        
        # Include task information
        task = result.task
        task_info = None
        if task:
            task_info = {
                "id": str(task.id),
                "name": task.name,
                "task_type": task.task_type.value,
                "task_description": task.task_description
            }
        
        response_data = {
            "id": str(result.id),
            "benchmark_task_id": str(result.benchmark_task_id),
            "model_id": str(result.model_id) if result.model_id else None,
            "server_id": str(result.server_id) if result.server_id else None,
            "execution_time": result.execution_time,
            "output": result.output,
            "score": result.score,
            "metrics": result.metrics,
            "passed": result.passed,
            "error_message": result.error_message,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "task": task_info
        }
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/{result_id}", response_model=BenchmarkResultResponse)
async def evaluate_benchmark_result(
    result_id: str,
    use_llm: bool = Query(default=False, description="Use LLM for evaluation"),
    db: Session = Depends(get_db)
):
    """Evaluate a benchmark result"""
    try:
        service = BenchmarkService(db)
        result = await service.evaluate_result(UUID(result_id), use_llm=use_llm)
        
        return BenchmarkResultResponse(
            id=str(result.id),
            benchmark_task_id=str(result.benchmark_task_id),
            model_id=str(result.model_id) if result.model_id else None,
            server_id=str(result.server_id) if result.server_id else None,
            execution_time=result.execution_time,
            output=result.output,
            score=result.score,
            metrics=result.metrics,
            passed=result.passed,
            error_message=result.error_message,
            created_at=result.created_at.isoformat() if result.created_at else None
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error evaluating result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comparison/", response_model=dict)
@router.get("/comparison/", response_model=dict)
async def compare_models(
    request: Optional[ComparisonRequest] = Body(None),
    model_ids: Optional[str] = Query(None, description="Comma-separated model IDs"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: Optional[int] = Query(None, description="Limit number of tasks"),
    db: Session = Depends(get_db)
):
    """Compare results of multiple models"""
    try:
        service = BenchmarkService(db)
        
        # Get model IDs from request body or query params
        if request and request.model_ids:
            model_id_list = request.model_ids
        elif model_ids:
            model_id_list = model_ids.split(',')
        else:
            raise HTTPException(status_code=400, detail="model_ids is required")
        
        # Convert model IDs
        model_ids_uuid = [UUID(mid.strip()) for mid in model_id_list]
        
        # Convert task_type
        task_type_enum = None
        task_type_value = request.task_type if request else task_type
        if task_type_value:
            try:
                task_type_enum = BenchmarkTaskType(task_type_value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid task_type: {task_type_value}")
        
        limit_value = request.limit if request else limit
        
        comparison = service.compare_models(
            model_ids=model_ids_uuid,
            task_type=task_type_enum,
            limit=limit_value
        )
        
        # Add task information to results
        for model_data in comparison.get("models", []):
            for result in model_data.get("results", []):
                if result.get("benchmark_task_id"):
                    task = db.query(BenchmarkTask).filter(
                        BenchmarkTask.id == UUID(result["benchmark_task_id"])
                    ).first()
                    if task:
                        result["task"] = {
                            "id": str(task.id),
                            "name": task.name,
                            "task_type": task.task_type.value,
                            "task_description": task.task_description
                        }
        
        return comparison
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/", response_model=dict)
async def get_benchmark_stats(
    db: Session = Depends(get_db)
):
    """Get benchmark statistics"""
    try:
        service = BenchmarkService(db)
        
        # Task counts by type
        task_counts = service.get_task_count_by_type()
        
        # Result statistics
        total_results = db.query(BenchmarkResult).count()
        passed_results = db.query(BenchmarkResult).filter(BenchmarkResult.passed == True).count()
        failed_results = db.query(BenchmarkResult).filter(BenchmarkResult.passed == False).count()
        
        # Average scores
        avg_score_query = db.query(BenchmarkResult.score).filter(BenchmarkResult.score.isnot(None)).all()
        avg_score = sum(s[0] for s in avg_score_query) / len(avg_score_query) if avg_score_query else None
        
        return {
            "tasks": {
                "total": sum(task_counts.values()),
                "by_type": task_counts
            },
            "results": {
                "total": total_results,
                "passed": passed_results,
                "failed": failed_results,
                "pass_rate": passed_results / total_results if total_results > 0 else 0.0,
                "average_score": avg_score
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

