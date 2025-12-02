"""
API routes for managing Ollama servers in database
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.ollama_server import OllamaServer
from app.models.ollama_model import OllamaModel
from app.services.ollama_service import OllamaService
import httpx

router = APIRouter(prefix="/api/servers", tags=["servers"])
logger = LoggingConfig.get_logger(__name__)


class ServerCreate(BaseModel):
    """Request model for creating server"""
    name: str = Field(..., description="Server display name")
    url: str = Field(..., description="Server base URL (e.g., http://10.39.0.6:11434)")
    api_version: str = Field(default="v1", description="API version path")
    auth_type: Optional[str] = Field(default=None, description="Authentication type")
    auth_config: Optional[dict] = Field(default=None, description="Authentication configuration")
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    max_concurrent: int = Field(default=1, ge=1)
    priority: int = Field(default=0)
    is_default: bool = False


class ServerUpdate(BaseModel):
    """Request model for updating server"""
    name: Optional[str] = None
    url: Optional[str] = None
    api_version: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[dict] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    max_concurrent: Optional[int] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ServerResponse(BaseModel):
    """Response model for server"""
    id: str
    name: str
    url: str
    api_version: str
    is_active: bool
    is_default: bool
    is_available: bool
    description: Optional[str]
    capabilities: Optional[List[str]]
    max_concurrent: int
    priority: int
    created_at: datetime
    updated_at: datetime
    last_checked_at: Optional[datetime]
    models_count: int = 0


@router.get("/", response_model=List[ServerResponse])
async def list_servers(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all Ollama servers"""
    query = db.query(OllamaServer)
    if active_only:
        query = query.filter(OllamaServer.is_active == True)
    
    servers = query.order_by(OllamaServer.priority.desc(), OllamaServer.name).all()
    
    result = []
    for server in servers:
        models_count = db.query(OllamaModel).filter(
            OllamaModel.server_id == server.id,
            OllamaModel.is_active == True
        ).count()
        
        result.append(ServerResponse(
            id=str(server.id),
            name=server.name,
            url=server.url,
            api_version=server.api_version,
            is_active=server.is_active,
            is_default=server.is_default,
            is_available=server.is_available,
            description=server.description,
            capabilities=server.capabilities,
            max_concurrent=server.max_concurrent,
            priority=server.priority,
            created_at=server.created_at,
            updated_at=server.updated_at,
            last_checked_at=server.last_checked_at,
            models_count=models_count
        ))
    
    return result


@router.post("/", response_model=ServerResponse)
async def create_server(
    server_data: ServerCreate,
    db: Session = Depends(get_db)
):
    """Create a new Ollama server"""
    # Check if URL already exists
    existing = db.query(OllamaServer).filter(OllamaServer.url == server_data.url).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Server with URL {server_data.url} already exists")
    
    # Check if name already exists
    existing_name = db.query(OllamaServer).filter(OllamaServer.name == server_data.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail=f"Server with name {server_data.name} already exists")
    
    # If this is set as default, unset other defaults
    if server_data.is_default:
        db.query(OllamaServer).update({"is_default": False})
    
    server = OllamaServer(
        name=server_data.name,
        url=server_data.url,
        api_version=server_data.api_version,
        auth_type=server_data.auth_type,
        auth_config=server_data.auth_config,
        description=server_data.description,
        capabilities=server_data.capabilities,
        max_concurrent=server_data.max_concurrent,
        priority=server_data.priority,
        is_default=server_data.is_default,
        is_active=True
    )
    
    db.add(server)
    db.commit()
    db.refresh(server)
    
    # Try to discover models on this server
    try:
        await discover_server_models(server.id, db)
    except Exception as e:
        # Log error but don't fail creation
        logger.warning(
            "Could not discover models for server",
            exc_info=True,
            extra={
                "server_id": str(server.id),
                "server_name": server.name,
                "error": str(e),
            }
        )
    
    return ServerResponse(
        id=str(server.id),
        name=server.name,
        url=server.url,
        api_version=server.api_version,
        is_active=server.is_active,
        is_default=server.is_default,
        is_available=server.is_available,
        description=server.description,
        capabilities=server.capabilities,
        max_concurrent=server.max_concurrent,
        priority=server.priority,
        created_at=server.created_at,
        updated_at=server.updated_at,
        last_checked_at=server.last_checked_at,
        models_count=0
    )


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(server_id: str, db: Session = Depends(get_db)):
    """Get server by ID"""
    server = db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    models_count = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.is_active == True
    ).count()
    
    return ServerResponse(
        id=str(server.id),
        name=server.name,
        url=server.url,
        api_version=server.api_version,
        is_active=server.is_active,
        is_default=server.is_default,
        is_available=server.is_available,
        description=server.description,
        capabilities=server.capabilities,
        max_concurrent=server.max_concurrent,
        priority=server.priority,
        created_at=server.created_at,
        updated_at=server.updated_at,
        last_checked_at=server.last_checked_at,
        models_count=models_count
    )


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str,
    server_data: ServerUpdate,
    db: Session = Depends(get_db)
):
    """Update server"""
    server = db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Update fields
    update_data = server_data.model_dump(exclude_unset=True)
    
    # If setting as default, unset other defaults
    if update_data.get("is_default") is True:
        db.query(OllamaServer).filter(OllamaServer.id != server_id).update({"is_default": False})
    
    for key, value in update_data.items():
        setattr(server, key, value)
    
    server.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(server)
    
    models_count = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.is_active == True
    ).count()
    
    return ServerResponse(
        id=str(server.id),
        name=server.name,
        url=server.url,
        api_version=server.api_version,
        is_active=server.is_active,
        is_default=server.is_default,
        is_available=server.is_available,
        description=server.description,
        capabilities=server.capabilities,
        max_concurrent=server.max_concurrent,
        priority=server.priority,
        created_at=server.created_at,
        updated_at=server.updated_at,
        last_checked_at=server.last_checked_at,
        models_count=models_count
    )


