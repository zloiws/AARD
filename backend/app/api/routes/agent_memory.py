"""
API routes for agent memory management
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.services.memory_service import MemoryService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(tags=["agent-memory"])


# Request/Response models
class CreateMemoryRequest(BaseModel):
    """Request to create a memory"""
    memory_type: str
    content: dict
    summary: Optional[str] = None
    importance: float = Field(0.5, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    expires_at: Optional[datetime] = None


class MemoryResponse(BaseModel):
    """Memory response model"""
    id: str
    agent_id: str
    memory_type: str
    content: dict
    summary: Optional[str]
    importance: float
    access_count: int
    last_accessed_at: Optional[str]
    tags: Optional[List[str]]
    source: Optional[str]
    created_at: str
    expires_at: Optional[str]


class UpdateMemoryRequest(BaseModel):
    """Request to update a memory"""
    content: Optional[dict] = None
    summary: Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None


class SearchMemoryRequest(BaseModel):
    """Request to search memories"""
    query_text: Optional[str] = None
    content_query: Optional[dict] = None
    memory_type: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)


class SaveContextRequest(BaseModel):
    """Request to save context"""
    context_key: str
    content: dict
    session_id: Optional[str] = None
    ttl_seconds: Optional[int] = None


class ContextResponse(BaseModel):
    """Context response model"""
    id: str
    agent_id: str
    session_id: Optional[str]
    context_key: str
    content: dict
    ttl_seconds: Optional[int]
    created_at: str
    expires_at: Optional[str]


class CreateAssociationRequest(BaseModel):
    """Request to create memory association"""
    related_memory_id: str
    association_type: str
    strength: float = Field(0.5, ge=0.0, le=1.0)
    description: Optional[str] = None


@router.get("/{agent_id}/memory", response_model=List[MemoryResponse])
async def list_memories(
    agent_id: str,
    memory_type: Optional[str] = Query(None),
    min_importance: Optional[float] = Query(None, ge=0.0, le=1.0),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List agent memories with filters"""
    try:
        memory_service = MemoryService(db)
        
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
        
        memories = memory_service.get_memories(
            agent_id=UUID(agent_id),
            memory_type=memory_type,
            min_importance=min_importance,
            tags=tag_list,
            limit=limit
        )
        
        return [
            MemoryResponse(
                id=str(m.id),
                agent_id=str(m.agent_id),
                memory_type=m.memory_type,
                content=m.content,
                summary=m.summary,
                importance=m.importance,
                access_count=m.access_count,
                last_accessed_at=m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                tags=m.tags,
                source=m.source,
                created_at=m.created_at.isoformat(),
                expires_at=m.expires_at.isoformat() if m.expires_at else None,
            )
            for m in memories
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/memory", response_model=MemoryResponse)
async def create_memory(
    agent_id: str,
    request: CreateMemoryRequest,
    db: Session = Depends(get_db)
):
    """Create a new memory"""
    try:
        memory_service = MemoryService(db)
        memory = memory_service.save_memory(
            agent_id=UUID(agent_id),
            memory_type=request.memory_type,
            content=request.content,
            summary=request.summary,
            importance=request.importance,
            tags=request.tags,
            source=request.source,
            expires_at=request.expires_at
        )
        
        return MemoryResponse(
            id=str(memory.id),
            agent_id=str(memory.agent_id),
            memory_type=memory.memory_type,
            content=memory.content,
            summary=memory.summary,
            importance=memory.importance,
            access_count=memory.access_count,
            last_accessed_at=memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
            tags=memory.tags,
            source=memory.source,
            created_at=memory.created_at.isoformat(),
            expires_at=memory.expires_at.isoformat() if memory.expires_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/memory/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    agent_id: str,
    memory_id: str,
    db: Session = Depends(get_db)
):
    """Get a memory by ID"""
    try:
        memory_service = MemoryService(db)
        memory = memory_service.get_memory(UUID(memory_id))
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if str(memory.agent_id) != agent_id:
            raise HTTPException(status_code=403, detail="Memory belongs to different agent")
        
        return MemoryResponse(
            id=str(memory.id),
            agent_id=str(memory.agent_id),
            memory_type=memory.memory_type,
            content=memory.content,
            summary=memory.summary,
            importance=memory.importance,
            access_count=memory.access_count,
            last_accessed_at=memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
            tags=memory.tags,
            source=memory.source,
            created_at=memory.created_at.isoformat(),
            expires_at=memory.expires_at.isoformat() if memory.expires_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}/memory/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    agent_id: str,
    memory_id: str,
    request: UpdateMemoryRequest,
    db: Session = Depends(get_db)
):
    """Update a memory"""
    try:
        memory_service = MemoryService(db)
        memory = memory_service.update_memory(
            memory_id=UUID(memory_id),
            content=request.content,
            summary=request.summary,
            importance=request.importance,
            tags=request.tags
        )
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if str(memory.agent_id) != agent_id:
            raise HTTPException(status_code=403, detail="Memory belongs to different agent")
        
        return MemoryResponse(
            id=str(memory.id),
            agent_id=str(memory.agent_id),
            memory_type=memory.memory_type,
            content=memory.content,
            summary=memory.summary,
            importance=memory.importance,
            access_count=memory.access_count,
            last_accessed_at=memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
            tags=memory.tags,
            source=memory.source,
            created_at=memory.created_at.isoformat(),
            expires_at=memory.expires_at.isoformat() if memory.expires_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}/memory/{memory_id}")
