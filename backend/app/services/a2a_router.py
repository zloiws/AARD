"""
A2A Message Router
Routes A2A messages between agents
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.a2a_protocol import A2AMessage, A2AMessageType, A2AResponse
from app.services.agent_registry import AgentRegistry
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_tracer, add_span_attributes

logger = LoggingConfig.get_logger(__name__)


class A2ARouter:
    """
    Router for A2A messages
    
    Handles:
    - Synchronous request-response
    - Asynchronous fire-and-forget
    - Broadcast and multicast
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.registry = AgentRegistry(db)
        self.tracer = get_tracer(__name__)
        self.pending_requests: Dict[UUID, asyncio.Future] = {}  # correlation_id -> Future
    
    async def send_message(
        self,
        message: A2AMessage,
        wait_for_response: bool = False,
        timeout: Optional[int] = None
    ) -> Optional[A2AMessage]:
        """
        Send A2A message
        
        Args:
            message: A2A message to send
            wait_for_response: If True, wait for response (for request messages)
            timeout: Timeout in seconds (uses message.expected_response_timeout if not provided)
            
        Returns:
            Response message if wait_for_response=True, None otherwise
        """
        with self.tracer.start_as_current_span("a2a_router.send_message") as span:
            add_span_attributes(span, {
                "message_id": str(message.message_id),
                "message_type": message.type.value,
                "recipient": str(message.recipient) if isinstance(message.recipient, UUID) else message.recipient
            })
            
            # Check if message is expired
            if message.is_expired():
                logger.warning(f"Message {message.message_id} has expired")
                add_span_attributes(span, expired=True)
                return None
            
            # Route based on recipient type
            if isinstance(message.recipient, UUID):
                # Direct message to specific agent
                return await self._send_to_agent(message, wait_for_response, timeout)
            elif message.recipient == "broadcast":
                # Broadcast to all active agents
                return await self._broadcast(message)
            elif message.recipient == "multicast":
                # Multicast to agents matching filter
                return await self._multicast(message, message.recipient_filter or {})
            else:
                logger.error(f"Unknown recipient type: {message.recipient}")
                return None
    
    async def _send_to_agent(
        self,
        message: A2AMessage,
        wait_for_response: bool = False,
        timeout: Optional[int] = None
    ) -> Optional[A2AMessage]:
        """Send message to specific agent"""
        recipient_id = message.recipient
        
        # Get agent endpoint
        endpoint = self.registry.get_agent_endpoint(recipient_id)
        if not endpoint:
            logger.warning(f"Agent {recipient_id} not found or has no endpoint")
            return None
        
        # For now, we'll use HTTP to send messages
        # In the future, this could use WebSocket, gRPC, etc.
        try:
            import httpx
            
            timeout_seconds = timeout or message.expected_response_timeout or 60
            
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    f"{endpoint}/a2a/message",
                    json=message.to_dict(),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if wait_for_response and message.type == A2AMessageType.REQUEST:
                        return A2AMessage.from_dict(response_data)
                    return None
                else:
                    logger.error(f"Failed to send message to {recipient_id}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(
                f"Error sending message to agent {recipient_id}: {e}",
                exc_info=True,
                extra={"agent_id": str(recipient_id), "endpoint": endpoint}
            )
            return None
    
    async def _broadcast(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Broadcast message to all active agents"""
        with self.tracer.start_as_current_span("a2a_router.broadcast") as span:
            active_agents = self.registry.find_agents()
            
            add_span_attributes(span, recipient_count=len(active_agents))
            
            # Send to all agents in parallel
            tasks = []
            for agent in active_agents:
                # Create a copy of message for each agent
                agent_message = A2AMessage(
                    **message.dict(),
                    recipient=agent.id
                )
                tasks.append(self._send_to_agent(agent_message, wait_for_response=False))
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
            logger.info(f"Broadcast to {len(active_agents)} agents: {successful} successful")
            
            return None  # Broadcast doesn't return response
    
    async def _multicast(
        self,
        message: A2AMessage,
        filter_criteria: Dict[str, Any]
    ) -> Optional[A2AMessage]:
        """Multicast message to agents matching filter"""
        with self.tracer.start_as_current_span("a2a_router.multicast") as span:
            # Extract filter criteria
            capabilities = filter_criteria.get("capabilities", [])
            status = filter_criteria.get("status")
            health_status = filter_criteria.get("health_status")
            
            # Find matching agents
            matching_agents = self.registry.find_agents(
                capabilities=capabilities if capabilities else None,
                status=status,
                health_status=health_status
            )
            
            add_span_attributes(span, {
                "recipient_count": len(matching_agents),
                "filter_capabilities": str(capabilities) if capabilities else None
            })
            
            # Send to all matching agents
            tasks = []
            for agent in matching_agents:
                agent_message = A2AMessage(
                    **message.dict(),
                    recipient=agent.id
                )
                tasks.append(self._send_to_agent(agent_message, wait_for_response=False))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
            
            logger.info(f"Multicast to {len(matching_agents)} agents: {successful} successful")
            
            return None  # Multicast doesn't return response
    
    async def handle_incoming_message(
        self,
        message: A2AMessage,
        handler_callback: Optional[callable] = None
    ) -> Optional[A2AMessage]:
        """
        Handle incoming A2A message
        
        Args:
            message: Incoming A2A message
            handler_callback: Optional callback function to handle the message
            
        Returns:
            Response message if message is a request, None otherwise
        """
        with self.tracer.start_as_current_span("a2a_router.handle_incoming") as span:
            add_span_attributes(span, {
                "message_id": str(message.message_id),
                "message_type": message.type.value,
                "sender_id": str(message.sender.agent_id)
            })
            
            # Check if message is expired
            if message.is_expired():
                logger.warning(f"Incoming message {message.message_id} has expired")
                return None
            
            # Handle based on message type
            if message.type == A2AMessageType.REQUEST:
                # Process request and return response
                if handler_callback:
                    try:
                        result = await handler_callback(message)
                        if isinstance(result, A2AResponse):
                            response = result.to_message(
                                sender_id=message.recipient,  # Current agent ID
                                correlation_id=message.message_id
                            )
                            return response
                        elif isinstance(result, dict):
                            # Convert dict to A2AResponse
                            a2a_response = A2AResponse(**result)
                            response = a2a_response.to_message(
                                sender_id=message.recipient,
                                correlation_id=message.message_id
                            )
                            return response
                    except Exception as e:
                        logger.error(f"Error handling message {message.message_id}: {e}", exc_info=True)
                        # Return error response
                        error_response = A2AResponse(
                            status="error",
                            error=str(e)
                        )
                        return error_response.to_message(
                            sender_id=message.recipient,
                            correlation_id=message.message_id
                        )
                else:
                    logger.warning(f"No handler callback for message {message.message_id}")
                    return None
                    
            elif message.type == A2AMessageType.RESPONSE:
                # Handle response to previous request
                if message.correlation_id and message.correlation_id in self.pending_requests:
                    future = self.pending_requests.pop(message.correlation_id)
                    if not future.done():
                        future.set_result(message)
                return None
                
            elif message.type == A2AMessageType.NOTIFICATION:
                # Fire-and-forget notification
                if handler_callback:
                    try:
                        await handler_callback(message)
                    except Exception as e:
                        logger.error(f"Error handling notification {message.message_id}: {e}", exc_info=True)
                return None
                
            elif message.type == A2AMessageType.HEARTBEAT:
                # Heartbeat message - update registry
                self.registry.register_heartbeat(
                    message.sender.agent_id,
                    endpoint=None,  # Endpoint should be known from registration
                    response_time_ms=None
                )
                return None
                
            else:
                logger.warning(f"Unknown message type: {message.type}")
                return None

