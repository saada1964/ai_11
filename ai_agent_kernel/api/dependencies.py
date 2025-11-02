"""
Authentication dependencies for FastAPI
"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.auth_service import AuthService
from models.models import User, ActiveSession
from config.logger import logger


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        auth_service = AuthService(db)
        user, session = await auth_service.verify_session(credentials.credentials)
        
        # Store user and session in request state for other dependencies
        request.state.current_user = user
        request.state.current_session = session
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user dependency: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_user_and_session(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Tuple[User, ActiveSession]:
    """
    Dependency to get current user and session
    """
    session = getattr(request.state, 'current_session', None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session information not available"
        )
    
    return current_user, session


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        auth_service = AuthService(db)
        user, _ = await auth_service.verify_session(credentials.credentials)
        return user if user.is_active else None
        
    except Exception:
        return None


class RequirePermissions:
    """
    Dependency class to require specific permissions
    """
    
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self, 
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # For now, we don't have a permission system implemented
        # This is a placeholder for future permission-based access control
        # You can extend this to check user roles, permissions, etc.
        
        # Example implementation:
        # if not all(perm in current_user.permissions for perm in self.required_permissions):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Insufficient permissions"
        #     )
        
        return current_user


class RequireRoles:
    """
    Dependency class to require specific user roles
    """
    
    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles
    
    async def __call__(
        self, 
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # For now, we don't have a role system implemented
        # This is a placeholder for future role-based access control
        
        # Example implementation:
        # if not any(role in current_user.roles for role in self.required_roles):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Insufficient role permissions"
        #     )
        
        return current_user




# ## ==> ==> ==> هذه هي الدالة الجديدة للـ WebSocket <== <== <==
async def authenticate_websocket_user(
    token: Optional[str],
    db: AsyncSession
) -> Optional[User]:
    """
    Verifies a token provided via WebSocket and returns the active user.
    Returns None if authentication fails.
    """
    if not token:
        return None
    
    try:
        # أعد استخدام نفس خدمة المصادقة القوية
        auth_service = AuthService(db)
        user, session = await auth_service.verify_session(token)
        
        # تأكد من أن المستخدم نشط
        if not user or not user.is_active:
            return None
            
        return user
        
    except Exception:
        # إذا فشل التحقق لأي سبب، أرجع None
        return None
    
# Commonly used dependency instances
require_admin = RequireRoles(["admin"])
require_moderator = RequireRoles(["admin", "moderator"])
require_user = RequireRoles(["admin", "moderator", "user"])