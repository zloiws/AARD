"""
Authentication API routes
"""
from typing import Optional

from app.core.auth import (get_current_user, get_current_user_with_role,
                           security)
from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Optional[str] = Field(None, description="User role (default: user)")


class LoginRequest(BaseModel):
    """User login request"""
    username: str  # Can be username or email
    password: str


class UserResponse(BaseModel):
    """User response model"""
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response model"""
    token: str
    user: UserResponse
    expires_at: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        auth_service = AuthService(db)
        
        # Validate role
        role = request.role or UserRole.USER.value
        if role not in [r.value for r in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Allowed roles: {[r.value for r in UserRole]}"
            )
        
        user = auth_service.register_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role=role
        )
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login and create a session"""
    try:
        auth_service = AuthService(db)
        
        # Authenticate user
        user = auth_service.authenticate(request.username, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create session
        session = auth_service.create_session(user.id)
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session.token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=24 * 60 * 60  # 24 hours
        )
        
        return LoginResponse(
            token=session.token,
            user=UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None
            ),
            expires_at=session.expires_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Logout and invalidate session"""
    try:
        auth_service = AuthService(db)
        
        # Get token from cookie or header
        token = None
        if credentials:
            token = credentials.credentials
        else:
            token = request.cookies.get("session_token")
        
        if token:
            auth_service.logout(token)
        
        # Clear cookie
        response.delete_cookie(key="session_token")
        
        return None
    except Exception as e:
        logger.error(f"Error logging out: {e}", exc_info=True)
        # Still clear cookie even if logout fails
        response.delete_cookie(key="session_token")
        return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    user = await get_current_user(request, credentials, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Refresh session token"""
    try:
        auth_service = AuthService(db)
        
        # Get current token
        token = None
        if credentials:
            token = credentials.credentials
        else:
            token = request.cookies.get("session_token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No session token provided"
            )
        
        # Validate current session
        user = auth_service.validate_session(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
        
        # Invalidate old session
        auth_service.logout(token)
        
        # Create new session
        new_session = auth_service.create_session(user.id)
        
        # Set new cookie
        response.set_cookie(
            key="session_token",
            value=new_session.token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=24 * 60 * 60
        )
        
        return LoginResponse(
            token=new_session.token,
            user=UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None
            ),
            expires_at=new_session.expires_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

