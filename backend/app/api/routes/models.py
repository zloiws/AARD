"""
API routes for model management
Now uses servers from database instead of .env
"""
from typing import Dict, List, Optional

import httpx
from app.core.database import get_db
from app.core.ollama_client import OllamaClient, get_ollama_client
from app.models.ollama_server import OllamaServer
from app.services.ollama_service import OllamaService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelInfo(BaseModel):
    """Model information"""
    name: str
    model: str
    size: int
    digest: str
    modified_at: str


class ServerInfo(BaseModel):
    """Server information with available models"""
    id: str
    name: str
    url: str
    api_url: str
    version: Optional[str] = None
    models: List[ModelInfo] = []
    available: bool = False
    is_default: bool = False


@router.get("/servers")
async def list_servers(db: Session = Depends(get_db)):
    """Get list of Ollama servers from database with their available models"""
    servers_list = OllamaService.get_all_active_servers(db)
    servers = []
    
    for server in servers_list:
        server_info = ServerInfo(
            id=str(server.id),
            name=server.name,
            url=server.url,
            api_url=server.get_api_url(),
            available=False,
            is_default=server.is_default,
            models=[]
        )
        
        try:
            # Get base URL (remove /v1 if present)
            base_url = server.url.rstrip("/")
            
            async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as http_client:
                # Get version
                try:
                    version_resp = await http_client.get("/api/version", timeout=5.0)
                    if version_resp.status_code == 200:
                        version_data = version_resp.json()
                        server_info.version = version_data.get("version")
                except:
                    pass
                
                # Get available models
                try:
                    tags_resp = await http_client.get("/api/tags", timeout=10.0)
                    if tags_resp.status_code == 200:
                        tags_data = tags_resp.json()
                        server_info.available = True
                        
                        for model_data in tags_data.get("models", []):
                            server_info.models.append(ModelInfo(
                                name=model_data.get("name", ""),
                                model=model_data.get("model", ""),
                                size=model_data.get("size", 0),
                                digest=model_data.get("digest", ""),
                                modified_at=model_data.get("modified_at", "")
                            ))
                except:
                    pass
        
        except Exception as e:
            pass  # Server unavailable
        
        servers.append(server_info)
    
    return {"servers": servers}


@router.get("/server/models")
async def get_server_models(server_url: str = Query(..., description="Ollama server URL")):
    """Get models from a specific server by URL"""
    try:
        # Ensure URL is properly formatted
        if not server_url.startswith("http"):
            server_url = f"http://{server_url}"
        
        # Remove /v1 if present for API calls
        base_url = server_url
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        elif base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            response = await client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model_data in data.get("models", []):
                models.append(ModelInfo(
                    name=model_data.get("name", ""),
                    model=model_data.get("model", ""),
                    size=model_data.get("size", 0),
                    digest=model_data.get("digest", ""),
                    modified_at=model_data.get("modified_at", "")
                ))
            
            # Get version info
            version = None
            try:
                version_resp = await client.get("/api/version", timeout=5.0)
                if version_resp.status_code == 200:
                    version_data = version_resp.json()
                    version = version_data.get("version")
            except:
                pass
            
            return {
                "server": server_url,
                "version": version,
                "models": models
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models from server: {str(e)}")


@router.post("/server")
async def add_server(server_url: str, client: OllamaClient = Depends(get_ollama_client)):
    """Add a new Ollama server (for future use with dynamic server management)"""
    # This is a placeholder for future dynamic server management
    # For now, servers are configured via .env
    return {"message": "Dynamic server management not yet implemented. Use .env configuration."}

