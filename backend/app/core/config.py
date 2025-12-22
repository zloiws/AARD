"""
Configuration management using Pydantic Settings
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from project root
# config.py is at: backend/app/core/config.py
# Project root is: backend/app/core/../../../
# Try multiple paths to find .env file
_current_file = Path(__file__).resolve()
# From backend/app/core/config.py -> backend/ -> project root
_backend_dir = _current_file.parent.parent.parent
_project_root = _backend_dir.parent
ENV_FILE = _project_root / ".env"
# Fallback: try in backend/ directory if not found in project root
if not ENV_FILE.exists():
    ENV_FILE = _backend_dir / ".env"
# Load with override to ensure variables are available
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


class OllamaInstanceConfig(BaseSettings):
    """Configuration for a single Ollama instance"""
    url: str = Field(..., description="Ollama API URL")
    model: str = Field(..., description="Model name")
    capabilities: List[str] = Field(default_factory=list, description="Model capabilities")
    max_concurrent: int = Field(default=1, ge=1, description="Max concurrent requests")
    
    @field_validator("capabilities", mode="before")
    @classmethod
    def parse_capabilities(cls, v):
        """Parse capabilities from comma-separated string"""
        if isinstance(v, str):
            return [cap.strip() for cap in v.split(",") if cap.strip()]
        return v or []


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "AARD"
    app_env: str = Field(default="development", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(..., description="Secret key for encryption")
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")
    allowed_origins: str = Field(
        default="http://localhost:8000",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Logging
    log_sqlalchemy: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    log_uvicorn_access: bool = Field(default=False, description="Enable Uvicorn access logging")
    log_module_levels: Optional[str] = Field(
        default=None,
        description='Module-specific log levels (JSON string, e.g., {"app.api": "DEBUG"})'
    )
    log_format: str = Field(
        default="json",
        description="Log format: 'json' for structured logging, 'text' for plain text"
    )
    log_file_enabled: bool = Field(default=True, description="Enable file logging")
    log_file_path: str = Field(
        default="logs/aard.log",
        description="Path to log file (relative to project root)"
    )
    log_file_rotation: str = Field(
        default="midnight",
        description="Log file rotation: 'midnight', 'W0' (weekly), or size like '10MB'"
    )
    log_file_retention: int = Field(
        default=30,
        ge=1,
        description="Number of days to keep log files"
    )
    log_sensitive_data: bool = Field(
        default=False,
        description="Enable logging of sensitive data (passwords, tokens) - NOT RECOMMENDED"
    )
    
    # Database
    postgres_host: str = Field(..., description="PostgreSQL host")
    postgres_db: str = Field(..., description="PostgreSQL database name")
    postgres_user: str = Field(..., description="PostgreSQL user")
    postgres_password: str = Field(..., description="PostgreSQL password")
    postgres_port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    database_pool_size: int = Field(default=20, ge=1, description="Database pool size")
    database_max_overflow: int = Field(default=10, ge=0, description="Database max overflow")
    
    # Ollama Instance 1
    ollama_url_1: str = Field(..., description="First Ollama instance URL")
    ollama_model_1: str = Field(..., description="First Ollama model")
    ollama_capabilities_1: str = Field(default="", description="First Ollama capabilities (comma-separated)")
    ollama_max_concurrent_1: int = Field(default=2, ge=1, description="First Ollama max concurrent")
    
    # Ollama Instance 2
    ollama_url_2: str = Field(..., description="Second Ollama instance URL")
    ollama_model_2: str = Field(..., description="Second Ollama model")
    ollama_capabilities_2: str = Field(default="", description="Second Ollama capabilities (comma-separated)")
    ollama_max_concurrent_2: int = Field(default=1, ge=1, description="Second Ollama max concurrent")
    
    # Features
    enable_agent_ops: bool = Field(default=False, description="Enable Agent Ops features")
    enable_a2a: bool = Field(default=False, description="Enable A2A communication")
    enable_planning: bool = Field(default=False, description="Enable planning system")
    interpretation_use_llm: bool = Field(default=True, description="Enable LLM-assisted interpretation (platform default)")
    enable_tracing: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    tracing_service_name: str = Field(default="aard", description="Service name for tracing")
    tracing_exporter: str = Field(
        default="console",
        description="Tracing exporter: 'console', 'otlp', 'database'"
    )
    tracing_otlp_endpoint: Optional[str] = Field(
        default=None,
        description="OTLP endpoint URL (e.g., http://localhost:4318/v1/traces)"
    )
    enable_caching: bool = Field(default=True, description="Enable caching")
    
    # ========================================================================
    # ГЛОБАЛЬНЫЕ ОГРАНИЧЕНИЯ ДЛЯ ЛЛМ И КОДА (СТОПОРЫ)
    # Цель: скорость и экономия ресурсов, нет неограниченным размышлениям
    # ========================================================================
    
    # LLM Ограничения (стопоры для размышлений)
    llm_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Максимальное время ожидания ответа LLM (секунды)"
    )
    llm_max_tokens: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="Максимальное количество токенов в ответе LLM (ограничение 'думать час')"
    )
    llm_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Температура LLM (низкая = быстрые детерминированные ответы)"
    )
    llm_top_p: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Top-p для LLM (ограничение выборки)"
    )
    llm_num_ctx: int = Field(
        default=2048,
        ge=512,
        le=8192,
        description="Размер контекста LLM (уменьшен для скорости)"
    )
    
    # Планирование ограничения
    planning_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Максимальное время генерации плана (секунды)"
    )
    planning_max_steps: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Максимальное количество шагов в плане"
    )
    
    # Выполнение ограничения
    execution_timeout_seconds: int = Field(
        default=45,
        ge=5,
        le=300,
        description="Максимальное время выполнения одного шага (секунды)"
    )
    execution_max_total_timeout_seconds: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Максимальное время выполнения всего плана (секунды)"
    )
    
    # Код выполнение ограничения (sandbox)
    code_execution_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Максимальное время выполнения кода (секунды)"
    )
    code_execution_memory_limit_mb: int = Field(
        default=256,
        ge=64,
        le=1024,
        description="Максимальное использование памяти для выполнения кода (MB)"
    )
    code_execution_max_output_size_mb: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Максимальный размер вывода кода (MB)"
    )
    code_execution_cpu_limit_percent: int = Field(
        default=50,
        ge=10,
        le=100,
        description="Максимальное использование CPU для выполнения кода (процент)"
    )
    
    # Automatic Replanning Configuration
    enable_auto_replanning: bool = Field(
        default=True,
        description="Enable automatic replanning on errors"
    )
    auto_replanning_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of automatic replanning attempts per task"
    )
    auto_replanning_min_interval_seconds: int = Field(
        default=5,
        ge=0,
        description="Minimum interval between replanning attempts (seconds)"
    )
    auto_replanning_timeout_seconds: int = Field(
        default=300,
        ge=30,
        description="Timeout for each replanning attempt (seconds)"
    )
    auto_replanning_trigger_critical: bool = Field(
        default=True,
        description="Trigger replanning for CRITICAL severity errors"
    )
    auto_replanning_trigger_high: bool = Field(
        default=True,
        description="Trigger replanning for HIGH severity errors"
    )
    auto_replanning_trigger_medium: bool = Field(
        default=False,
        description="Trigger replanning for MEDIUM severity errors"
    )
    auto_replanning_require_human_intervention_after: int = Field(
        default=5,
        ge=1,
        description="Require human intervention after N failed replanning attempts"
    )
    
    @property
    def database_url(self) -> str:
        """Construct database URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def ollama_instance_1(self) -> OllamaInstanceConfig:
        """Get first Ollama instance config"""
        capabilities = [
            cap.strip() 
            for cap in self.ollama_capabilities_1.split(",") 
            if cap.strip()
        ] if self.ollama_capabilities_1 else []
        return OllamaInstanceConfig(
            url=self.ollama_url_1,
            model=self.ollama_model_1,
            capabilities=capabilities,
            max_concurrent=self.ollama_max_concurrent_1,
        )
    
    @property
    def ollama_instance_2(self) -> OllamaInstanceConfig:
        """Get second Ollama instance config"""
        capabilities = [
            cap.strip() 
            for cap in self.ollama_capabilities_2.split(",") 
            if cap.strip()
        ] if self.ollama_capabilities_2 else []
        return OllamaInstanceConfig(
            url=self.ollama_url_2,
            model=self.ollama_model_2,
            capabilities=capabilities,
            max_concurrent=self.ollama_max_concurrent_2,
        )
    
    @property
    def ollama_instances(self) -> List[OllamaInstanceConfig]:
        """Get list of all Ollama instances"""
        return [self.ollama_instance_1, self.ollama_instance_2]
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

