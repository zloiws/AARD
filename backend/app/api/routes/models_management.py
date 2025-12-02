"""
API routes for managing models (capabilities, priority, etc.)
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
import httpx

from app.core.database import get_db
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer

router = APIRouter(prefix="/api/models", tags=["models_management"])


class ModelUpdate(BaseModel):
    """Request model for updating model configuration"""
    name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class ModelResponse(BaseModel):
    """Response model for model"""
    id: str
    name: str
    model_name: str
    is_active: bool
    capabilities: Optional[List[str]]
    priority: int
    size_bytes: Optional[int]
    created_at: datetime
    updated_at: datetime


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: UUID, db: Session = Depends(get_db)):
    """Get model by ID"""
    model = db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return ModelResponse(
        id=str(model.id),
        name=model.name,
        model_name=model.model_name,
        is_active=model.is_active,
        capabilities=model.capabilities or [],
        priority=model.priority or 0,
        size_bytes=model.size_bytes,
        created_at=model.created_at,
        updated_at=model.updated_at
    )


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    update: ModelUpdate,
    db: Session = Depends(get_db)
):
    """Update model configuration"""
    model = db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if update.name is not None:
        model.name = update.name
    if update.capabilities is not None:
        model.capabilities = update.capabilities
    if update.priority is not None:
        model.priority = update.priority
    if update.is_active is not None:
        model.is_active = update.is_active
    
    model.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(model)
    
    return ModelResponse(
        id=str(model.id),
        name=model.name,
        model_name=model.model_name,
        is_active=model.is_active,
        capabilities=model.capabilities or [],
        priority=model.priority or 0,
        size_bytes=model.size_bytes,
        created_at=model.created_at,
        updated_at=model.updated_at
    )


@router.post("/{model_id}/check-availability")
async def check_model_availability(model_id: UUID, db: Session = Depends(get_db)):
    """Check if model is available on its server"""
    model = db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    server = db.query(OllamaServer).filter(OllamaServer.id == model.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    try:
        base_url = server.url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        elif base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            # Check if model exists
            response = await client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            models = [m.get("name", "") for m in data.get("models", [])]
            is_available = model.model_name in models
            
            # Update model availability in database
            model.last_seen_at = datetime.utcnow()
            db.commit()
            
            return {
                "model_id": str(model.id),
                "model_name": model.model_name,
                "is_available": is_available,
                "server_url": server.url
            }
    except Exception as e:
        return {
            "model_id": str(model.id),
            "model_name": model.model_name,
            "is_available": False,
            "error": str(e),
            "server_url": server.url
        }


@router.get("/server/{server_id}/check-all")
async def check_all_models_availability(server_id: UUID, db: Session = Depends(get_db)):
    """Check availability of all models on a server"""
    server = db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    models = db.query(OllamaModel).filter(OllamaModel.server_id == server_id).all()
    
    results = []
    for model in models:
        result = await check_model_availability(model.id, db)
        results.append(result)
    
    return {"server_id": str(server_id), "results": results}


@router.post("/{model_id}/unload")
async def unload_model(model_id: UUID, db: Session = Depends(get_db)):
    """
    Unload model from Ollama server (remove from GPU memory)
    
    This sends a request to Ollama to unload the model from GPU memory.
    Note: Ollama doesn't have a direct unload endpoint, but we can use
    a workaround by checking running processes and potentially using
    the /api/generate endpoint with a special flag (if supported).
    
    TODO: Implement proper GPU unload when Ollama API supports it.
    For now, this is a placeholder that checks if model is loaded.
    """
    model = db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    server = db.query(OllamaServer).filter(OllamaServer.id == model.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    try:
        base_url = server.url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        elif base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            # Check what models are currently loaded in GPU
            # Ollama API: GET /api/ps returns running processes
            try:
                ps_response = await client.get("/api/ps", timeout=10.0)
                ps_response.raise_for_status()
                ps_data = ps_response.json()
                
                loaded_models = [proc.get("model", "") for proc in ps_data.get("models", [])]
                is_loaded = model.model_name in loaded_models
                
                if not is_loaded:
                    return {
                        "model_id": str(model.id),
                        "model_name": model.model_name,
                        "status": "not_loaded",
                        "message": "Model is not currently loaded in GPU"
                    }
                
                # TODO: Implement actual unload when Ollama API supports it
                # For now, return information about loaded model
                # In the future, we might need to:
                # 1. Use a special API endpoint (if Ollama adds one)
                # 2. Or wait for model to timeout naturally
                # 3. Or restart Ollama service (not recommended)
                
                return {
                    "model_id": str(model.id),
                    "model_name": model.model_name,
                    "status": "loaded",
                    "message": "Model is loaded in GPU. Automatic unload not yet implemented.",
                    "note": "TODO: Implement GPU unload when Ollama API supports it. See backend/app/api/routes/models_management.py"
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # /api/ps might not be available in all Ollama versions
                    return {
                        "model_id": str(model.id),
                        "model_name": model.model_name,
                        "status": "unknown",
                        "message": "Cannot check model status - /api/ps endpoint not available",
                        "note": "TODO: Implement GPU unload when Ollama API supports it"
                    }
                raise
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking model status: {str(e)}"
        )


@router.post("/{model_id}/unload-from-gpu")
async def unload_model_from_gpu(model_id: UUID, db: Session = Depends(get_db)):
    """
    Unload model from GPU when switching to another model
    
    This is a placeholder for future implementation.
    The idea is to automatically unload the current model from GPU
    when a request comes for a different model, to free up GPU memory.
    
    TODO: Implement automatic GPU unload logic:
    1. Check which model is currently loaded in GPU
    2. If different from requested model, unload current model
    3. Load requested model
    4. Handle errors gracefully
    
    This should be called automatically by OllamaClient before generating
    with a new model if the previous model is still loaded.
    """
    model = db.query(OllamaModel).filter(OllamaModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    server = db.query(OllamaServer).filter(OllamaServer.id == model.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # TODO: Implement actual GPU unload logic
    # For now, return a placeholder response
    return {
        "model_id": str(model.id),
        "model_name": model.model_name,
        "status": "not_implemented",
        "message": "Automatic GPU unload is not yet implemented",
        "note": "TODO: Implement in backend/app/api/routes/models_management.py and backend/app/core/ollama_client.py",
        "future_implementation": {
            "description": "When a request comes for model B while model A is loaded:",
            "steps": [
                "1. Check /api/ps to see which model is loaded",
                "2. If different, attempt to unload current model",
                "3. Load requested model",
                "4. Proceed with generation"
            ],
            "challenges": [
                "Ollama API doesn't have direct unload endpoint",
                "May need to wait for natural timeout",
                "Or implement workaround (if available)"
            ]
        }
    }
