"""
Benchmark Service for managing benchmark tasks and results
"""
import json
import time
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.models.benchmark_result import BenchmarkResult
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from app.core.ollama_client import OllamaClient, TaskType
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class BenchmarkService:
    """Service for managing benchmark tasks"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def load_tasks_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load benchmark tasks from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            logger.info(f"Loaded {len(tasks)} tasks from {file_path}")
            return tasks
        except Exception as e:
            logger.error(f"Error loading tasks from {file_path}: {e}")
            raise
    
    def import_task(self, task_data: Dict[str, Any]) -> BenchmarkTask:
        """Import a single task into the database"""
        # Check if task already exists
        existing = self.db.query(BenchmarkTask).filter(
            BenchmarkTask.name == task_data['name']
        ).first()
        
        if existing:
            logger.info(f"Task {task_data['name']} already exists, skipping")
            return existing
        
        # Create new task
        task = BenchmarkTask(
            task_type=BenchmarkTaskType(task_data['task_type']),
            category=task_data.get('category'),
            name=task_data['name'],
            task_description=task_data['task_description'],
            expected_output=task_data.get('expected_output'),
            evaluation_criteria=task_data.get('evaluation_criteria'),
            difficulty=task_data.get('difficulty'),
            tags=task_data.get('tags'),
            task_metadata=task_data.get('metadata')
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Imported task: {task.name}")
        return task
    
    def import_tasks_from_directory(self, directory: Path) -> Dict[str, int]:
        """Import all tasks from benchmark JSON files in a directory"""
        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0
        }
        
        if not directory.exists():
            logger.error(f"Directory {directory} does not exist")
            return stats
        
        # Find all JSON files
        json_files = list(directory.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files in {directory}")
        
        for json_file in json_files:
            try:
                tasks = self.load_tasks_from_file(json_file)
                stats['total'] += len(tasks)
                
                for task_data in tasks:
                    try:
                        self.import_task(task_data)
                        stats['imported'] += 1
                    except Exception as e:
                        logger.error(f"Error importing task {task_data.get('name', 'unknown')}: {e}")
                        stats['errors'] += 1
            except Exception as e:
                logger.error(f"Error processing file {json_file}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Import complete: {stats}")
        return stats
    
    def get_task_by_name(self, name: str) -> Optional[BenchmarkTask]:
        """Get a task by name"""
        return self.db.query(BenchmarkTask).filter(BenchmarkTask.name == name).first()
    
    def list_tasks(
        self,
        task_type: Optional[BenchmarkTaskType] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[BenchmarkTask]:
        """List benchmark tasks with optional filters"""
        query = self.db.query(BenchmarkTask)
        
        if task_type:
            query = query.filter(BenchmarkTask.task_type == task_type)
        if category:
            query = query.filter(BenchmarkTask.category == category)
        if difficulty:
            query = query.filter(BenchmarkTask.difficulty == difficulty)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_task_count_by_type(self) -> Dict[str, int]:
        """Get count of tasks by type"""
        counts = {}
        for task_type in BenchmarkTaskType:
            count = self.db.query(BenchmarkTask).filter(
                BenchmarkTask.task_type == task_type
            ).count()
            counts[task_type.value] = count
        return counts
    
    async def run_benchmark(
        self,
        task_id: UUID,
        model_id: Optional[UUID] = None,
        server_id: Optional[UUID] = None,
        model_name: Optional[str] = None,
        server_url: Optional[str] = None,
        timeout: float = 60.0
    ) -> BenchmarkResult:
        """
        Run a single benchmark task with specified model
        
        Args:
            task_id: ID of the benchmark task
            model_id: ID of the model (from database)
            server_id: ID of the server (from database)
            model_name: Model name (if model_id not provided)
            server_url: Server URL (if server_id not provided)
            timeout: Timeout in seconds
            
        Returns:
            BenchmarkResult with execution results
        """
        # Get task
        task = self.db.query(BenchmarkTask).filter(BenchmarkTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Get model and server info
        model = None
        server = None
        
        if model_id:
            model = self.db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
            if model:
                model_name = model.model_name
                if not server_id and model.server_id:
                    server_id = model.server_id
        
        if server_id:
            server = self.db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
            if server:
                server_url = server.get_api_url()
        
        if not model_name:
            raise ValueError("Model name must be provided (either via model_id or model_name)")
        
        if not server_url:
            raise ValueError("Server URL must be provided (either via server_id or server_url)")
        
        # Map task type to Ollama TaskType
        task_type_map = {
            BenchmarkTaskType.CODE_GENERATION: TaskType.CODE_GENERATION,
            BenchmarkTaskType.CODE_ANALYSIS: TaskType.CODE_ANALYSIS,
            BenchmarkTaskType.REASONING: TaskType.REASONING,
            BenchmarkTaskType.PLANNING: TaskType.PLANNING,
            BenchmarkTaskType.GENERAL_CHAT: TaskType.GENERAL_CHAT,
        }
        ollama_task_type = task_type_map.get(task.task_type, TaskType.DEFAULT)
        
        # Create result object
        result = BenchmarkResult(
            benchmark_task_id=task_id,
            model_id=model.id if model else None,
            server_id=server.id if server else None,
            passed=False
        )
        self.db.add(result)
        self.db.flush()
        
        # Execute benchmark
        start_time = time.time()
        output = None
        error_message = None
        
        try:
            client = OllamaClient()
            response = await asyncio.wait_for(
                client.generate(
                    prompt=task.task_description,
                    task_type=ollama_task_type,
                    model=model_name,
                    server_url=server_url
                ),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            output = response.response
            
            # Store result
            result.execution_time = execution_time
            result.output = output
            result.execution_metadata = {
                "model": model_name,
                "server_url": server_url,
                "task_type": task.task_type.value,
                "timeout": timeout
            }
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_message = f"Timeout after {timeout} seconds"
            result.execution_time = execution_time
            result.error_message = error_message
            result.execution_metadata = {
                "model": model_name,
                "server_url": server_url,
                "error_type": "timeout"
            }
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            result.execution_time = execution_time
            result.error_message = error_message
            result.execution_metadata = {
                "model": model_name,
                "server_url": server_url,
                "error_type": type(e).__name__
            }
        
        # Save result (score and passed will be set by evaluation)
        self.db.commit()
        self.db.refresh(result)
        
        return result
    
    async def run_suite(
        self,
        task_type: Optional[BenchmarkTaskType] = None,
        model_id: Optional[UUID] = None,
        model_name: Optional[str] = None,
        server_id: Optional[UUID] = None,
        server_url: Optional[str] = None,
        limit: Optional[int] = None,
        timeout: float = 60.0
    ) -> List[BenchmarkResult]:
        """
        Run a full benchmark suite for a model
        
        Args:
            task_type: Filter by task type (None = all types)
            model_id: ID of the model
            model_name: Model name
            server_id: ID of the server
            server_url: Server URL
            limit: Maximum number of tasks to run
            timeout: Timeout per task in seconds
            
        Returns:
            List of BenchmarkResult objects
        """
        # Get tasks
        tasks = self.list_tasks(task_type=task_type, limit=limit)
        
        if not tasks:
            logger.warning(f"No tasks found for type {task_type}")
            return []
        
        logger.info(f"Running suite: {len(tasks)} tasks for model {model_name or model_id}")
        
        results = []
        for i, task in enumerate(tasks, 1):
            logger.info(f"Running task {i}/{len(tasks)}: {task.name}")
            try:
                result = await self.run_benchmark(
                    task_id=task.id,
                    model_id=model_id,
                    server_id=server_id,
                    model_name=model_name,
                    server_url=server_url,
                    timeout=timeout
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error running task {task.name}: {e}")
                # Create failed result
                result = BenchmarkResult(
                    benchmark_task_id=task.id,
                    model_id=model_id,
                    server_id=server_id,
                    passed=False,
                    error_message=str(e),
                    execution_metadata={"error_type": type(e).__name__}
                )
                self.db.add(result)
                self.db.commit()
                results.append(result)
        
        logger.info(f"Suite complete: {len(results)} results")
        return results
    
    def compare_models(
        self,
        model_ids: List[UUID],
        task_type: Optional[BenchmarkTaskType] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compare results of multiple models
        
        Args:
            model_ids: List of model IDs to compare
            task_type: Filter by task type
            limit: Limit number of tasks per model
            
        Returns:
            Dictionary with comparison statistics
        """
        comparison = {
            "models": [],
            "tasks": [],
            "summary": {}
        }
        
        # Get tasks
        tasks = self.list_tasks(task_type=task_type, limit=limit)
        
        for model_id in model_ids:
            model = self.db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
            if not model:
                continue
            
            # Get results for this model
            results = self.db.query(BenchmarkResult).filter(
                and_(
                    BenchmarkResult.model_id == model_id,
                    BenchmarkResult.benchmark_task_id.in_([t.id for t in tasks])
                )
            ).all()
            
            model_stats = {
                "model_id": str(model_id),
                "model_name": model.model_name,
                "total_tasks": len(tasks),
                "completed": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed or not r.passed),
                "avg_score": sum(r.score for r in results if r.score) / len(results) if results else 0.0,
                "avg_execution_time": sum(r.execution_time for r in results if r.execution_time) / len(results) if results else 0.0,
                "results": [r.to_dict() for r in results]
            }
            
            comparison["models"].append(model_stats)
        
        # Summary
        comparison["summary"] = {
            "total_models": len(comparison["models"]),
            "total_tasks": len(tasks),
            "best_model": max(comparison["models"], key=lambda m: m["avg_score"])["model_name"] if comparison["models"] else None,
            "fastest_model": min(comparison["models"], key=lambda m: m["avg_execution_time"])["model_name"] if comparison["models"] else None
        }
        
        return comparison

