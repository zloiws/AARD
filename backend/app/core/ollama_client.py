"""
Ollama API client with support for multiple instances and model selection
"""
import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

from app.core.config import get_settings, OllamaInstanceConfig


class TaskType(str, Enum):
    """Task type enumeration"""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REASONING = "reasoning"
    GENERAL_CHAT = "general_chat"
    PLANNING = "planning"
    TEXT_GENERATION = "text_generation"
    DEFAULT = "general_chat"


class OllamaResponse(BaseModel):
    """Ollama API response model"""
    model: str
    response: str
    done: bool = False


class OllamaError(Exception):
    """Custom exception for Ollama errors"""
    pass


class CacheEntry(BaseModel):
    """Cache entry for LLM responses"""
    response: str
    timestamp: datetime
    model: str



class OllamaClient:
    """
    Client for interacting with Ollama API
    Supports multiple instances with load balancing and caching
    """
    
    def __init__(self):
        # Lazy load settings to avoid issues with module-level initialization
        self._settings = None
        self._instances: Optional[List[OllamaInstanceConfig]] = None
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl = timedelta(hours=24)
        self._client: Optional[httpx.AsyncClient] = None
        self._instance_clients: Dict[str, httpx.AsyncClient] = {}
        
        self._task_type_mapping: Optional[Dict[TaskType, Optional[OllamaInstanceConfig]]] = None
    
    @property
    def settings(self):
        """Lazy load settings"""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings
    
    @property
    def instances(self) -> List[OllamaInstanceConfig]:
        """Lazy load instances"""
        if self._instances is None:
            self._instances = [
                self.settings.ollama_instance_1,
                self.settings.ollama_instance_2,
            ]
        return self._instances
    
    @property
    def task_type_mapping(self) -> Dict[TaskType, Optional[OllamaInstanceConfig]]:
        """Map task types to instances"""
        if self._task_type_mapping is None:
            mapping = {}
            for task_type in TaskType:
                mapping[task_type] = self._select_instance_for_task_type(task_type)
            self._task_type_mapping = mapping
        return self._task_type_mapping
    
    def _select_instance_for_task_type(self, task_type: TaskType) -> Optional[OllamaInstanceConfig]:
        """Select instance based on task type"""
        if task_type in [TaskType.CODE_GENERATION, TaskType.CODE_ANALYSIS]:
            # Look for coding-capable instance
            for inst in self.instances:
                if "code" in [cap.lower() for cap in inst.capabilities]:
                    return inst
        elif task_type in [TaskType.REASONING, TaskType.PLANNING]:
            # Look for reasoning-capable instance
            for inst in self.instances:
                if "reasoning" in [cap.lower() for cap in inst.capabilities]:
                    return inst
        
        # Default to first instance
        return self.instances[0] if self.instances else None
    
    def select_model_for_task(self, task_type: TaskType) -> Optional[OllamaInstanceConfig]:
        """Select appropriate model instance for task type"""
        instance = self.task_type_mapping.get(task_type)
        if instance is None:
            # Fallback to first instance
            if self.instances:
                return self.instances[0]
            raise OllamaError("No Ollama instances configured")
        
        return instance
    
    def _get_cache_key(self, prompt: str, model: str, **kwargs) -> str:
        """Generate cache key for prompt"""
        key_data = f"{prompt}:{model}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get response from cache if available and not expired"""
        if cache_key not in self.cache:
            return None
        
        entry = self.cache[cache_key]
        if datetime.utcnow() - entry.timestamp > self.cache_ttl:
            del self.cache[cache_key]
            return None
        
        return entry.response
    
    def _save_to_cache(self, cache_key: str, response: str, model: str, metadata: Optional[Dict] = None):
        """Save response to cache"""
        self.cache[cache_key] = CacheEntry(
            response=response,
            timestamp=datetime.utcnow(),
            model=model
        )
    
    async def _get_client(self, instance: OllamaInstanceConfig) -> httpx.AsyncClient:
        """Get or create HTTP client for instance"""
        client_key = instance.url
        if client_key not in self._instance_clients:
            # Remove /v1 from base URL for client
            base_url = instance.url
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            elif base_url.endswith("/v1/"):
                base_url = base_url[:-4]
            
            self._instance_clients[client_key] = httpx.AsyncClient(
                base_url=base_url,
                timeout=300.0,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                )
            )
        return self._instance_clients[client_key]
    
    async def health_check(self, instance: OllamaInstanceConfig) -> bool:
        """Check if Ollama instance is healthy"""
        try:
            # Ollama API endpoints are at base URL without /v1
            base_url = instance.url
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]  # Remove /v1
            elif base_url.endswith("/v1/"):
                base_url = base_url[:-4]  # Remove /v1/
            
            # Create a temporary client for health check
            async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
                # Use /api/tags endpoint (doesn't require model to be loaded)
                response = await client.get("/api/tags", timeout=5.0)
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return False
        except Exception:
            return False
    
    def _normalize_server_url(self, url: str) -> str:
        """Normalize server URL to standard format"""
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        if not url.endswith("/v1"):
            if url.endswith("/v1/"):
                url = url.rstrip("/")
            else:
                url = url.rstrip("/") + "/v1"
        return url
    
    def _create_dynamic_instance(self, server_url: str, model: str) -> OllamaInstanceConfig:
        """Create a dynamic instance config for servers not in .env"""
        normalized_url = self._normalize_server_url(server_url)
        return OllamaInstanceConfig(
            url=normalized_url,
            model=model,
            capabilities=[],
            max_concurrent=1
        )
    
    def _find_instance_by_url(self, server_url: str) -> Optional[OllamaInstanceConfig]:
        """Find configured instance by URL
        
        NOTE: This only searches in loaded instances (from .env).
        For database-backed servers, use OllamaService instead.
        """
        normalized_url = self._normalize_server_url(server_url)
        for inst in self.instances:
            if self._normalize_server_url(inst.url) == normalized_url:
                return inst
        return None
    
    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.DEFAULT,
        model: Optional[str] = None,
        server_url: Optional[str] = None,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
        **kwargs
    ) -> OllamaResponse:
        """
        Generate response using Ollama
        
        Args:
            prompt: Input prompt
            task_type: Type of task (for model selection)
            model: Specific model to use (overrides task_type selection)
            server_url: Specific server URL to use (overrides instance selection)
            system_prompt: System prompt for the model
            history: Chat history in Ollama format
            stream: Whether to stream response
            **kwargs: Additional parameters (temperature, top_p, etc.)
            
        Returns:
            OllamaResponse object
        """
        instance = None
        actual_model_name = None
        is_dynamic_instance = False  # Track if we created a dynamic instance
        
        # PRIORITY 1: If server_url is explicitly provided, use it
        # IMPORTANT: When server_url and model are provided, ALWAYS use them directly
        # Do NOT fallback to .env configuration
        if server_url:
            server_url = server_url.strip()
            
            # If model is also provided, create dynamic instance immediately
            # This ensures we use the exact model requested, not from .env
            if model:
                model = model.strip()
                instance = self._create_dynamic_instance(server_url, model)
                actual_model_name = model
                is_dynamic_instance = True
                print(f"[OllamaClient] Created dynamic instance: {server_url} / {model}")
            else:
                # Only server_url provided - this should not happen in new logic
                # But if it does, require model
                raise OllamaError(f"Model name required when using server {server_url}. Please specify model.")
        
        # PRIORITY 2: If model is specified but no server_url
        # This should not happen in new logic - server_url should always be provided
        # But keep for backward compatibility
        elif model:
            model = model.strip()
            print(f"[OllamaClient] WARNING: Model {model} specified but no server_url. This should not happen.")
            raise OllamaError(
                f"Server URL required when model is specified. "
                f"Please ensure server_id is provided in the request."
            )
        
        # PRIORITY 3: Auto-select based on task type
        # This should not happen in new logic - server_url and model should always be provided
        # But keep for backward compatibility
        else:
            print(f"[OllamaClient] WARNING: No server_url and no model specified. This should not happen.")
            raise OllamaError(
                "Server URL and model must be provided. "
                "Please ensure server_id and model are provided in the request, "
                "or use auto-selection which should be handled in chat.py."
            )
        
        # Ensure we have an instance
        if not instance:
            raise OllamaError("No suitable Ollama instance found")
        
        # Determine final model name
        model_to_use = actual_model_name if actual_model_name else instance.model
        
        # DEBUG: Log model selection
        print(f"[OllamaClient] DEBUG: actual_model_name={actual_model_name}, instance.model={instance.model}, model_to_use={model_to_use}")
        print(f"[OllamaClient] DEBUG: server_url={server_url}, is_dynamic_instance={is_dynamic_instance}")
        
        # Check cache
        cache_key = self._get_cache_key(prompt, model_to_use, **kwargs)
        cached_response = self._get_from_cache(cache_key)
        if cached_response:
            print(f"[OllamaClient] DEBUG: Using cached response for model={model_to_use}")
            return OllamaResponse(
                model=model_to_use,
                response=cached_response,
                done=True
            )
        
        # Health check (but don't fallback if server_url was explicitly provided)
        if not is_dynamic_instance:
            if not await self.health_check(instance):
                # Only fallback if server_url was not explicitly provided
                if not server_url:
                    # Try fallback to another instance
                    for fallback_instance in self.instances:
                        if fallback_instance != instance and await self.health_check(fallback_instance):
                            instance = fallback_instance
                            break
                    else:
                        raise OllamaError(f"Ollama instance {instance.url} is not available and no fallback found")
                else:
                    raise OllamaError(f"Ollama instance {instance.url} is not available")
        else:
            # For dynamic instances, always check health but don't fallback
            if not await self.health_check(instance):
                raise OllamaError(f"Ollama server {instance.url} is not available")
        
        # Prepare messages for chat API
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request
        payload = {
            "model": model_to_use,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "num_ctx": kwargs.get("num_ctx", 4096),
            }
        }
        
        # Prepare request URL (remove /v1 for API calls)
        request_base_url = instance.url
        if request_base_url.endswith("/v1"):
            request_base_url = request_base_url[:-3]
        elif request_base_url.endswith("/v1/"):
            request_base_url = request_base_url[:-4]
        
        # DEBUG: Log payload (after request_base_url is defined)
        print(f"[OllamaClient] DEBUG: Sending request to {request_base_url}/api/chat with model={model_to_use}")
        print(f"[OllamaClient] DEBUG: Payload model field: {payload['model']}")
        
        # Make request
        # Use longer timeout for planning tasks (10 minutes)
        timeout_value = 600.0 if task_type == TaskType.PLANNING else 300.0
        
        async with httpx.AsyncClient(
            base_url=request_base_url,
            timeout=timeout_value,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            )
        ) as request_client:
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    if task_type == TaskType.PLANNING:
                        print(f"[OllamaClient] INFO: Planning request, timeout={timeout_value}s, attempt {attempt+1}/{max_retries}")
                    
                    response = await request_client.post(
                        "/api/chat",
                        json=payload,
                        timeout=timeout_value
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Extract response from chat format
                    response_text = data.get("message", {}).get("content", "")
                    
                    # DEBUG: Check what model Ollama returned
                    ollama_returned_model = data.get("model")
                    if ollama_returned_model and ollama_returned_model != model_to_use:
                        print(f"[OllamaClient] WARNING: Ollama returned model '{ollama_returned_model}' but we requested '{model_to_use}'")
                        print(f"[OllamaClient] DEBUG: Using requested model '{model_to_use}' in response")
                    
                    # Save to cache
                    if data.get("done") and response_text:
                        self._save_to_cache(
                            cache_key,
                            response_text,
                            model_to_use,
                            metadata={"attempt": attempt + 1}
                        )
                    
                    # Always use model_to_use (the one we requested), not what Ollama returned
                    # This ensures consistency with what the user selected
                    return OllamaResponse(
                        model=model_to_use,
                        response=response_text,
                        done=data.get("done", False)
                    )
                    
                except httpx.TimeoutException:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise OllamaError(f"Request to {instance.url} timed out after {max_retries} attempts")
                except httpx.HTTPStatusError as e:
                    raise OllamaError(f"HTTP error from {instance.url}: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise OllamaError(f"Error calling Ollama at {instance.url}: {str(e)}")
            
            raise OllamaError(f"Failed to generate response after {max_retries} attempts")
    
    async def generate_stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.DEFAULT,
        model: Optional[str] = None,
        server_url: Optional[str] = None,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ):
        """
        Generate streaming response using Ollama
        
        Yields:
            OllamaResponse chunks
        """
        instance = None
        actual_model_name = None
        is_dynamic_instance = False
        
        # PRIORITY 1: If server_url is explicitly provided, use it
        if server_url:
            server_url = server_url.strip()
            normalized_url = self._normalize_server_url(server_url)
            
            # Try to find configured instance
            instance = self._find_instance_by_url(server_url)
            
            if instance:
                if model:
                    actual_model_name = model.strip()
                else:
                    actual_model_name = instance.model
            else:
                if not model:
                    raise OllamaError(f"Model name required when using server {server_url} not in configuration")
                instance = self._create_dynamic_instance(server_url, model)
                actual_model_name = model.strip()
                is_dynamic_instance = True
        
        # PRIORITY 2: If model is specified but no server_url
        elif model:
            model = model.strip()
            for inst in self.instances:
                if inst.model == model:
                    instance = inst
                    actual_model_name = model
                    break
            
            if not instance:
                model_base = model.split(':')[0] if ':' in model else model
                for inst in self.instances:
                    inst_model_base = inst.model.split(':')[0] if ':' in inst.model else inst.model
                    if inst_model_base == model_base:
                        instance = inst
                        actual_model_name = model
                        break
            
            if not instance:
                for inst in self.instances:
                    if await self.health_check(inst):
                        instance = inst
                        actual_model_name = model
                        break
                
                if not instance:
                    raise OllamaError(f"Model {model} not found and no available instances")
        
        # PRIORITY 3: Auto-select based on task type
        else:
            instance = self.select_model_for_task(task_type)
            if not instance:
                for inst in self.instances:
                    if await self.health_check(inst):
                        instance = inst
                        break
                if not instance:
                    raise OllamaError("No available Ollama instances found")
            actual_model_name = None
        
        if not instance:
            raise OllamaError("No suitable Ollama instance found")
        
        model_to_use = actual_model_name if actual_model_name else instance.model
        
        # Health check
        if not is_dynamic_instance:
            if not await self.health_check(instance):
                if not server_url:
                    for fallback_instance in self.instances:
                        if fallback_instance != instance and await self.health_check(fallback_instance):
                            instance = fallback_instance
                            break
                    else:
                        raise OllamaError(f"Ollama instance {instance.url} is not available")
                else:
                    raise OllamaError(f"Ollama instance {instance.url} is not available")
        else:
            if not await self.health_check(instance):
                raise OllamaError(f"Ollama server {instance.url} is not available")
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request URL
        request_base_url = instance.url
        if request_base_url.endswith("/v1"):
            request_base_url = request_base_url[:-3]
        elif request_base_url.endswith("/v1/"):
            request_base_url = request_base_url[:-4]
        
        # Create client and stream
        async with httpx.AsyncClient(
            base_url=request_base_url,
            timeout=300.0,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            )
        ) as request_client:
            payload = {
                "model": model_to_use,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                    "num_ctx": kwargs.get("num_ctx", 4096),
                }
            }
            
            async with request_client.stream("POST", "/api/chat", json=payload, timeout=300.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            # Extract content from chat format
                            content = data.get("message", {}).get("content", "")
                            yield OllamaResponse(
                                model=model_to_use,
                                response=content,
                                done=data.get("done", False)
                            )
                        except json.JSONDecodeError:
                            continue
    
    def get_instance_by_model_name(self, model_name: str) -> Optional[OllamaInstanceConfig]:
        """Get Ollama instance config by model name"""
        for instance in self.instances:
            if instance.model == model_name:
                return instance
        return None
    
    async def close(self):
        """Close all HTTP clients"""
        for client in self._instance_clients.values():
            await client.aclose()
        self._instance_clients.clear()


# Global client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get global Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
