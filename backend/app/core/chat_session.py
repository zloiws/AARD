"""
Chat session management with database persistence
"""
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.chat_session import ChatSession as ChatSessionModel, ChatMessage as ChatMessageModel
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ChatMessage:
    """Chat message data class"""
    def __init__(self, id: str, role: str, content: str, model: Optional[str] = None, 
                 timestamp: datetime = None, metadata: Dict = None):
        self.id = id
        self.role = role
        self.content = content
        self.model = model
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}


class ChatSession:
    """Chat session data class"""
    def __init__(self, id: str, created_at: datetime = None, messages: List[ChatMessage] = None,
                 system_prompt: Optional[str] = None, title: Optional[str] = None):
        self.id = id
        self.created_at = created_at or datetime.utcnow()
        self.messages = messages or []
        self.system_prompt = system_prompt
        self.title = title


class ChatSessionManager:
    """Manager for chat sessions with database persistence"""
    
    def create_session(self, db: Session, system_prompt: Optional[str] = None, 
                      title: Optional[str] = None, user_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session in database"""
        try:
            session_id = uuid.uuid4()
            db_session = ChatSessionModel(
                id=session_id,
                system_prompt=system_prompt,
                title=title,
                user_id=uuid.UUID(user_id) if user_id and user_id.strip() else None
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
            logger.info(f"Created chat session: {session_id}")
            
            return ChatSession(
                id=str(session_id),
                created_at=db_session.created_at,
                system_prompt=system_prompt,
                title=title
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating chat session: {e}", exc_info=True)
            raise
    
    def get_session(self, db: Session, session_id: str) -> Optional[ChatSession]:
        """Get session by ID from database"""
        try:
            session_uuid = uuid.UUID(session_id)
            db_session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_uuid).first()
            
            if not db_session:
                return None
            
            # Load messages
            messages = []
            for msg in db_session.messages:
                messages.append(ChatMessage(
                    id=str(msg.id),
                    role=msg.role,
                    content=msg.content,
                    model=msg.model,
                    timestamp=msg.created_at,
                    metadata=msg.message_metadata or {}
                ))
            
            return ChatSession(
                id=str(db_session.id),
                created_at=db_session.created_at,
                messages=messages,
                system_prompt=db_session.system_prompt,
                title=db_session.title
            )
        except (ValueError, Exception) as e:
            logger.warning(f"Error getting session {session_id}: {e}")
            return None
    
    def add_message(self, db: Session, session_id: str, role: str, content: str, 
                   model: Optional[str] = None, metadata: Dict = None) -> Optional[ChatMessage]:
        """Add message to session in database"""
        try:
            session_uuid = uuid.UUID(session_id)
            db_session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_uuid).first()
            
            if not db_session:
                logger.warning(f"Session {session_id} not found")
                return None
            
            # Get next sequence number
            max_sequence = db.query(ChatMessageModel.sequence).filter(
                ChatMessageModel.session_id == session_uuid
            ).order_by(ChatMessageModel.sequence.desc()).first()
            next_sequence = (max_sequence[0] + 1) if max_sequence and max_sequence[0] is not None else 0
            
            message_id = uuid.uuid4()
            db_message = ChatMessageModel(
                id=message_id,
                session_id=session_uuid,
                role=role,
                content=content,
                model=model,
                sequence=next_sequence,
                message_metadata=metadata or {}
            )
            db.add(db_message)
            
            # Update session updated_at
            db_session.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_message)
            
            return ChatMessage(
                id=str(message_id),
                role=role,
                content=content,
                model=model,
                timestamp=db_message.created_at,
                metadata=metadata or {}
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding message to session {session_id}: {e}", exc_info=True)
            return None
    
    def get_messages(self, db: Session, session_id: str) -> List[ChatMessage]:
        """Get all messages from session"""
        session = self.get_session(db, session_id)
        if session:
            return session.messages
        return []
    
    def delete_session(self, db: Session, session_id: str):
        """Delete a session (cascade will delete messages)"""
        try:
            session_uuid = uuid.UUID(session_id)
            db_session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_uuid).first()
            if db_session:
                db.delete(db_session)
                db.commit()
                logger.info(f"Deleted chat session: {session_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
    
    def get_ollama_history(self, db: Session, session_id: str) -> List[Dict[str, str]]:
        """Get chat history in Ollama format"""
        session = self.get_session(db, session_id)
        if not session:
            return []
        
        history = []
        if session.system_prompt:
            history.append({"role": "system", "content": session.system_prompt})
        
        for msg in session.messages:
            # Skip system messages (already added as system_prompt)
            if msg.role == "system":
                continue
            history.append({"role": msg.role, "content": msg.content})
        
        return history


# Global session manager instance
_session_manager = ChatSessionManager()


def get_session_manager() -> ChatSessionManager:
    """Get global session manager instance"""
    return _session_manager
