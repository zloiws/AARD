"""
Benchmark Service for managing benchmark tasks and results
"""
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
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

