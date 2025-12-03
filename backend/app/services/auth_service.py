"""
Authentication service for user management and sessions
"""
import secrets
import bcrypt
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User, Session as UserSession, UserRole
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class AuthService:
    """Service for user authentication and session management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_duration_hours = 24  # Default session duration
    
    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = UserRole.USER.value
    ) -> User:
        """
        Register a new user
        
        Args:
            username: Username
            email: Email address
            password: Plain text password
            role: User role (default: user)
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        if self.db.query(User).filter(User.username == username).first():
            raise ValueError(f"Username '{username}' already exists")
        
        # Check if email exists
        if self.db.query(User).filter(User.email == email).first():
            raise ValueError(f"Email '{email}' already exists")
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Registered new user: {username} (role: {role})")
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user by username and password
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        # Try to find user by username or email
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication failed: user '{username}' is inactive")
            return None
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User '{username}' authenticated successfully")
        return user
    
    def create_session(self, user_id: UUID, duration_hours: Optional[int] = None) -> UserSession:
        """
        Create a new session for a user
        
        Args:
            user_id: User ID
            duration_hours: Session duration in hours (default: 24)
            
        Returns:
            Created Session object
        """
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Calculate expiration
        duration = duration_hours or self.session_duration_hours
        expires_at = datetime.utcnow() + timedelta(hours=duration)
        
        # Create session
        session = UserSession(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Created session for user {user_id}")
        return session
    
    def validate_session(self, token: str) -> Optional[User]:
        """
        Validate a session token and return the associated user
        
        Args:
            token: Session token
            
        Returns:
            User object if session is valid, None otherwise
        """
        session = self.db.query(UserSession).filter(
            UserSession.token == token
        ).first()
        
        if not session:
            return None
        
        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            logger.info(f"Session {session.id} expired")
            self.db.delete(session)
            self.db.commit()
            return None
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        self.db.commit()
        
        # Get user
        user = self.db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    def logout(self, token: str) -> bool:
        """
        Logout by invalidating a session
        
        Args:
            token: Session token
            
        Returns:
            True if session was found and deleted, False otherwise
        """
        session = self.db.query(UserSession).filter(
            UserSession.token == token
        ).first()
        
        if session:
            self.db.delete(session)
            self.db.commit()
            logger.info(f"Session {session.id} invalidated")
            return True
        
        return False
    
    def logout_all_user_sessions(self, user_id: UUID) -> int:
        """
        Logout all sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions deleted
        """
        sessions = self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).all()
        
        count = len(sessions)
        for session in sessions:
            self.db.delete(session)
        
        self.db.commit()
        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions from the database
        
        Returns:
            Number of sessions deleted
        """
        expired_sessions = self.db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_sessions)
        for session in expired_sessions:
            self.db.delete(session)
        
        self.db.commit()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

