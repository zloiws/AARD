"""
Service for managing Ollama servers and models in database
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.ollama_server import OllamaServer
from app.models.ollama_model import OllamaModel
from app.core.ollama_client import OllamaInstanceConfig


class OllamaService:
    """Service for managing Ollama servers and models"""
    
    @staticmethod
    def get_all_active_servers(db: Session) -> List[OllamaServer]:
        """Get all active Ollama servers from database"""
        return db.query(OllamaServer).filter(OllamaServer.is_active == True).order_by(
            OllamaServer.priority.desc(),
            OllamaServer.name
        ).all()
    
    @staticmethod
    def get_server_by_url(db: Session, url: str) -> Optional[OllamaServer]:
        """Get server by URL"""
        return db.query(OllamaServer).filter(OllamaServer.url == url).first()
    
    @staticmethod
    def get_server_by_id(db: Session, server_id: str) -> Optional[OllamaServer]:
        """Get server by ID"""
        return db.query(OllamaServer).filter(OllamaServer.id == server_id).first()
    
    @staticmethod
    def get_default_server(db: Session) -> Optional[OllamaServer]:
        """Get default server"""
        return db.query(OllamaServer).filter(
            and_(OllamaServer.is_default == True, OllamaServer.is_active == True)
        ).first()
    
    @staticmethod
    def get_models_for_server(db: Session, server_id: str) -> List[OllamaModel]:
        """Get all active models for a server"""
        return db.query(OllamaModel).filter(
            and_(
                OllamaModel.server_id == server_id,
                OllamaModel.is_active == True
            )
        ).order_by(OllamaModel.priority.desc(), OllamaModel.name).all()
    
    @staticmethod
    def get_model_by_name(db: Session, server_id: str, model_name: str) -> Optional[OllamaModel]:
        """Get model by name and server"""
        return db.query(OllamaModel).filter(
            and_(
                OllamaModel.server_id == server_id,
                OllamaModel.model_name == model_name,
                OllamaModel.is_active == True
            )
        ).first()
    
    @staticmethod
    def convert_to_instance_config(server: OllamaServer) -> OllamaInstanceConfig:
        """Convert database model to OllamaInstanceConfig"""
        api_url = server.get_api_url()
        default_model = server.server_metadata.get("default_model", "") if server.server_metadata else ""
        
        return OllamaInstanceConfig(
            url=api_url,
            model=default_model,  # Will be overridden when model is selected
            capabilities=server.capabilities or [],
            max_concurrent=server.max_concurrent or 1
        )
    
    @staticmethod
    def convert_servers_to_instances(db: Session) -> List[OllamaInstanceConfig]:
        """Convert all active servers to instance configs"""
        servers = OllamaService.get_all_active_servers(db)
        instances = []
        
        for server in servers:
            if server.is_available or True:  # TODO: check health
                instance = OllamaService.convert_to_instance_config(server)
                instances.append(instance)
        
        return instances

