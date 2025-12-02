"""
Chat session management and history
"""
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Chat message in session"""
    id: str
    role: str  # "user" or "assistant" or "system"
    content: str
    model: Optional[str] = None
    timestamp: datetime
    metadata: Dict = {}


class ChatSession(BaseModel):
    """Chat session with history"""
    id: str
    created_at: datetime
    messages: List[ChatMessage] = []
    system_prompt: Optional[str] = None
    title: Optional[str] = None


class ChatSessionManager:
    """Manager for chat sessions (in-memory for now, can be moved to DB)"""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self, system_prompt: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        session = ChatSession(
            id=session_id,
            created_at=datetime.utcnow(),
            system_prompt=system_prompt,
            title=title
        )
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def add_message(self, session_id: str, role: str, content: str, model: Optional[str] = None, metadata: Dict = None):
        """Add message to session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        message = ChatMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            model=model,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        session.messages.append(message)
        return message
    
    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages from session"""
        session = self.sessions.get(session_id)
        if session:
            return session.messages
        return []
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_ollama_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get chat history in Ollama format"""
        session = self.sessions.get(session_id)
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


# Global session manager
_session_manager = ChatSessionManager()


def get_session_manager() -> ChatSessionManager:
    """Get global session manager"""
    return _session_manager

