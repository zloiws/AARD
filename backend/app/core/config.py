"""
Configuration management using Pydantic Settings
"""
import os
from pathlib import Path
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from dotenv import load_dotenv

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
        description="Module-specific log levels (JSON string, e.g., '{\"app.api\": \"DEBUG\"}')"
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
    enable_tracing: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    enable_caching: bool = Field(default=True, description="Enable caching")
    
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

