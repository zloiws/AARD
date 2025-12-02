"""
Ollama client that loads instances from database
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.ollama_client import OllamaClient, OllamaInstanceConfig
from app.services.ollama_service import OllamaService


class OllamaDBClient:
    """
    Wrapper around OllamaClient that loads instances from database
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._client: Optional[OllamaClient] = None
    
    @property
    def client(self) -> OllamaClient:
        """Get OllamaClient instance (creates if not exists)"""
        if self._client is None:
            self._client = OllamaClient()
        return self._client
    
    def get_instances(self) -> List[OllamaInstanceConfig]:
        """Get instances from database"""
        return OllamaService.convert_servers_to_instances(self.db)
    
    def get_instance_by_url(self, url: str) -> Optional[OllamaInstanceConfig]:
        """Get instance from database by URL"""
        server = OllamaService.get_server_by_url(self.db, url)
        if server:
            return OllamaService.convert_to_instance_config(server)
        return None
    
    def get_instance_by_model_name(self, model_name: str, server_url: Optional[str] = None) -> Optional[OllamaInstanceConfig]:
        """Get instance from database by model name"""
        if server_url:
            server = OllamaService.get_server_by_url(self.db, server_url)
            if server:
                model = OllamaService.get_model_by_name(self.db, str(server.id), model_name)
                if model:
                    return OllamaService.convert_to_instance_config(server)
        
        # Search across all servers
        servers = OllamaService.get_all_active_servers(self.db)
        for server in servers:
            model = OllamaService.get_model_by_name(self.db, str(server.id), model_name)
            if model:
                return OllamaService.convert_to_instance_config(server)
        
        return None
    
    async def generate(self, *args, **kwargs):
        """Delegate to OllamaClient.generate"""
        return await self.client.generate(*args, **kwargs)
    
    async def generate_stream(self, *args, **kwargs):
        """Delegate to OllamaClient.generate_stream"""
        return self.client.generate_stream(*args, **kwargs)
    
    async def health_check(self, instance: OllamaInstanceConfig) -> bool:
        """Delegate to OllamaClient.health_check"""
        return await self.client.health_check(instance)


def get_ollama_db_client(db: Session) -> OllamaDBClient:
    """Get OllamaDBClient instance with database session"""
    return OllamaDBClient(db)

