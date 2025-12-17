"""
Authentication middleware and decorators
"""
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User, UserRole

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Optional[Session] = None
) -> Optional[User]:
    """
    Get current user from request (from token or cookie)
    
    Args:
        request: FastAPI request
        credentials: HTTP Bearer credentials (optional)
        db: Database session (optional, will create if not provided and token exists)
        
    Returns:
        User object if authenticated, None otherwise
    """
    # Try to get token from Authorization header or cookie first (fast check)
    token = None
    if credentials:
        token = credentials.credentials
    elif request:
        # Try to get token from cookie
        token = request.cookies.get("session_token")
    
    # If no token, return None immediately without DB query
    if not token:
        return None
    
    # Only query DB if we have a token
    # Create DB session if not provided
    db_provided = db is not None
    if not db_provided:
        db = next(get_db())
    
    try:
        auth_service = AuthService(db)
        user = auth_service.validate_session(token)
        return user
    except Exception as e:
        # If DB query fails, log and return None (don't block request)
        from app.core.logging_config import LoggingConfig
        logger = LoggingConfig.get_logger(__name__)
        logger.warning(f"Failed to validate session (non-critical): {e}")
        return None
    finally:
        # Close DB session only if we created it
        if not db_provided and db:
            db.close()


def require_auth(func):
    """
    Decorator to require authentication for an endpoint
    
    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(request: Request, current_user: User = Depends(get_current_user)):
            ...
    """
    # This is a simple marker decorator - actual auth check is done via Depends(get_current_user)
    return func


def require_role(*allowed_roles: UserRole):
    """
    Decorator factory to require specific role(s) for an endpoint
    
    Usage:
        @router.get("/admin")
        @require_role(UserRole.ADMIN)
        async def admin_endpoint(request: Request, current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        # This is a marker decorator - actual role check is done via Depends(get_current_user_with_role)
        return func
    return decorator


async def get_current_user_with_role(
    *allowed_roles: UserRole,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    db: Session = None
) -> User:
    """
    Get current user and verify they have one of the allowed roles
    
    Args:
        allowed_roles: Allowed user roles
        request: FastAPI request
        credentials: HTTP Bearer credentials (optional)
        db: Database session (optional)
        
    Returns:
        User object if authenticated and authorized
        
    Raises:
        HTTPException: If not authenticated or not authorized
    """
    user = await get_current_user(request=request, credentials=credentials, db=db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if allowed_roles and user.role not in [role.value for role in allowed_roles]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
        )
    
    return user


async def get_current_user_required(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> "User":
    """
    Require authentication: return User or raise 401
    """
    user = await get_current_user(request=request, credentials=credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None (no exception)
    This version doesn't require DB session unless token is present.
    
    Args:
        request: FastAPI request
        credentials: HTTP Bearer credentials (optional)
        
    Returns:
        User object if authenticated, None otherwise
    """
    # Fast check for token first
    token = None
    if credentials:
        token = credentials.credentials
    elif request:
        token = request.cookies.get("session_token")
    
    # If no token, return None immediately without DB query
    if not token:
        return None
    
    # Only create DB session if we have a token
    try:
        db = next(get_db())
        try:
            auth_service = AuthService(db)
            user = auth_service.validate_session(token)
            return user
        finally:
            db.close()
    except Exception as e:
        # If DB query fails, log and return None (don't block request)
        from app.core.logging_config import LoggingConfig
        logger = LoggingConfig.get_logger(__name__)
        logger.warning(f"Failed to validate session (non-critical): {e}")
        return None

