"""
Model Selector for Dual-Model Architecture
Separates planning models (reasoning) from code generation models
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from app.services.ollama_service import OllamaService

logger = LoggingConfig.get_logger(__name__)


class ModelSelector:
    """
    Selector for specialized models based on dual-model architecture:
    - Planning models: for reasoning, strategy, task decomposition
    - Code models: for code generation and execution
    """
    
    # Capabilities for planning models (model "Размышлений")
    PLANNING_MODEL_CAPABILITIES = ["planning", "reasoning", "strategy"]
    
    # Capabilities for code models (model "Кода")
    CODE_MODEL_CAPABILITIES = ["code_generation", "code_analysis", "code"]
    
    def __init__(self, db: Session = None):
        """
        Initialize Model Selector
        
        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or SessionLocal()
    
    def _filter_embedding_models(self, models: List[OllamaModel]) -> List[OllamaModel]:
        """
        Filter out embedding models (they don't support chat API)
        
        Args:
            models: List of OllamaModel instances
            
        Returns:
            Filtered list without embedding models
        """
        return [
            m for m in models 
            if m.model_name and not ("embedding" in m.model_name.lower() or "embed" in m.model_name.lower())
        ]
    
    def get_planning_model(
        self,
        server: Optional[OllamaServer] = None
    ) -> Optional[OllamaModel]:
        """
        Get model for planning tasks (model "Размышлений")
        
        Looks for models with planning/reasoning capabilities.
        Prefers models with "planning" capability, falls back to "reasoning".
        
        Args:
            server: Optional specific server to search on
            
        Returns:
            OllamaModel with planning capabilities or None
        """
        try:
            if server:
                models = OllamaService.get_models_for_server(self.db, str(server.id))
            else:
                # Get default server or first active server
                server = OllamaService.get_default_server(self.db)
                if not server:
                    servers = OllamaService.get_all_active_servers(self.db)
                    if servers:
                        server = servers[0]
                    else:
                        logger.warning("No active servers found")
                        return None
                
                models = OllamaService.get_models_for_server(self.db, str(server.id))
            
            if not models:
                logger.warning(f"No models found for server {server.name if server else 'unknown'}")
                return None
            
            # Filter out embedding models (they don't support chat API)
            models = self._filter_embedding_models(models)
            if not models:
                logger.warning("No non-embedding models found for planning")
                return None
            
            # First, try to find model with "planning" capability
            for capability in ["planning", "reasoning", "strategy"]:
                for model in models:
                    if model.capabilities and isinstance(model.capabilities, list):
                        if capability in [c.lower() for c in model.capabilities]:
                            logger.info(
                                f"Selected planning model: {model.name} (capability: {capability})",
                                extra={
                                    "model_id": str(model.id),
                                    "model_name": model.name,
                                    "capability": capability,
                                    "server_id": str(server.id) if server else None
                                }
                            )
                            return model
            
            # Fallback: return first active model
            if models:
                logger.warning(
                    f"No planning-capable model found, using fallback: {models[0].name}",
                    extra={
                        "model_id": str(models[0].id),
                        "model_name": models[0].name
                    }
                )
                return models[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting planning model: {e}", exc_info=True)
            return None
    
    def get_code_model(
        self,
        server: Optional[OllamaServer] = None
    ) -> Optional[OllamaModel]:
        """
        Get model for code generation tasks (model "Кода")
        
        Looks for models with code generation capabilities.
        Prefers models with "code_generation" capability.
        
        Args:
            server: Optional specific server to search on
            
        Returns:
            OllamaModel with code generation capabilities or None
        """
        try:
            if server:
                models = OllamaService.get_models_for_server(self.db, str(server.id))
            else:
                # Get default server or first active server
                server = OllamaService.get_default_server(self.db)
                if not server:
                    servers = OllamaService.get_all_active_servers(self.db)
                    if servers:
                        server = servers[0]
                    else:
                        logger.warning("No active servers found")
                        return None
                
                models = OllamaService.get_models_for_server(self.db, str(server.id))
            
            if not models:
                logger.warning(f"No models found for server {server.name if server else 'unknown'}")
                return None
            
            # Filter out embedding models (they don't support chat API)
            models = self._filter_embedding_models(models)
            if not models:
                logger.warning("No non-embedding models found for code generation")
                return None
            
            # First, try to find model with code generation capabilities
            for capability in ["code_generation", "code_analysis", "code"]:
                for model in models:
                    if model.capabilities and isinstance(model.capabilities, list):
                        if capability in [c.lower() for c in model.capabilities]:
                            logger.info(
                                f"Selected code model: {model.name} (capability: {capability})",
                                extra={
                                    "model_id": str(model.id),
                                    "model_name": model.name,
                                    "capability": capability,
                                    "server_id": str(server.id) if server else None
                                }
                            )
                            return model
            
            # Fallback: return first active model
            if models:
                logger.warning(
                    f"No code-capable model found, using fallback: {models[0].name}",
                    extra={
                        "model_id": str(models[0].id),
                        "model_name": models[0].name
                    }
                )
                return models[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting code model: {e}", exc_info=True)
            return None
    
    def get_model_by_capability(
        self,
        capability: str,
        server: Optional[OllamaServer] = None
    ) -> Optional[OllamaModel]:
        """
        Get model by specific capability
        
        Args:
            capability: Required capability (e.g., "planning", "code_generation", "reasoning")
            server: Optional specific server to search on
            
        Returns:
            OllamaModel with the specified capability or None
        """
        try:
            if server:
                models = OllamaService.get_models_for_server(self.db, str(server.id))
            else:
                # Get default server or first active server
                server = OllamaService.get_default_server(self.db)
                if not server:
                    servers = OllamaService.get_all_active_servers(self.db)
                    if servers:
                        server = servers[0]
                    else:
                        logger.warning("No active servers found")
                        return None
                
                models = OllamaService.get_models_for_server(self.db, str(server.id))
            
            if not models:
                logger.warning(f"No models found for server {server.name if server else 'unknown'}")
                return None
            
            # Filter out embedding models (they don't support chat API)
            models = self._filter_embedding_models(models)
            if not models:
                logger.warning("No non-embedding models found")
                return None
            
            capability_lower = capability.lower()
            
            # Find model with the specified capability
            for model in models:
                if model.capabilities and isinstance(model.capabilities, list):
                    if capability_lower in [c.lower() for c in model.capabilities]:
                        logger.info(
                            f"Selected model by capability: {model.name} (capability: {capability})",
                            extra={
                                "model_id": str(model.id),
                                "model_name": model.name,
                                "capability": capability,
                                "server_id": str(server.id) if server else None
                            }
                        )
                        return model
            
            # Fallback: return first active model
            if models:
                logger.warning(
                    f"No model with capability '{capability}' found, using fallback: {models[0].name}",
                    extra={
                        "model_id": str(models[0].id),
                        "model_name": models[0].name,
                        "requested_capability": capability
                    }
                )
                return models[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting model by capability '{capability}': {e}", exc_info=True)
            return None
    
    def get_server_for_model(self, model: OllamaModel) -> Optional[OllamaServer]:
        """
        Get server for a given model
        
        Args:
            model: OllamaModel instance
            
        Returns:
            OllamaServer instance or None
        """
        try:
            return OllamaService.get_server_by_id(self.db, str(model.server_id))
        except Exception as e:
            logger.error(f"Error getting server for model: {e}", exc_info=True)
            return None

