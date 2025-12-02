"""
Database model for Ollama server configuration
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class OllamaServer(Base):
    """Ollama server configuration stored in database"""
    __tablename__ = "ollama_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # Display name
    url = Column(String, nullable=False, unique=True)  # Base URL (e.g., http://10.39.0.6:11434)
    api_version = Column(String, default="v1")  # API version path (usually "v1")
    
    # Authentication (optional, for future use)
    auth_type = Column(String, nullable=True)  # "none", "basic", "bearer", "api_key"
    auth_config = Column(JSON, nullable=True)  # Flexible auth config: {"username": "...", "password": "..."} or {"token": "..."}
    
    # Server status
    is_active = Column(Boolean, default=True)  # Enable/disable server
    is_default = Column(Boolean, default=False)  # Default server for auto-selection
    
    # Metadata
    description = Column(String, nullable=True)
    capabilities = Column(JSON, nullable=True)  # ["general", "coding", "reasoning"]
    max_concurrent = Column(Integer, default=1)
    priority = Column(Integer, default=0)  # Higher priority = preferred
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=True)  # Last health check
    is_available = Column(Boolean, default=False)  # Last known availability status
    
    # Additional metadata
    server_metadata = Column(JSON, nullable=True)  # Version, models list, etc. (renamed from metadata to avoid SQLAlchemy conflict)

    def __repr__(self):
        return f"<OllamaServer(id={self.id}, name='{self.name}', url='{self.url}', is_active={self.is_active})>"
    
    def get_api_url(self) -> str:
        """Get full API URL"""
        base_url = self.url.rstrip("/")
        api_path = self.api_version.lstrip("/") if self.api_version else "v1"
        return f"{base_url}/{api_path}"

