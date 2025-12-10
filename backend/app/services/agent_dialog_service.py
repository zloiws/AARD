"""
Agent Dialog Service for managing conversations between agents
"""
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.orm.attributes import flag_modified

from app.models.agent_conversation import (
    AgentConversation,
    ConversationStatus,
    MessageRole
)
from app.models.agent import Agent, AgentStatus
from app.models.task import Task
from app.core.logging_config import LoggingConfig
from app.services.a2a_router import A2ARouter
from app.core.a2a_protocol import A2AMessage, A2AMessageType, A2AResponse
from app.core.config import get_settings

logger = LoggingConfig.get_logger(__name__)
settings = get_settings()


class AgentDialogService:
    """
    Service for managing agent conversations/dialogs
    
    Handles:
    - Creating conversations between agents
    - Adding messages to conversations
    - Managing conversation context
    - Determining conversation completion
    - Integration with A2A protocol for message exchange
    """
    
    def __init__(self, db: Session):
        """
        Initialize Agent Dialog Service
        
        Args:
            db: Database session
        """
        self.db = db
        self.a2a_router = A2ARouter(db)
    
    def create_conversation(
        self,
        participant_ids: List[UUID],
        goal: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        task_id: Optional[UUID] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> AgentConversation:
        """
        Create a new conversation between agents
        
        Args:
            participant_ids: List of agent IDs participating in the conversation
            goal: Goal of the conversation
            title: Optional title for the conversation
            description: Optional description
            task_id: Optional link to a task
            initial_context: Optional initial context
            
        Returns:
            Created AgentConversation
            
        Raises:
            ValueError: If invalid participant IDs or less than 2 participants
        """
        if len(participant_ids) < 2:
            raise ValueError("Conversation must have at least 2 participants")
        
        # Validate that all participants exist and are active
        agents = self.db.query(Agent).filter(
            and_(
                Agent.id.in_(participant_ids),
                Agent.status == AgentStatus.ACTIVE.value
            )
        ).all()
        
        if len(agents) != len(participant_ids):
            found_ids = {agent.id for agent in agents}
            missing_ids = set(participant_ids) - found_ids
            raise ValueError(f"Some agents not found or not active: {missing_ids}")
        
        # Create conversation
        conversation = AgentConversation(
            title=title,
            description=description,
            participants=[str(pid) for pid in participant_ids],
            messages=[],
            context=initial_context or {},
            goal=goal,
            status=ConversationStatus.INITIATED.value,
            task_id=task_id
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        logger.info(
            f"Created conversation: {conversation.id}",
            extra={
                "conversation_id": str(conversation.id),
                "participants": [str(pid) for pid in participant_ids],
                "goal": goal,
                "task_id": str(task_id) if task_id else None
            }
        )
        
        return conversation
    
    def get_conversation(self, conversation_id: UUID) -> Optional[AgentConversation]:
        """
        Get conversation by ID
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            AgentConversation or None if not found
        """
        return self.db.query(AgentConversation).filter(
            AgentConversation.id == conversation_id
        ).first()
    
    def get_conversations_by_task(self, task_id: UUID) -> List[AgentConversation]:
        """
        Get all conversations for a task
        
        Args:
            task_id: Task ID
            
        Returns:
            List of AgentConversation
        """
        return self.db.query(AgentConversation).filter(
            AgentConversation.task_id == task_id
        ).order_by(AgentConversation.created_at.desc()).all()
    
    def get_conversations_by_agent(self, agent_id: UUID) -> List[AgentConversation]:
        """
        Get all conversations where an agent participates
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of AgentConversation
        """
        # Query conversations where agent_id is in participants JSONB array
        agent_id_str = str(agent_id)
        return self.db.query(AgentConversation).filter(
            AgentConversation.participants.contains([agent_id_str])
        ).order_by(AgentConversation.created_at.desc()).all()
    
    def add_message(
        self,
        conversation_id: UUID,
        agent_id: UUID,
        content: str,
        role: MessageRole = MessageRole.AGENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation
        
        Args:
            conversation_id: Conversation ID
            agent_id: Agent ID sending the message
            content: Message content
            role: Message role
            metadata: Optional message metadata
            
        Returns:
            Created message object
            
        Raises:
            ValueError: If conversation not found or agent is not a participant
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Verify agent is a participant
        if not conversation.is_participant(agent_id):
            raise ValueError(f"Agent {agent_id} is not a participant in conversation {conversation_id}")
        
        # Add message
        message = conversation.add_message(
            agent_id=agent_id,
            content=content,
            role=role,
            metadata=metadata
        )
        
        # Mark JSONB fields as modified for SQLAlchemy to track changes
        flag_modified(conversation, "messages")
        if conversation.status != ConversationStatus.ACTIVE.value:
            flag_modified(conversation, "status")
        
        self.db.commit()
        self.db.refresh(conversation)
        
        logger.debug(
            f"Added message to conversation {conversation_id}",
            extra={
                "conversation_id": str(conversation_id),
                "agent_id": str(agent_id),
                "message_id": message.get("id"),
                "role": role.value if isinstance(role, MessageRole) else role
            }
        )
        
        return message
    
    async def send_message_to_participants(
        self,
        conversation_id: UUID,
        sender_agent_id: UUID,
        content: str,
        recipient_agent_ids: Optional[List[UUID]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message in conversation and notify other participants via A2A protocol
        
        Args:
            conversation_id: Conversation ID
            sender_agent_id: Agent ID sending the message
            content: Message content
            recipient_agent_ids: Optional list of specific recipients (if None, sends to all other participants)
            metadata: Optional message metadata
            
        Returns:
            Created message object
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Add message to conversation
        message = self.add_message(
            conversation_id=conversation_id,
            agent_id=sender_agent_id,
            content=content,
            role=MessageRole.AGENT,
            metadata=metadata
        )
        
        # Determine recipients
        participants = conversation.get_participants()
        if recipient_agent_ids:
            # Send to specific recipients
            recipients = [rid for rid in recipient_agent_ids if rid in participants and rid != sender_agent_id]
        else:
            # Send to all other participants
            recipients = [pid for pid in participants if pid != sender_agent_id]
        
        # Send A2A messages to recipients
        for recipient_id in recipients:
            try:
                a2a_message = A2AMessage(
                    message_id=uuid4(),
                    sender=sender_agent_id,
                    recipient=recipient_id,
                    type=A2AMessageType.REQUEST,
                    content={
                        "conversation_id": str(conversation_id),
                        "message": content,
                        "sender_agent_id": str(sender_agent_id),
                        "message_id": message.get("id")
                    },
                    metadata=metadata or {}
                )
                
                # Send asynchronously (fire-and-forget for now)
                await self.a2a_router.send_message(a2a_message, wait_for_response=False)
                
                logger.debug(
                    f"Sent A2A message to agent {recipient_id}",
                    extra={
                        "conversation_id": str(conversation_id),
                        "sender_id": str(sender_agent_id),
                        "recipient_id": str(recipient_id)
                    }
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send A2A message to agent {recipient_id}: {e}",
                    exc_info=True,
                    extra={
                        "conversation_id": str(conversation_id),
                        "recipient_id": str(recipient_id)
                    }
                )
        
        return message
    
    def update_context(
        self,
        conversation_id: UUID,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update conversation context
        
        Args:
            conversation_id: Conversation ID
            updates: Dictionary with context updates
            
        Returns:
            Updated context
            
        Raises:
            ValueError: If conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation.update_context(updates)
        self.db.commit()
        self.db.refresh(conversation)
        
        logger.debug(
            f"Updated context for conversation {conversation_id}",
            extra={
                "conversation_id": str(conversation_id),
                "updates": list(updates.keys())
            }
        )
        
        return conversation.get_context()
    
    def is_conversation_complete(
        self,
        conversation_id: UUID,
        check_conditions: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if conversation is complete based on conditions
        
        Args:
            conversation_id: Conversation ID
            check_conditions: Optional conditions to check:
                - min_messages: Minimum number of messages
                - max_messages: Maximum number of messages
                - goal_achieved: Check if goal is achieved (requires goal_checker function)
                - timeout_seconds: Maximum conversation duration
                
        Returns:
            True if conversation should be considered complete
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        # Refresh to get latest state
        self.db.refresh(conversation)
        
        if conversation.status in [ConversationStatus.COMPLETED.value, ConversationStatus.FAILED.value, ConversationStatus.CANCELLED.value]:
            return True
        
        if not check_conditions:
            return False
        
        messages = conversation.get_messages()
        message_count = len(messages)
        
        # Check minimum messages
        if "min_messages" in check_conditions:
            if message_count < check_conditions["min_messages"]:
                return False
        
        # Check maximum messages
        if "max_messages" in check_conditions:
            if message_count >= check_conditions["max_messages"]:
                logger.info(
                    f"Conversation {conversation_id} reached max_messages limit",
                    extra={"conversation_id": str(conversation_id), "message_count": message_count}
                )
                return True
        
        # Check timeout
        if "timeout_seconds" in check_conditions:
            elapsed = (datetime.now(timezone.utc) - conversation.created_at).total_seconds()
            if elapsed >= check_conditions["timeout_seconds"]:
                logger.info(
                    f"Conversation {conversation_id} reached timeout",
                    extra={"conversation_id": str(conversation_id), "elapsed_seconds": elapsed}
                )
                return True
        
        # Check goal achievement (if goal_checker provided)
        if "goal_achieved" in check_conditions and check_conditions["goal_achieved"]:
            # This would require a goal_checker function
            # For now, we'll just return True if goal_achieved is explicitly set
            return True
        
        return False
    
    def complete_conversation(
        self,
        conversation_id: UUID,
        success: bool = True,
        result: Optional[Dict[str, Any]] = None
    ) -> AgentConversation:
        """
        Mark conversation as completed
        
        Args:
            conversation_id: Conversation ID
            success: Whether conversation completed successfully
            result: Optional result data to store in context
            
        Returns:
            Updated AgentConversation
            
        Raises:
            ValueError: If conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Store result in context if provided
        if result:
            conversation.update_context({"result": result, "completed_at": datetime.now(timezone.utc).isoformat()})
        
        conversation.complete(success=success)
        self.db.commit()
        self.db.refresh(conversation)
        
        logger.info(
            f"Completed conversation {conversation_id}",
            extra={
                "conversation_id": str(conversation_id),
                "success": success,
                "message_count": len(conversation.get_messages())
            }
        )
        
        return conversation
    
    def pause_conversation(self, conversation_id: UUID) -> AgentConversation:
        """
        Pause a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Updated AgentConversation
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation.status = ConversationStatus.PAUSED.value
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def resume_conversation(self, conversation_id: UUID) -> AgentConversation:
        """
        Resume a paused conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Updated AgentConversation
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        if conversation.status != ConversationStatus.PAUSED.value:
            raise ValueError(f"Conversation {conversation_id} is not paused")
        
        conversation.status = ConversationStatus.ACTIVE.value
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation

