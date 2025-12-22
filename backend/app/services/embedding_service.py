"""
Service for generating text embeddings for vector search
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.models.ollama_server import OllamaServer

import asyncio
import json
from functools import lru_cache

import httpx
from app.core.config import get_settings
from app.core.logging_config import LoggingConfig
from app.services.ollama_service import OllamaService
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using LLM models via Ollama.
    
    Supports:
    - Text embedding generation
    - Embedding caching
    - Vector normalization
    - Batch processing
    """
    
    # Default embedding dimension (can be adjusted based on model)
    # Note: Different models have different dimensions (e.g., 768, 1536)
    DEFAULT_EMBEDDING_DIM = 1536  # Default, but actual dimension depends on model
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.ollama_service = OllamaService()  # OllamaService is static
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_size_limit = 1000  # Limit cache size
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for given text.
        
        Args:
            text: Text to generate embedding for
            model: Optional model name (uses default if not provided)
            use_cache: Whether to use cached embeddings
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            # Return zero vector matching DEFAULT_EMBEDDING_DIM
            return [0.0] * self.DEFAULT_EMBEDDING_DIM
        
        # Check cache first
        if use_cache and text in self._embedding_cache:
            logger.debug(f"Using cached embedding for text: {text[:50]}...")
            return self._embedding_cache[text]
        
        try:
            # Get default model if not provided
            if not model:
                model = self._get_default_embedding_model()
            
            # Generate embedding via Ollama
            embedding = await self._generate_embedding_via_ollama(text, model)
            
            # Normalize embedding
            normalized = self._normalize_vector(embedding)
            # Ensure embedding dimension matches expected DEFAULT_EMBEDDING_DIM
            if len(normalized) != self.DEFAULT_EMBEDDING_DIM:
                if len(normalized) < self.DEFAULT_EMBEDDING_DIM:
                    # pad with zeros
                    normalized = normalized + [0.0] * (self.DEFAULT_EMBEDDING_DIM - len(normalized))
                else:
                    # truncate
                    normalized = normalized[: self.DEFAULT_EMBEDDING_DIM]
            
            # Cache the result
            if use_cache:
                self._cache_embedding(text, normalized)
            
            logger.debug(f"Generated embedding for text: {text[:50]}... (dim={len(normalized)})")
            return normalized
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            # Return zero vector with default embedding dimension on error
            return [0.0] * self.DEFAULT_EMBEDDING_DIM
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to generate embeddings for
            model: Optional model name
            use_cache: Whether to use cached embeddings
            
        Returns:
            List of embedding vectors
        """
        results = []
        
        for text in texts:
            embedding = await self.generate_embedding(text, model, use_cache)
            results.append(embedding)
        
        return results
    
    def _get_default_embedding_model(self) -> str:
        """
        Get default embedding model.
        Uses nomic-embed-text if available, otherwise falls back to any available model.
        """
        return "nomic-embed-text"  # Common embedding model for Ollama
    
    async def _find_server_with_model(self, model_name: str) -> Optional[Any]:
        """
        Find a server that has the specified model available.
        
        Args:
            model_name: Name of the model to find
            
        Returns:
            OllamaServer instance if found, None otherwise
        """
        import httpx
        
        servers = self.ollama_service.get_all_active_servers(self.db)
        if not servers:
            return None
        
        # Try to find a server with the model
        for server in servers:
            try:
                base_url = server.url.rstrip("/")
                if base_url.endswith("/v1"):
                    base_url = base_url[:-3]
                
                async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
                    # Check if model is available on this server
                    response = await client.get("/api/tags", timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        models = data.get("models", [])
                        for model_data in models:
                            # Check both 'name' and 'model' fields
                            model_full_name = model_data.get("name", "") or model_data.get("model", "")
                            if model_name in model_full_name:
                                logger.debug(f"Found model {model_name} on server {server.name} ({server.url})")
                                return server
            except Exception as e:
                logger.debug(f"Error checking server {server.name} for model {model_name}: {e}")
                continue
        
        # If not found, return first available server (will try to use model anyway)
        logger.warning(f"Model {model_name} not found on any server, using first available server")
        return servers[0] if servers else None
    
    async def _generate_embedding_via_ollama(
        self,
        text: str,
        model: str
    ) -> List[float]:
        """
        Generate embedding using Ollama API.
        
        Note: Ollama's embedding API might differ from chat API.
        This is a basic implementation that can be extended.
        """
        # Find a server that has the model
        server = await self._find_server_with_model(model)
        if not server:
            raise ValueError("No Ollama servers available")
        
        base_url = server.url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        
        # Ollama embedding endpoint
        # Note: This might need adjustment based on your Ollama version
        embed_url = f"{base_url}/api/embeddings"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    embed_url,
                    json={
                        "model": model,
                        "prompt": text
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding", [])
                    
                    if not embedding:
                        raise ValueError(f"No embedding returned from model {model}")
                    
                    return embedding
                else:
                    raise ValueError(f"Ollama API error: {response.status_code} - {response.text}")
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout generating embedding for model {model}")
            raise
        except Exception as e:
            logger.error(f"Error calling Ollama embedding API: {e}")
            raise
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """
        Normalize vector to unit length (L2 normalization).
        This is important for cosine similarity calculations.
        """
        if not vector:
            return [0.0] * self.DEFAULT_EMBEDDING_DIM
        
        # Calculate L2 norm
        norm = sum(x * x for x in vector) ** 0.5
        
        if norm == 0:
            # Zero vector - return the original vector (preserve dimension).
            # Upstream callers (generate_embedding) will pad/truncate to DEFAULT_EMBEDDING_DIM as needed.
            return vector
        
        # Normalize
        normalized = [x / norm for x in vector]
        return normalized
    
    def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding result"""
        # Simple LRU-style cache management
        if len(self._embedding_cache) >= self._cache_size_limit:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]
        
        self._embedding_cache[text] = embedding
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        logger.debug("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self._embedding_cache),
            "cache_limit": self._cache_size_limit,
            "cache_usage_percent": (len(self._embedding_cache) / self._cache_size_limit) * 100
        }
    
    def cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        Assumes vectors are already normalized.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")
        
        # Dot product (since vectors are normalized, this equals cosine similarity)
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Clamp to [-1, 1] range (shouldn't happen with normalized vectors, but safety check)
        return max(-1.0, min(1.0, dot_product))

