"""
Database model for Ollama model configuration
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class OllamaModel(Base):
    """Ollama model configuration linked to server"""
    __tablename__ = "ollama_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(UUID(as_uuid=True), ForeignKey("ollama_servers.id", ondelete="CASCADE"), nullable=False)
    
    # Model identification
    name = Column(String, nullable=False)  # Display name (e.g., "qwen3-vl:8b")
    model_name = Column(String, nullable=False)  # Exact model name from Ollama API
    digest = Column(String, nullable=True)  # Model digest/hash
    
    # Model info
    size_bytes = Column(BigInteger, nullable=True)  # Model size in bytes
    format = Column(String, nullable=True)  # Model format (e.g., "gguf")
    
    # Metadata from Ollama
    modified_at = Column(DateTime, nullable=True)
    details = Column(JSON, nullable=True)  # Full model details from Ollama
    
    # Configuration
    is_active = Column(Boolean, default=True)
    capabilities = Column(JSON, nullable=True)  # ["code_generation", "reasoning", etc.]
    priority = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, nullable=True)  # Last time model was seen on server
    
    # Relationship
    server = relationship("OllamaServer", backref="models")

    def __repr__(self):
        return f"<OllamaModel(id={self.id}, name='{self.name}', server_id={self.server_id})>"

