"""
Memory Service for managing agent short-term and long-term memory
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.agent_memory import (
    AgentMemory, MemoryEntry, MemoryAssociation,
    MemoryType, AssociationType
)
from app.models.agent import Agent
from app.services.embedding_service import EmbeddingService
from sqlalchemy import text

logger = LoggingConfig.get_logger(__name__)


class MemoryService:
    """Service for managing agent memory"""
    
    def __init__(self, db: Session = None):
        """
        Initialize Memory Service
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or SessionLocal()
        self.embedding_service = EmbeddingService(self.db)
    
    # Long-term memory methods
    
    def save_memory(
        self,
        agent_id: UUID,
        memory_type: str,
        content: Dict[str, Any],
        summary: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> AgentMemory:
        """
        Save a memory to long-term storage
        
        Args:
            agent_id: Agent ID
            memory_type: Type of memory (fact, experience, pattern, rule)
            content: Memory content (dict)
            summary: Human-readable summary
            importance: Importance score (0.0 to 1.0)
            tags: Tags for categorization
            source: Source of memory (task_id, user, etc.)
            expires_at: Optional expiration date
            
        Returns:
            Created AgentMemory
        """
        # Validate agent exists
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Validate importance range
        importance = max(0.0, min(1.0, importance))
        
        memory = AgentMemory(
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            summary=summary,
            importance=importance,
            tags=tags or [],
            source=source,
            expires_at=expires_at
        )
        
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        
        logger.info(
            f"Saved memory for agent {agent_id}",
            extra={
                "memory_id": str(memory.id),
                "memory_type": memory_type,
                "importance": importance
            }
        )
        
        return memory
    
    def get_memory(self, memory_id: UUID) -> Optional[AgentMemory]:
        """
        Get a memory by ID
        
        Args:
            memory_id: Memory ID
            
        Returns:
            AgentMemory or None
        """
        memory = self.db.query(AgentMemory).filter(AgentMemory.id == memory_id).first()
        
        if memory:
            # Update access tracking
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()
            self.db.commit()
        
        return memory
    
    def get_memories(
        self,
        agent_id: UUID,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[AgentMemory]:
        """
        Get memories for an agent with filters
        
        Args:
            agent_id: Agent ID
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            tags: Filter by tags (any match)
            limit: Maximum number of results
            
        Returns:
            List of AgentMemory
        """
        query = self.db.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            or_(
                AgentMemory.expires_at.is_(None),
                AgentMemory.expires_at > datetime.utcnow()
            )
        )
        
        if memory_type:
            query = query.filter(AgentMemory.memory_type == memory_type)
        
        if min_importance is not None:
            query = query.filter(AgentMemory.importance >= min_importance)
        
        if tags:
            # Filter by tags using JSONB contains
            for tag in tags:
                query = query.filter(AgentMemory.tags.contains([tag]))
        
        return query.order_by(desc(AgentMemory.importance), desc(AgentMemory.last_accessed_at)).limit(limit).all()
    
    def search_memories(
        self,
        agent_id: UUID,
        query_text: Optional[str] = None,
        content_query: Optional[Dict[str, Any]] = None,
        memory_type: Optional[str] = None,
        limit: int = 20
    ) -> List[AgentMemory]:
        """
        Search memories by text or content
        
        Args:
            agent_id: Agent ID
            query_text: Text to search in summary
            content_query: JSONB query for content (PostgreSQL JSONB operators)
            memory_type: Filter by memory type
            limit: Maximum number of results
            
        Returns:
            List of matching AgentMemory
        """
        query = self.db.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            or_(
                AgentMemory.expires_at.is_(None),
                AgentMemory.expires_at > datetime.utcnow()
            )
        )
        
        if memory_type:
            query = query.filter(AgentMemory.memory_type == memory_type)
        
        if query_text:
            # Search in summary (case-insensitive)
            query = query.filter(AgentMemory.summary.ilike(f"%{query_text}%"))
        
        if content_query:
            # Use JSONB contains for content search
            # This is a simple implementation - can be extended with more complex queries
            for key, value in content_query.items():
                query = query.filter(
                    func.jsonb_extract_path_text(AgentMemory.content, key) == str(value)
                )
        
        return query.order_by(desc(AgentMemory.importance), desc(AgentMemory.last_accessed_at)).limit(limit).all()
    
    def update_memory(
        self,
        memory_id: UUID,
        content: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[AgentMemory]:
        """
        Update a memory
        
        Args:
            memory_id: Memory ID
            content: New content
            summary: New summary
            importance: New importance score
            tags: New tags
            
        Returns:
            Updated AgentMemory or None
        """
        memory = self.db.query(AgentMemory).filter(AgentMemory.id == memory_id).first()
        if not memory:
            return None
        
        if content is not None:
            memory.content = content
        if summary is not None:
            memory.summary = summary
        if importance is not None:
            memory.importance = max(0.0, min(1.0, importance))
        if tags is not None:
            memory.tags = tags
        
        self.db.commit()
        self.db.refresh(memory)
        
        logger.debug(f"Updated memory {memory_id}")
        
        return memory
    
    def forget_memory(self, memory_id: UUID) -> bool:
        """
        Delete a memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if deleted, False if not found
        """
        memory = self.db.query(AgentMemory).filter(AgentMemory.id == memory_id).first()
        if not memory:
            return False
        
        self.db.delete(memory)
        self.db.commit()
        
        logger.info(f"Deleted memory {memory_id}")
        
        return True
    
    def forget_expired_memories(self, agent_id: Optional[UUID] = None) -> int:
        """
        Delete expired memories
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            Number of deleted memories
        """
        query = self.db.query(AgentMemory).filter(
            AgentMemory.expires_at.isnot(None),
            AgentMemory.expires_at <= datetime.utcnow()
        )
        
        if agent_id:
            query = query.filter(AgentMemory.agent_id == agent_id)
        
        count = query.count()
        query.delete(synchronize_session=False)
        self.db.commit()
        
        if count > 0:
            logger.info(f"Deleted {count} expired memories")
        
        return count
    
    # Short-term memory methods
    
    def save_context(
        self,
        agent_id: UUID,
        context_key: str,
        content: Dict[str, Any],
        session_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> MemoryEntry:
        """
        Save context to short-term memory
        
        Args:
            agent_id: Agent ID
            context_key: Key for context lookup
            content: Context data
            session_id: Optional session ID
            ttl_seconds: Time to live in seconds
            
        Returns:
            Created MemoryEntry
        """
        # Validate agent exists
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Calculate expiration
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        # Check if entry exists for this key and session
        existing = self.db.query(MemoryEntry).filter(
            MemoryEntry.agent_id == agent_id,
            MemoryEntry.context_key == context_key,
            MemoryEntry.session_id == session_id
        ).first()
        
        if existing:
            # Update existing entry
            existing.content = content
            existing.expires_at = expires_at
            existing.ttl_seconds = ttl_seconds
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new entry
        entry = MemoryEntry(
            agent_id=agent_id,
            session_id=session_id,
            context_key=context_key,
            content=content,
            ttl_seconds=ttl_seconds,
            expires_at=expires_at
        )
        
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        
        logger.debug(
            f"Saved context for agent {agent_id}",
            extra={"context_key": context_key, "session_id": session_id}
        )
        
        return entry
    
    def get_context(
        self,
        agent_id: UUID,
        context_key: str,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get context from short-term memory
        
        Args:
            agent_id: Agent ID
            context_key: Context key
            session_id: Optional session ID
            
        Returns:
            Context content or None
        """
        query = self.db.query(MemoryEntry).filter(
            MemoryEntry.agent_id == agent_id,
            MemoryEntry.context_key == context_key,
            or_(
                MemoryEntry.expires_at.is_(None),
                MemoryEntry.expires_at > datetime.utcnow()
            )
        )
        
        if session_id:
            query = query.filter(MemoryEntry.session_id == session_id)
        
        entry = query.first()
        
        if entry and entry.is_expired():
            # Entry expired, delete it
            self.db.delete(entry)
            self.db.commit()
            return None
        
        return entry.content if entry else None
    
    def get_all_context(
        self,
        agent_id: UUID,
        session_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all context entries for an agent/session
        
        Args:
            agent_id: Agent ID
            session_id: Optional session ID
            
        Returns:
            Dictionary of context_key -> content
        """
        query = self.db.query(MemoryEntry).filter(
            MemoryEntry.agent_id == agent_id,
            or_(
                MemoryEntry.expires_at.is_(None),
                MemoryEntry.expires_at > datetime.utcnow()
            )
        )
        
        if session_id:
            query = query.filter(MemoryEntry.session_id == session_id)
        
        entries = query.all()
        
        # Filter out expired entries
        result = {}
        for entry in entries:
            if not entry.is_expired():
                result[entry.context_key] = entry.content
            else:
                # Delete expired entry
                self.db.delete(entry)
        
        self.db.commit()
        
        return result
    
    def clear_context(
        self,
        agent_id: UUID,
        session_id: Optional[str] = None,
        context_key: Optional[str] = None
    ) -> int:
        """
        Clear context entries
        
        Args:
            agent_id: Agent ID
            session_id: Optional session ID to filter by
            context_key: Optional context key to filter by
            
        Returns:
            Number of deleted entries
        """
        query = self.db.query(MemoryEntry).filter(MemoryEntry.agent_id == agent_id)
        
        if session_id:
            query = query.filter(MemoryEntry.session_id == session_id)
        
        if context_key:
            query = query.filter(MemoryEntry.context_key == context_key)
        
        count = query.count()
        query.delete(synchronize_session=False)
        self.db.commit()
        
        if count > 0:
            logger.debug(f"Cleared {count} context entries for agent {agent_id}")
        
        return count
    
    def clear_expired_context(self, agent_id: Optional[UUID] = None) -> int:
        """
        Clear expired context entries
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            Number of deleted entries
        """
        query = self.db.query(MemoryEntry).filter(
            MemoryEntry.expires_at.isnot(None),
            MemoryEntry.expires_at <= datetime.utcnow()
        )
        
        if agent_id:
            query = query.filter(MemoryEntry.agent_id == agent_id)
        
        count = query.count()
        query.delete(synchronize_session=False)
        self.db.commit()
        
        if count > 0:
            logger.debug(f"Cleared {count} expired context entries")
        
        return count
    
    # Association methods
    
    def create_association(
        self,
        memory_id: UUID,
        related_memory_id: UUID,
        association_type: str,
        strength: float = 0.5,
        description: Optional[str] = None
    ) -> MemoryAssociation:
        """
        Create an association between memories
        
        Args:
            memory_id: First memory ID
            related_memory_id: Related memory ID
            association_type: Type of association
            strength: Association strength (0.0 to 1.0)
            description: Description of association
            
        Returns:
            Created MemoryAssociation
        """
        # Validate memories exist
        memory1 = self.db.query(AgentMemory).filter(AgentMemory.id == memory_id).first()
        memory2 = self.db.query(AgentMemory).filter(AgentMemory.id == related_memory_id).first()
        
        if not memory1 or not memory2:
            raise ValueError("One or both memories not found")
        
        if memory_id == related_memory_id:
            raise ValueError("Cannot associate memory with itself")
        
        # Check if association already exists
        existing = self.db.query(MemoryAssociation).filter(
            MemoryAssociation.memory_id == memory_id,
            MemoryAssociation.related_memory_id == related_memory_id
        ).first()
        
        if existing:
            # Update existing
            existing.association_type = association_type
            existing.strength = max(0.0, min(1.0, strength))
            existing.description = description
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new association
        association = MemoryAssociation(
            memory_id=memory_id,
            related_memory_id=related_memory_id,
            association_type=association_type,
            strength=max(0.0, min(1.0, strength)),
            description=description
        )
        
        self.db.add(association)
        self.db.commit()
        self.db.refresh(association)
        
        logger.debug(
            f"Created association between memories {memory_id} and {related_memory_id}",
            extra={"association_type": association_type, "strength": strength}
        )
        
        return association
    
    def get_related_memories(
        self,
        memory_id: UUID,
        association_type: Optional[str] = None,
        min_strength: Optional[float] = None,
        limit: int = 20
    ) -> List[AgentMemory]:
        """
        Get memories related to a given memory
        
        Args:
            memory_id: Memory ID
            association_type: Filter by association type
            min_strength: Minimum association strength
            limit: Maximum number of results
            
        Returns:
            List of related AgentMemory
        """
        query = self.db.query(AgentMemory).join(
            MemoryAssociation,
            AgentMemory.id == MemoryAssociation.related_memory_id
        ).filter(
            MemoryAssociation.memory_id == memory_id,
            or_(
                AgentMemory.expires_at.is_(None),
                AgentMemory.expires_at > datetime.utcnow()
            )
        )
        
        if association_type:
            query = query.filter(MemoryAssociation.association_type == association_type)
        
        if min_strength is not None:
            query = query.filter(MemoryAssociation.strength >= min_strength)
        
        return query.order_by(desc(MemoryAssociation.strength)).limit(limit).all()
    
    def delete_association(self, association_id: UUID) -> bool:
        """
        Delete an association
        
        Args:
            association_id: Association ID
            
        Returns:
            True if deleted, False if not found
        """
        association = self.db.query(MemoryAssociation).filter(
            MemoryAssociation.id == association_id
        ).first()
        
        if not association:
            return False
        
        self.db.delete(association)
        self.db.commit()
        
        logger.debug(f"Deleted association {association_id}")
        
        return True

