"""
Prometheus metrics configuration
"""
import os

from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               Info, generate_latest)
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.registry import REGISTRY

# Check if we're in multiprocess mode
if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
    REGISTRY = MultiProcessCollector(REGISTRY)

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_errors_total = Counter(
    'http_errors_total',
    'Total number of HTTP errors',
    ['method', 'endpoint', 'status_code', 'error_type']
)

# ============================================================================
# LLM Request Metrics
# ============================================================================

llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['model', 'server_url', 'task_type', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model', 'server_url', 'task_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total number of tokens processed',
    ['model', 'type']  # meaning: 'input' or 'output'
)

llm_errors_total = Counter(
    'llm_errors_total',
    'Total number of LLM errors',
    ['model', 'server_url', 'error_type']
)

llm_model_loaded = Gauge(
    'llm_model_loaded',
    'Whether a model is currently loaded',
    ['model', 'server_url']
)

# ============================================================================
# Plan Execution Metrics
# ============================================================================

plan_executions_total = Counter(
    'plan_executions_total',
    'Total number of plan executions',
    ['status']  # status: 'success', 'failed', 'cancelled'
)

plan_execution_duration_seconds = Histogram(
    'plan_execution_duration_seconds',
    'Plan execution duration in seconds',
    ['status'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0)
)

plan_steps_total = Counter(
    'plan_steps_total',
    'Total number of plan steps executed',
    ['step_type', 'status']  # step_type: 'action', 'decision', 'validation'
)

plan_step_duration_seconds = Histogram(
    'plan_step_duration_seconds',
    'Plan step execution duration in seconds',
    ['step_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# ============================================================================
# Task Queue Metrics
# ============================================================================

queue_tasks_total = Counter(
    'queue_tasks_total',
    'Total number of tasks added to queues',
    ['queue_name', 'priority']
)

queue_tasks_processed_total = Counter(
    'queue_tasks_processed_total',
    'Total number of tasks processed',
    ['queue_name', 'status']  # status: 'success', 'failed', 'retried'
)

queue_task_duration_seconds = Histogram(
    'queue_task_duration_seconds',
    'Task processing duration in seconds',
    ['queue_name'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

queue_size = Gauge(
    'queue_size',
    'Current number of tasks in queue',
    ['queue_name', 'status']  # status: 'pending', 'processing', 'failed'
)

queue_retries_total = Counter(
    'queue_retries_total',
    'Total number of task retries',
    ['queue_name']
)

# ============================================================================
# Database Metrics
# ============================================================================

db_queries_total = Counter(
    'db_queries_total',
    'Total number of database queries',
    ['operation', 'table']  # operation: 'select', 'insert', 'update', 'delete'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

db_errors_total = Counter(
    'db_errors_total',
    'Total number of database errors',
    ['operation', 'error_type']
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    ['state']  # state: 'active', 'idle', 'overflow'
)

db_connection_pool_overflow = Gauge(
    'db_connection_pool_overflow',
    'Database connection pool overflow count',
    []
)

# ============================================================================
# Approval Request Metrics
# ============================================================================

approval_requests_total = Counter(
    'approval_requests_total',
    'Total number of approval requests',
    ['request_type', 'status']  # status: 'pending', 'approved', 'rejected'
)

approval_request_duration_seconds = Histogram(
    'approval_request_duration_seconds',
    'Time from approval request to decision in seconds',
    ['request_type', 'status'],
    buckets=(60.0, 300.0, 600.0, 1800.0, 3600.0, 7200.0, 86400.0)
)

# ============================================================================
# Artifact Metrics
# ============================================================================

artifacts_total = Counter(
    'artifacts_total',
    'Total number of artifacts created',
    ['artifact_type', 'status']  # status: 'draft', 'approved', 'active'
)

artifact_generation_duration_seconds = Histogram(
    'artifact_generation_duration_seconds',
    'Artifact generation duration in seconds',
    ['artifact_type'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0)
)

# ============================================================================
# System Info
# ============================================================================

app_info = Info(
    'app_info',
    'Application information'
)

# Initialize app info
from app.core.config import get_settings

try:
    settings = get_settings()
    app_info.info({
        'app_name': settings.app_name,
        'app_env': settings.app_env,
        'version': '0.1.0'
    })
except Exception:
    pass  # Settings may not be available during import

# ============================================================================
# Helper Functions
# ============================================================================

def get_metrics():
    """
    Get Prometheus metrics in text format
    
    Returns:
        bytes: Metrics in Prometheus text format
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type():
    """
    Get content type for Prometheus metrics
    
    Returns:
        str: Content type for metrics endpoint
    """
    return CONTENT_TYPE_LATEST

