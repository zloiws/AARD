"""
Agent Gym Service - Automated testing and benchmarking for agents
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import time
import traceback as tb
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.agent_test import (
    AgentTest, AgentTestRun, AgentBenchmark, AgentBenchmarkRun,
    TestStatus, TestType
)
from app.models.agent import Agent
from app.services.agent_service import AgentService
from app.agents.simple_agent import SimpleAgent
from app.core.ollama_client import OllamaClient

logger = LoggingConfig.get_logger(__name__)


class AgentGymService:
    """Service for running agent tests and benchmarks"""
    
    def __init__(self, db: Session = None):
        """
        Initialize Agent Gym Service
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or SessionLocal()
        self.agent_service = AgentService(self.db)
    
    def create_test(
        self,
        name: str,
        agent_id: UUID,
        test_type: str,
        input_data: Dict[str, Any],
        expected_output: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 60,
        max_retries: int = 0,
        required_tools: Optional[List[str]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> AgentTest:
        """
        Create a new agent test
        
        Args:
            name: Test name
            agent_id: Agent ID to test
            test_type: Test type (functional, performance, etc.)
            input_data: Test input data
            expected_output: Expected output (optional)
            validation_rules: Validation rules (optional)
            timeout_seconds: Timeout in seconds
            max_retries: Maximum retries
            required_tools: List of required tool names
            description: Test description
            tags: Tags for categorization
            created_by: Creator username
            
        Returns:
            Created AgentTest
        """
        test = AgentTest(
            name=name,
            description=description,
            test_type=test_type,
            agent_id=agent_id,
            input_data=input_data,
            expected_output=expected_output,
            validation_rules=validation_rules,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            required_tools=required_tools or [],
            created_by=created_by,
            tags=tags or []
        )
        
        self.db.add(test)
        self.db.commit()
        self.db.refresh(test)
        
        logger.info(
            f"Created test: {name}",
            extra={"test_id": str(test.id), "agent_id": str(agent_id), "test_type": test_type}
        )
        
        return test
    
    async def run_test(
        self,
        test_id: UUID,
        run_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> AgentTestRun:
        """
        Run an agent test
        
        Args:
            test_id: Test ID to run
            run_by: User or system that runs the test
            notes: Additional notes
            
        Returns:
            Test run result
        """
        test = self.db.query(AgentTest).filter(AgentTest.id == test_id).first()
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        agent = self.db.query(Agent).filter(Agent.id == test.agent_id).first()
        if not agent:
            raise ValueError(f"Agent {test.agent_id} not found")
        
        # Create test run record
        test_run = AgentTestRun(
            test_id=test_id,
            agent_id=test.agent_id,
            agent_version=agent.version,
            status=TestStatus.RUNNING.value,
            input_data=test.input_data,
            expected_output=test.expected_output,
            run_by=run_by,
            notes=notes
        )
        
        self.db.add(test_run)
        self.db.commit()
        self.db.refresh(test_run)
        
        start_time = time.time()
        tokens_used = 0
        llm_calls = 0
        tool_calls = 0
        
        try:
            # Initialize agent
            ollama_client = OllamaClient()
            agent_instance = SimpleAgent(
                agent_id=test.agent_id,
                agent_service=self.agent_service,
                ollama_client=ollama_client,
                db_session=self.db
            )
            
            # Extract task from input_data
            task_description = test.input_data.get("task", test.input_data.get("description", ""))
            context = test.input_data.get("context", {})
            use_tools = test.input_data.get("use_tools", False)
            
            # Run test with timeout
            try:
                result = await asyncio.wait_for(
                    agent_instance.execute(
                        task_description=task_description,
                        context=context,
                        use_tools=use_tools
                    ),
                    timeout=test.timeout_seconds
                )
            except asyncio.TimeoutError:
                test_run.status = TestStatus.TIMEOUT.value
                test_run.error_message = f"Test timed out after {test.timeout_seconds} seconds"
                test_run.error_type = "TimeoutError"
            except Exception as e:
                test_run.status = TestStatus.ERROR.value
                test_run.error_message = str(e)
                test_run.error_type = type(e).__name__
                test_run.error_traceback = tb.format_exc()
                raise
            
            # Record output
            test_run.output_data = result
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            test_run.duration_ms = duration_ms
            
            # Validate result
            validation_result = self._validate_result(test, result)
            test_run.validation_passed = validation_result["passed"]
            test_run.validation_details = validation_result["details"]
            
            # Determine final status
            if test_run.status == TestStatus.RUNNING.value:
                if validation_result["passed"] == "true":
                    test_run.status = TestStatus.PASSED.value
                elif validation_result["passed"] == "partial":
                    test_run.status = TestStatus.PASSED.value  # Partial pass is still a pass
                else:
                    test_run.status = TestStatus.FAILED.value
            
            # Extract metrics from result metadata
            if result.get("metadata"):
                metadata = result["metadata"]
                tokens_used = metadata.get("tokens_used", 0)
                llm_calls = metadata.get("llm_calls", 0)
                tool_calls = metadata.get("tool_calls", 0)
            
            test_run.tokens_used = tokens_used
            test_run.llm_calls = llm_calls
            test_run.tool_calls = tool_calls
            
        except Exception as e:
            test_run.status = TestStatus.ERROR.value
            test_run.error_message = str(e)
            test_run.error_type = type(e).__name__
            test_run.error_traceback = tb.format_exc()
            duration_ms = int((time.time() - start_time) * 1000)
            test_run.duration_ms = duration_ms
        
        finally:
            test_run.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(test_run)
            
            logger.info(
                f"Test run completed: {test.name}",
                extra={
                    "test_id": str(test_id),
                    "test_run_id": str(test_run.id),
                    "status": test_run.status,
                    "duration_ms": test_run.duration_ms
                }
            )
        
        return test_run
    
    def _validate_result(self, test: AgentTest, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate test result
        
        Args:
            test: Test definition
            result: Actual result from agent
            
        Returns:
            Validation result with 'passed' and 'details'
        """
        validation_result = {
            "passed": "false",
            "details": {}
        }
        
        # If no validation rules, check if result has success status
        if not test.validation_rules and not test.expected_output:
            if result.get("status") == "success":
                validation_result["passed"] = "true"
            return validation_result
        
        # Check expected output
        if test.expected_output:
            expected = test.expected_output
            actual = result.get("result") or result
            
            # Simple equality check
            if expected == actual:
                validation_result["passed"] = "true"
                validation_result["details"]["expected_output_match"] = True
            else:
                validation_result["details"]["expected_output_match"] = False
                validation_result["details"]["expected"] = expected
                validation_result["details"]["actual"] = actual
        
        # Apply validation rules
        if test.validation_rules:
            rules = test.validation_rules
            
            # Regex validation
            if "regex" in rules:
                import re
                pattern = rules["regex"]
                text = str(result.get("result", ""))
                if re.search(pattern, text):
                    validation_result["details"]["regex_match"] = True
                    if validation_result["passed"] == "false":
                        validation_result["passed"] = "partial"
                else:
                    validation_result["details"]["regex_match"] = False
            
            # Schema validation (basic)
            if "schema" in rules:
                schema = rules["schema"]
                # Basic schema check - can be extended
                validation_result["details"]["schema_check"] = "basic"
        
        return validation_result
    
    def get_test_runs(
        self,
        test_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentTestRun]:
        """
        Get test runs with filters
        
        Args:
            test_id: Filter by test ID
            agent_id: Filter by agent ID
            status: Filter by status
            limit: Maximum number of results
            
        Returns:
            List of test runs
        """
        query = self.db.query(AgentTestRun)
        
        if test_id:
            query = query.filter(AgentTestRun.test_id == test_id)
        if agent_id:
            query = query.filter(AgentTestRun.agent_id == agent_id)
        if status:
            query = query.filter(AgentTestRun.status == status)
        
        return query.order_by(AgentTestRun.started_at.desc()).limit(limit).all()
    
    def create_benchmark(
        self,
        name: str,
        benchmark_type: str,
        agent_ids: List[UUID],
        tasks: List[Dict[str, Any]],
        iterations: int = 1,
        timeout_seconds: int = 300,
        parallel_execution: bool = False,
        metrics: Optional[List[str]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> AgentBenchmark:
        """
        Create a new benchmark
        
        Args:
            name: Benchmark name
            benchmark_type: Benchmark type
            agent_ids: List of agent IDs to compare
            tasks: List of tasks to execute
            iterations: Number of iterations per agent
            timeout_seconds: Timeout per task
            parallel_execution: Whether to run in parallel
            metrics: List of metrics to collect
            description: Benchmark description
            tags: Tags for categorization
            created_by: Creator username
            
        Returns:
            Created AgentBenchmark
        """
        benchmark = AgentBenchmark(
            name=name,
            description=description,
            benchmark_type=benchmark_type,
            agent_ids=[str(aid) for aid in agent_ids],
            tasks=tasks,
            iterations=iterations,
            timeout_seconds=timeout_seconds,
            parallel_execution="true" if parallel_execution else "false",
            metrics=metrics or ["duration_ms", "tokens_used", "success_rate"],
            created_by=created_by,
            tags=tags or []
        )
        
        self.db.add(benchmark)
        self.db.commit()
        self.db.refresh(benchmark)
        
        logger.info(
            f"Created benchmark: {name}",
            extra={"benchmark_id": str(benchmark.id), "agent_count": len(agent_ids)}
        )
        
        return benchmark
    
    async def run_benchmark(
        self,
        benchmark_id: UUID,
        run_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> AgentBenchmarkRun:
        """
        Run a benchmark
        
        Args:
            benchmark_id: Benchmark ID to run
            run_by: User or system that runs the benchmark
            notes: Additional notes
            
        Returns:
            Benchmark run result
        """
        benchmark = self.db.query(AgentBenchmark).filter(AgentBenchmark.id == benchmark_id).first()
        if not benchmark:
            raise ValueError(f"Benchmark {benchmark_id} not found")
        
        # Create benchmark run record
        benchmark_run = AgentBenchmarkRun(
            benchmark_id=benchmark_id,
            status=TestStatus.RUNNING.value,
            agent_results={},
            run_by=run_by,
            notes=notes
        )
        
        self.db.add(benchmark_run)
        self.db.commit()
        self.db.refresh(benchmark_run)
        
        start_time = time.time()
        agent_results = {}
        
        try:
            # Convert agent_ids from strings to UUIDs
            agent_uuids = [UUID(aid) for aid in benchmark.agent_ids]
            
            # Run tasks for each agent
            for agent_id in agent_uuids:
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    agent_results[str(agent_id)] = {
                        "status": "error",
                        "error": f"Agent {agent_id} not found"
                    }
                    continue
                
                agent_result = {
                    "agent_id": str(agent_id),
                    "agent_name": agent.name,
                    "agent_version": agent.version,
                    "tasks": [],
                    "metrics": {}
                }
                
                # Run each task
                for task in benchmark.tasks:
                    task_result = await self._run_benchmark_task(
                        agent_id, task, benchmark.timeout_seconds
                    )
                    agent_result["tasks"].append(task_result)
                
                # Calculate metrics
                agent_result["metrics"] = self._calculate_agent_metrics(agent_result["tasks"])
                agent_results[str(agent_id)] = agent_result
            
            # Calculate summary
            summary = self._calculate_benchmark_summary(agent_results)
            
            benchmark_run.agent_results = agent_results
            benchmark_run.summary = summary
            benchmark_run.status = TestStatus.PASSED.value
            
        except Exception as e:
            benchmark_run.status = TestStatus.ERROR.value
            benchmark_run.error_message = str(e)
            benchmark_run.error_type = type(e).__name__
            logger.error(f"Benchmark run failed: {e}", exc_info=True)
        
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            benchmark_run.duration_ms = duration_ms
            benchmark_run.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(benchmark_run)
        
        return benchmark_run
    
    async def _run_benchmark_task(
        self,
        agent_id: UUID,
        task: Dict[str, Any],
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Run a single benchmark task for an agent"""
        task_start = time.time()
        
        try:
            ollama_client = OllamaClient()
            agent_instance = SimpleAgent(
                agent_id=agent_id,
                agent_service=self.agent_service,
                ollama_client=ollama_client,
                db_session=self.db
            )
            
            task_description = task.get("task", task.get("description", ""))
            context = task.get("context", {})
            
            result = await asyncio.wait_for(
                agent_instance.execute(
                    task_description=task_description,
                    context=context,
                    use_tools=task.get("use_tools", False)
                ),
                timeout=timeout_seconds
            )
            
            duration_ms = int((time.time() - task_start) * 1000)
            
            return {
                "status": result.get("status", "unknown"),
                "duration_ms": duration_ms,
                "result": result.get("result"),
                "metadata": result.get("metadata", {})
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "duration_ms": int((time.time() - task_start) * 1000),
                "error": "Task timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "duration_ms": int((time.time() - task_start) * 1000),
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _calculate_agent_metrics(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics for an agent from task results"""
        if not tasks:
            return {}
        
        successful = sum(1 for t in tasks if t.get("status") == "success")
        total = len(tasks)
        
        durations = [t.get("duration_ms", 0) for t in tasks if t.get("duration_ms")]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        total_tokens = sum(
            t.get("metadata", {}).get("tokens_used", 0) for t in tasks
        )
        
        return {
            "success_rate": successful / total if total > 0 else 0,
            "total_tasks": total,
            "successful_tasks": successful,
            "failed_tasks": total - successful,
            "avg_duration_ms": int(avg_duration),
            "total_tokens_used": total_tokens
        }
    
    def _calculate_benchmark_summary(self, agent_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for benchmark"""
        if not agent_results:
            return {}
        
        summaries = []
        for agent_id, result in agent_results.items():
            metrics = result.get("metrics", {})
            summaries.append({
                "agent_id": agent_id,
                "agent_name": result.get("agent_name", "Unknown"),
                "success_rate": metrics.get("success_rate", 0),
                "avg_duration_ms": metrics.get("avg_duration_ms", 0),
                "total_tokens_used": metrics.get("total_tokens_used", 0)
            })
        
        # Find best agent by success rate
        best_agent = max(summaries, key=lambda x: x["success_rate"]) if summaries else None
        
        return {
            "total_agents": len(agent_results),
            "best_agent": best_agent,
            "agent_summaries": summaries
        }

