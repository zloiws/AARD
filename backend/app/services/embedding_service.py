"""
Service for generating text embeddings for vector search
"""
from typing import List, Optional, Dict, Any
import asyncio
import json
import httpx
from functools import lru_cache

from app.core.logging_config import LoggingConfig
from app.core.config import get_settings
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
    DEFAULT_EMBEDDING_DIM = 1536
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.ollama_service = OllamaService(db)
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
            
            # Cache the result
            if use_cache:
                self._cache_embedding(text, normalized)
            
            logger.debug(f"Generated embedding for text: {text[:50]}... (dim={len(normalized)})")
            return normalized
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            # Return zero vector on error
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
        For now, we'll use a general model that supports embeddings.
        In the future, this can be configured via settings.
        """
        # Try to get a model that supports embeddings
        # Most Ollama models can generate embeddings via their API
        servers = self.ollama_service.get_all_active_servers(self.db)
        if servers:
            # Use the default server's first available model
            # In practice, you might want to use a specific embedding model
            return "nomic-embed-text"  # Common embedding model for Ollama
        else:
            # Fallback
            return "nomic-embed-text"
    
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
        servers = self.ollama_service.get_all_active_servers(self.db)
        if not servers:
            raise ValueError("No Ollama servers available")
        
        # Use first available server
        server = servers[0]
        base_url = server.url.rstrip("/")
        
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
            # Zero vector - return as is
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

