"""
Permission checking utilities
"""
from typing import TYPE_CHECKING, List, Optional

from app.models.user import User, UserRole
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.user import User


class Permission:
    """Permission constants"""
    # Agent permissions
    AGENT_CREATE = "agent:create"
    AGENT_EDIT = "agent:edit"
    AGENT_DELETE = "agent:delete"
    AGENT_VIEW = "agent:view"
    
    # Tool permissions
    TOOL_CREATE = "tool:create"
    TOOL_EDIT = "tool:edit"
    TOOL_DELETE = "tool:delete"
    TOOL_VIEW = "tool:view"
    
    # Plan permissions
    PLAN_CREATE = "plan:create"
    PLAN_EDIT = "plan:edit"
    PLAN_DELETE = "plan:delete"
    PLAN_VIEW = "plan:view"
    PLAN_EXECUTE = "plan:execute"
    
    # Admin permissions
    ADMIN_ALL = "admin:all"
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN.value: [
        Permission.ADMIN_ALL,
        Permission.USER_MANAGE,
        Permission.SYSTEM_CONFIG,
        Permission.AGENT_CREATE,
        Permission.AGENT_EDIT,
        Permission.AGENT_DELETE,
        Permission.AGENT_VIEW,
        Permission.TOOL_CREATE,
        Permission.TOOL_EDIT,
        Permission.TOOL_DELETE,
        Permission.TOOL_VIEW,
        Permission.PLAN_CREATE,
        Permission.PLAN_EDIT,
        Permission.PLAN_DELETE,
        Permission.PLAN_VIEW,
        Permission.PLAN_EXECUTE,
    ],
    UserRole.USER.value: [
        Permission.AGENT_VIEW,
        Permission.AGENT_CREATE,
        Permission.AGENT_EDIT,
        Permission.TOOL_VIEW,
        Permission.TOOL_CREATE,
        Permission.TOOL_EDIT,
        Permission.PLAN_VIEW,
        Permission.PLAN_CREATE,
        Permission.PLAN_EDIT,
        Permission.PLAN_EXECUTE,
    ],
    UserRole.VIEWER.value: [
        Permission.AGENT_VIEW,
        Permission.TOOL_VIEW,
        Permission.PLAN_VIEW,
    ],
}


def has_permission(user: User, permission: str) -> bool:
    """
    Check if a user has a specific permission
    
    Args:
        user: User object
        permission: Permission string (e.g., "agent:create")
        
    Returns:
        True if user has permission, False otherwise
    """
    user_permissions = ROLE_PERMISSIONS.get(user.role, [])
    
    # Admin has all permissions
    if Permission.ADMIN_ALL in user_permissions:
        return True
    
    return permission in user_permissions


def require_permission(permission: str):
    """
    Decorator factory to require a specific permission
    
    Usage:
        @router.post("/agents")
        @require_permission(Permission.AGENT_CREATE)
        async def create_agent(...):
            ...
    """
    def decorator(func):
        # This is a marker decorator - actual permission check is done via Depends
        return func
    return decorator


async def get_current_user_with_permission(
    permission: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    db: Session = None
):
    """
    Get current user and verify they have the required permission
    
    Args:
        permission: Required permission
        request: FastAPI request
        credentials: HTTP Bearer credentials (optional)
        db: Database session (optional)
        
    Returns:
        User object if authenticated and authorized
        
    Raises:
        HTTPException: If not authenticated or not authorized
    """
    from app.core.auth import get_current_user
    
    user = await get_current_user(request=request, credentials=credentials, db=db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required permission: {permission}"
        )
    
    return user