@router.delete("/{server_id}")
async def delete_server(server_id: str, db: Session = Depends(get_db)):
    """Delete server and all its models"""
    server = db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    db.delete(server)
    db.commit()
    return {"message": "Server deleted successfully"}


@router.post("/{server_id}/discover", response_model=dict)
async def discover_server_models(server_id: str, db: Session = Depends(get_db)):
    """Discover and sync models from Ollama server"""
    server = db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Get base URL for API calls
    base_url = server.url.rstrip("/")
    
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            # Get models from server
            response = await client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Update server availability
            server.is_available = True
            server.last_checked_at = datetime.utcnow()
            
            # Get existing models for this server
            existing_models = {
                model.model_name: model 
                for model in db.query(OllamaModel).filter(OllamaModel.server_id == server.id).all()
            }
            
            seen_model_names = set()
            
            # Sync models
            for model_data in data.get("models", []):
                model_name = model_data.get("name", "")
                if not model_name:
                    continue
                
                seen_model_names.add(model_name)
                
                if model_name in existing_models:
                    # Update existing model
                    model = existing_models[model_name]
                    model.size_bytes = model_data.get("size", 0)
                    model.digest = model_data.get("digest", "")
                    model.modified_at = datetime.fromisoformat(model_data.get("modified_at", "").replace("Z", "+00:00")) if model_data.get("modified_at") else None
                    model.details = model_data
                    model.last_seen_at = datetime.utcnow()
                    model.is_active = True
                else:
                    # Create new model
                    model = OllamaModel(
                        server_id=server.id,
                        name=model_name,
                        model_name=model_name,
                        size_bytes=model_data.get("size", 0),
                        digest=model_data.get("digest", ""),
                        modified_at=datetime.fromisoformat(model_data.get("modified_at", "").replace("Z", "+00:00")) if model_data.get("modified_at") else None,
                        details=model_data,
                        last_seen_at=datetime.utcnow(),
                        is_active=True
                    )
                    db.add(model)
            
            # Deactivate models that are no longer on server
            for model_name, model in existing_models.items():
                if model_name not in seen_model_names:
                    model.is_active = False
            
            db.commit()
            
            return {
                "message": "Models discovered successfully",
                "models_found": len(seen_model_names),
                "models_added": len(seen_model_names) - len(existing_models)
            }
    
    except Exception as e:
        server.is_available = False
        server.last_checked_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error discovering models: {str(e)}")


@router.get("/{server_id}/models", response_model=List[dict])
async def get_server_models(server_id: str, db: Session = Depends(get_db)):
    """Get all models for a server"""
    server = db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    models = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.is_active == True
    ).order_by(OllamaModel.name).all()
    
    return [
        {
            "id": str(model.id),
            "name": model.name,
            "model_name": model.model_name,
            "size_bytes": model.size_bytes,
            "digest": model.digest,
            "modified_at": model.modified_at.isoformat() if model.modified_at else None,
            "capabilities": model.capabilities,
            "is_active": model.is_active
        }
        for model in models
    ]

