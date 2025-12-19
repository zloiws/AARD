"""
A2A (Agent-to-Agent) Communication Protocol
Standardized protocol for agent-to-agent communication
"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from app.core.logging_config import LoggingConfig
from pydantic import BaseModel, Field, field_validator, model_validator

logger = LoggingConfig.get_logger(__name__)


class A2AMessageType(str, Enum):
    """A2A message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class A2AEncryptionType(str, Enum):
    """Encryption types for A2A messages"""
    NONE = "none"
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"


class AgentIdentity(BaseModel):
    """Agent identity information"""
    agent_id: UUID
    spiffe_id: Optional[str] = None
    version: int
    capabilities: List[str] = Field(default_factory=list)


class A2AMessage(BaseModel):
    """
    Standard A2A message format
    
    Based on specification from ТЗ AARD.md section 7.3.2
    """
    # Header
    message_id: UUID = Field(default_factory=uuid4)
    correlation_id: Optional[UUID] = None  # For linking request/response
    parent_message_id: Optional[UUID] = None  # For message chains
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int = Field(default=300, ge=1, le=3600)  # Time to live in seconds
    priority: int = Field(default=5, ge=0, le=9)  # 0-9, where 9 is highest
    
    # Participants
    sender: AgentIdentity
    recipient: Union[UUID, str]  # UUID, "broadcast", or "multicast"
    recipient_filter: Optional[Dict[str, Any]] = None  # For multicast filtering
    
    # Content
    type: A2AMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Context
    context: Optional[Dict[str, Any]] = None  # task_id, step_id, user_id, trace_id
    
    # Response handling
    expected_response_timeout: Optional[int] = None  # For request types (seconds)
    
    # Security
    signature: Optional[str] = None  # Digital signature
    encryption: A2AEncryptionType = A2AEncryptionType.NONE
    encryption_key_id: Optional[UUID] = None
    
    @field_validator('recipient')
    @classmethod
    def validate_recipient(cls, v):
        """Validate recipient field"""
        if isinstance(v, str) and v not in ["broadcast", "multicast"]:
            raise ValueError("recipient must be UUID, 'broadcast', or 'multicast'")
        return v
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate message type"""
        return v
    
    @model_validator(mode='after')
    def set_default_timeout(self):
        """Set default timeout for request messages"""
        if self.type == A2AMessageType.REQUEST and self.expected_response_timeout is None:
            self.expected_response_timeout = 60
        return self
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL"""
        if not self.timestamp:
            return False
        expiry_time = self.timestamp + timedelta(seconds=self.ttl)
        now = datetime.now(timezone.utc)
        # Handle timezone-aware and naive datetimes
        if self.timestamp.tzinfo is None:
            # Naive datetime - assume UTC
            expiry_time = expiry_time.replace(tzinfo=None)
            return now.replace(tzinfo=None) > expiry_time
        return now > expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "message_id": str(self.message_id),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "parent_message_id": str(self.parent_message_id) if self.parent_message_id else None,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "priority": self.priority,
            "sender": {
                "agent_id": str(self.sender.agent_id),
                "spiffe_id": self.sender.spiffe_id,
                "version": self.sender.version,
                "capabilities": self.sender.capabilities
            },
            "recipient": str(self.recipient) if isinstance(self.recipient, UUID) else self.recipient,
            "recipient_filter": self.recipient_filter,
            "type": self.type.value,
            "payload": self.payload,
            "context": self.context,
            "expected_response_timeout": self.expected_response_timeout,
            "signature": self.signature,
            "encryption": self.encryption.value,
            "encryption_key_id": str(self.encryption_key_id) if self.encryption_key_id else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create message from dictionary"""
        # Convert string UUIDs to UUID objects
        if isinstance(data.get('message_id'), str):
            data['message_id'] = UUID(data['message_id'])
        if isinstance(data.get('correlation_id'), str):
            data['correlation_id'] = UUID(data['correlation_id'])
        if isinstance(data.get('parent_message_id'), str):
            data['parent_message_id'] = UUID(data['parent_message_id'])
        if isinstance(data.get('recipient'), str) and data['recipient'] not in ["broadcast", "multicast"]:
            data['recipient'] = UUID(data['recipient'])
        if isinstance(data.get('encryption_key_id'), str):
            data['encryption_key_id'] = UUID(data['encryption_key_id'])
        
        # Convert timestamp
        if isinstance(data.get('timestamp'), str):
            ts_str = data['timestamp'].replace('Z', '+00:00')
            try:
                data['timestamp'] = datetime.fromisoformat(ts_str)
            except ValueError:
                # Fallback for naive datetime strings
                data['timestamp'] = datetime.fromisoformat(data['timestamp']).replace(tzinfo=timezone.utc)
        
        # Convert sender
        if isinstance(data.get('sender'), dict):
            data['sender'] = AgentIdentity(**data['sender'])
        
        # Convert enums
        if isinstance(data.get('type'), str):
            data['type'] = A2AMessageType(data['type'])
        if isinstance(data.get('encryption'), str):
            data['encryption'] = A2AEncryptionType(data['encryption'])
        
        return cls(**data)


class A2ARequest(BaseModel):
    """Helper class for creating A2A requests"""
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
    
    def to_message(
        self,
        sender_id: UUID,
        recipient: Union[UUID, str],
        sender_version: int = 1,
        sender_capabilities: Optional[List[str]] = None,
        priority: int = 5,
        timeout: int = 60
    ) -> A2AMessage:
        """Convert request to A2A message"""
        return A2AMessage(
            sender=AgentIdentity(
                agent_id=sender_id,
                version=sender_version,
                capabilities=sender_capabilities or []
            ),
            recipient=recipient,
            type=A2AMessageType.REQUEST,
            payload={
                "action": self.action,
                "parameters": self.parameters
            },
            context=self.context,
            expected_response_timeout=timeout,
            priority=priority
        )


class A2AResponse(BaseModel):
    """Helper class for creating A2A responses"""
    status: str  # "success", "error", "partial"
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_message(
        self,
        sender_id: UUID,
        correlation_id: UUID,
        sender_version: int = 1,
        sender_capabilities: Optional[List[str]] = None
    ) -> A2AMessage:
        """Convert response to A2A message"""
        message_type = A2AMessageType.ERROR if self.status == "error" else A2AMessageType.RESPONSE
        
        payload = {
            "status": self.status,
            "result": self.result,
            "metadata": self.metadata
        }
        
        if self.error:
            payload["error"] = self.error
        
        return A2AMessage(
            message_id=uuid4(),
            correlation_id=correlation_id,
            sender=AgentIdentity(
                agent_id=sender_id,
                version=sender_version,
                capabilities=sender_capabilities or []
            ),
            recipient="broadcast",  # Response recipient determined by correlation_id
            type=message_type,
            payload=payload
        )