async def delete_memory(
    agent_id: str,
    memory_id: str,
    db: Session = Depends(get_db)
):
    """Delete a memory"""
    try:
        memory_service = MemoryService(db)
        
        # Check memory exists and belongs to agent
        memory = memory_service.get_memory(UUID(memory_id))
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if str(memory.agent_id) != agent_id:
            raise HTTPException(status_code=403, detail="Memory belongs to different agent")
        
        deleted = memory_service.forget_memory(UUID(memory_id))
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {"status": "deleted", "memory_id": memory_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/memory/search", response_model=List[MemoryResponse])
async def search_memories(
    agent_id: str,
    request: SearchMemoryRequest,
    db: Session = Depends(get_db)
):
    """Search memories"""
    try:
        memory_service = MemoryService(db)
        memories = memory_service.search_memories(
            agent_id=UUID(agent_id),
            query_text=request.query_text,
            content_query=request.content_query,
            memory_type=request.memory_type,
            limit=request.limit
        )
        
        return [
            MemoryResponse(
                id=str(m.id),
                agent_id=str(m.agent_id),
                memory_type=m.memory_type,
                content=m.content,
                summary=m.summary,
                importance=m.importance,
                access_count=m.access_count,
                last_accessed_at=m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                tags=m.tags,
                source=m.source,
                created_at=m.created_at.isoformat(),
                expires_at=m.expires_at.isoformat() if m.expires_at else None,
            )
            for m in memories
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/context", response_model=ContextResponse)
async def save_context(
    agent_id: str,
    request: SaveContextRequest,
    db: Session = Depends(get_db)
):
    """Save context to short-term memory"""
    try:
        memory_service = MemoryService(db)
        entry = memory_service.save_context(
            agent_id=UUID(agent_id),
            context_key=request.context_key,
            content=request.content,
            session_id=request.session_id,
            ttl_seconds=request.ttl_seconds
        )
        
        return ContextResponse(
            id=str(entry.id),
            agent_id=str(entry.agent_id),
            session_id=entry.session_id,
            context_key=entry.context_key,
            content=entry.content,
            ttl_seconds=entry.ttl_seconds,
            created_at=entry.created_at.isoformat(),
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/context/{context_key}")
async def get_context(
    agent_id: str,
    context_key: str,
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get context from short-term memory"""
    try:
        memory_service = MemoryService(db)
        content = memory_service.get_context(
            agent_id=UUID(agent_id),
            context_key=context_key,
            session_id=session_id
        )
        
        if content is None:
            raise HTTPException(status_code=404, detail="Context not found")
        
        return {"context_key": context_key, "content": content}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/context")
async def get_all_context(
    agent_id: str,
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all context entries for an agent/session"""
    try:
        memory_service = MemoryService(db)
        context = memory_service.get_all_context(
            agent_id=UUID(agent_id),
            session_id=session_id
        )
        
        return {"context": context}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting all context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}/context")
async def clear_context(
    agent_id: str,
    session_id: Optional[str] = Query(None),
    context_key: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Clear context entries"""
    try:
        memory_service = MemoryService(db)
        count = memory_service.clear_context(
            agent_id=UUID(agent_id),
            session_id=session_id,
            context_key=context_key
        )
        
        return {"status": "cleared", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error clearing context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/memory/{memory_id}/associate")
async def create_association(
    agent_id: str,
    memory_id: str,
    request: CreateAssociationRequest,
    db: Session = Depends(get_db)
):
    """Create an association between memories"""
    try:
        memory_service = MemoryService(db)
        
        # Verify memory belongs to agent
        memory = memory_service.get_memory(UUID(memory_id))
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if str(memory.agent_id) != agent_id:
            raise HTTPException(status_code=403, detail="Memory belongs to different agent")
        
        association = memory_service.create_association(
            memory_id=UUID(memory_id),
            related_memory_id=UUID(request.related_memory_id),
            association_type=request.association_type,
            strength=request.strength,
            description=request.description
        )
        
        return {
            "id": str(association.id),
            "memory_id": str(association.memory_id),
            "related_memory_id": str(association.related_memory_id),
            "association_type": association.association_type,
            "strength": association.strength,
            "description": association.description,
            "created_at": association.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating association: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/memory/{memory_id}/related")
async def get_related_memories(
    agent_id: str,
    memory_id: str,
    association_type: Optional[str] = Query(None),
    min_strength: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get memories related to a given memory"""
    try:
        memory_service = MemoryService(db)
        
        # Verify memory belongs to agent
        memory = memory_service.get_memory(UUID(memory_id))
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if str(memory.agent_id) != agent_id:
            raise HTTPException(status_code=403, detail="Memory belongs to different agent")
        
        related = memory_service.get_related_memories(
            memory_id=UUID(memory_id),
            association_type=association_type,
            min_strength=min_strength,
            limit=limit
        )
        
        return [
            {
                "id": str(m.id),
                "memory_type": m.memory_type,
                "summary": m.summary,
                "importance": m.importance,
            }
            for m in related
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting related memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

