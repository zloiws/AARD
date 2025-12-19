"""
API routes for checkpoints
"""
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.checkpoint import Checkpoint
from app.services.checkpoint_service import CheckpointService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/checkpoints", tags=["checkpoints"])


class CheckpointResponse(BaseModel):
    """Checkpoint response model"""
    id: str
    entity_type: str
    entity_id: str
    state_hash: Optional[str]
    reason: Optional[str]
    created_by: Optional[str]
    created_at: str
    trace_id: Optional[str]
    
    class Config:
        from_attributes = True


class CheckpointDetailResponse(BaseModel):
    """Detailed checkpoint response model"""
    id: str
    entity_type: str
    entity_id: str
    state_data: dict
    state_hash: Optional[str]
    reason: Optional[str]
    created_by: Optional[str]
    created_at: str
    trace_id: Optional[str]
    
    class Config:
        from_attributes = True


class CheckpointCreateRequest(BaseModel):
    """Request to create a checkpoint"""
    entity_type: str
    entity_id: str
    state_data: dict
    reason: Optional[str] = None
    created_by: Optional[str] = None


@router.post("/", response_model=CheckpointResponse)
async def create_checkpoint(
    request: CheckpointCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new checkpoint"""
    try:
        entity_uuid = UUID(request.entity_id)
        service = CheckpointService(db)
        
        checkpoint = service.create_checkpoint(
            entity_type=request.entity_type,
            entity_id=entity_uuid,
            state_data=request.state_data,
            reason=request.reason,
            created_by=request.created_by or "system"
        )
        
        return CheckpointResponse(
            id=str(checkpoint.id),
            entity_type=checkpoint.entity_type,
            entity_id=str(checkpoint.entity_id),
            state_hash=checkpoint.state_hash,
            reason=checkpoint.reason,
            created_by=checkpoint.created_by,
            created_at=checkpoint.created_at.isoformat(),
            trace_id=checkpoint.trace_id,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[CheckpointResponse])
async def list_checkpoints(
    entity_type: str = Query(..., description="Entity type"),
    entity_id: str = Query(..., description="Entity ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of checkpoints"),
    db: Session = Depends(get_db)
):
    """List checkpoints for an entity"""
    try:
        entity_uuid = UUID(entity_id)
        service = CheckpointService(db)
        
        checkpoints = service.list_checkpoints(entity_type, entity_uuid, limit)
        
        return [
            CheckpointResponse(
                id=str(c.id),
                entity_type=c.entity_type,
                entity_id=str(c.entity_id),
                state_hash=c.state_hash,
                reason=c.reason,
                created_by=c.created_by,
                created_at=c.created_at.isoformat(),
                trace_id=c.trace_id,
            )
            for c in checkpoints
        ]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity ID format")
    except Exception as e:
        logger.error(f"Error listing checkpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{checkpoint_id}", response_model=CheckpointDetailResponse)
async def get_checkpoint(
    checkpoint_id: str,
    db: Session = Depends(get_db)
):
    """Get a checkpoint by ID"""
    try:
        checkpoint_uuid = UUID(checkpoint_id)
        service = CheckpointService(db)
        
        checkpoint = service.get_checkpoint(checkpoint_uuid)
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        return CheckpointDetailResponse(
            id=str(checkpoint.id),
            entity_type=checkpoint.entity_type,
            entity_id=str(checkpoint.entity_id),
            state_data=checkpoint.state_data,
            state_hash=checkpoint.state_hash,
            reason=checkpoint.reason,
            created_by=checkpoint.created_by,
            created_at=checkpoint.created_at.isoformat(),
            trace_id=checkpoint.trace_id,
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid checkpoint ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting checkpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_type}/{entity_id}/latest", response_model=CheckpointDetailResponse)
async def get_latest_checkpoint(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get the latest checkpoint for an entity"""
    try:
        entity_uuid = UUID(entity_id)
        service = CheckpointService(db)
        
        checkpoint = service.get_latest_checkpoint(entity_type, entity_uuid)
        if not checkpoint:
            raise HTTPException(status_code=404, detail="No checkpoint found")
        
        return CheckpointDetailResponse(
            id=str(checkpoint.id),
            entity_type=checkpoint.entity_type,
            entity_id=str(checkpoint.entity_id),
            state_data=checkpoint.state_data,
            state_hash=checkpoint.state_hash,
            reason=checkpoint.reason,
            created_by=checkpoint.created_by,
            created_at=checkpoint.created_at.isoformat(),
            trace_id=checkpoint.trace_id,
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest checkpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{checkpoint_id}/restore")
async def restore_checkpoint(
    checkpoint_id: str,
    db: Session = Depends(get_db)
):
    """Restore state from a checkpoint"""
    try:
        checkpoint_uuid = UUID(checkpoint_id)
        service = CheckpointService(db)
        
        state_data = service.restore_checkpoint(checkpoint_uuid)
        
        return {
            "status": "restored",
            "checkpoint_id": checkpoint_id,
            "state_data": state_data,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error restoring checkpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{entity_type}/{entity_id}/rollback")
async def rollback_entity(
    entity_type: str,
    entity_id: str,
    checkpoint_id: Optional[str] = Query(None, description="Optional checkpoint ID (uses latest if not provided)"),
    db: Session = Depends(get_db)
):
    """Rollback an entity to a checkpoint"""
    try:
        entity_uuid = UUID(entity_id)
        service = CheckpointService(db)
        
        checkpoint_uuid = UUID(checkpoint_id) if checkpoint_id else None
        state_data = service.rollback_entity(entity_type, entity_uuid, checkpoint_uuid)
        
        return {
            "status": "rolled_back",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "checkpoint_id": checkpoint_id,
            "state_data": state_data,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back entity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

