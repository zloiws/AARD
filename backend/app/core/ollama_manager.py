"""
Ollama Manager - loads instances from database instead of .env
"""
from typing import List, Optional

from app.core.ollama_client import OllamaError, OllamaInstanceConfig
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from app.services.ollama_service import OllamaService
from sqlalchemy.orm import Session


class OllamaManager:
    """Manager for Ollama instances loaded from database"""
    
    def __init__(self, db: Session):
        self.db = db
        self._instances: Optional[List[OllamaInstanceConfig]] = None
    
    def get_instances(self) -> List[OllamaInstanceConfig]:
        """Get all active Ollama instances from database"""
        if self._instances is None:
            self._instances = OllamaService.convert_servers_to_instances(self.db)
        return self._instances
    
    def get_instance_by_url(self, url: str) -> Optional[OllamaInstanceConfig]:
        """Get instance by URL"""
        # Normalize URL for comparison
        normalized_url = self._normalize_url(url)
        
        servers = OllamaService.get_all_active_servers(self.db)
        for server in servers:
            if self._normalize_url(server.get_api_url()) == normalized_url:
                return OllamaService.convert_to_instance_config(server)
        return None
    
    def get_instance_by_model_name(self, model_name: str, server_url: Optional[str] = None) -> Optional[OllamaInstanceConfig]:
        """Get instance by model name"""
        if server_url:
            # Get server by URL first
            server = OllamaService.get_server_by_url(self.db, server_url)
            if server:
                # Check if model exists on this server
                model = OllamaService.get_model_by_name(self.db, str(server.id), model_name)
                if model:
                    instance = OllamaService.convert_to_instance_config(server)
                    return instance
        
        # Search across all servers
        servers = OllamaService.get_all_active_servers(self.db)
        for server in servers:
            model = OllamaService.get_model_by_name(self.db, str(server.id), model_name)
            if model:
                return OllamaService.convert_to_instance_config(server)
        
        return None
    
    def create_dynamic_instance(self, server_url: str, model_name: str) -> OllamaInstanceConfig:
        """Create dynamic instance for servers not in database"""
        normalized_url = self._normalize_url(server_url)
        if not normalized_url.endswith("/v1"):
            if normalized_url.endswith("/v1/"):
                normalized_url = normalized_url.rstrip("/")
            else:
                normalized_url = normalized_url.rstrip("/") + "/v1"
        
        return OllamaInstanceConfig(
            url=normalized_url,
            model=model_name,
            capabilities=[],
            max_concurrent=1
        )
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = f"http://{url}"
        if not url.endswith("/v1"):
            if not url.endswith("/v1/"):
                url = url + "/v1"
        return url
    
    def reload(self):
        """Reload instances from database"""
        self._instances = None

