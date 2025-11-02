"""
Authentication API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.auth_service import AuthService
from schemas.auth_schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    RefreshTokenRequest, LogoutRequest, ChangePasswordRequest,
    ActiveSessionsResponse, AuthResponse
)
from api.dependencies import get_current_user, get_current_user_and_session
from models.models import User, ActiveSession
from config.logger import logger


router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account
    
    - **username**: Unique username (3-50 characters, alphanumeric + underscore/dash)
    - **email**: Valid email address
    - **password**: Strong password (minimum 8 characters)
    
    Returns access token and user information upon successful registration.
    """
    try:
        auth_service = AuthService(db)
        
        # Register user
        user = await auth_service.register_user(user_data)
        
        # Automatically log in the new user
        login_data = UserLogin(email=user_data.email, password=user_data.password)
        tokens = await auth_service.authenticate_user(login_data, request)
        
        logger.info(f"New user registered and logged in: {user.email}")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and create session
    
    - **email**: User email address
    - **password**: User password
    
    Returns access token, refresh token, and user information.
    Session information is tracked for security purposes.
    """
    try:
        auth_service = AuthService(db)
        tokens = await auth_service.authenticate_user(credentials, request)
        
        logger.info(f"User logged in: {credentials.email}")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    token_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token.
    """
    try:
        auth_service = AuthService(db)
        tokens = await auth_service.refresh_token(token_data.refresh_token, request)
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=AuthResponse)
async def logout_user(
    logout_data: LogoutRequest,
    user_session: tuple[User, ActiveSession] = Depends(get_current_user_and_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user (terminate session)
    
    - **logout_all**: If true, terminates all user sessions
    
    Default behavior terminates only the current session.
    """
    try:
        user, session = user_session
        auth_service = AuthService(db)
        
        success = await auth_service.logout_user(
            user_id=user.id,
            session_id=session.id if not logout_data.logout_all else None,
            logout_all=logout_data.logout_all
        )
        
        if success:
            message = "All sessions terminated" if logout_data.logout_all else "Session terminated"
            logger.info(f"User {user.email} logged out (all sessions: {logout_data.logout_all})")
            
            return AuthResponse(
                success=True,
                message=message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    
    Returns detailed information about the authenticated user.
    """
    return UserResponse.model_validate(current_user)


@router.get("/sessions", response_model=ActiveSessionsResponse)
async def get_user_sessions(
    user_session: tuple[User, ActiveSession] = Depends(get_current_user_and_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active sessions for current user
    
    Returns list of active sessions with device and location information.
    """
    try:
        user, current_session = user_session
        auth_service = AuthService(db)
        
        sessions = await auth_service.get_active_sessions(
            user_id=user.id,
            current_session_id=current_session.id
        )
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving sessions"
        )


@router.delete("/sessions/{session_id}", response_model=AuthResponse)
async def terminate_session(
    session_id: int,
    user_session: tuple[User, ActiveSession] = Depends(get_current_user_and_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Terminate a specific session
    
    - **session_id**: ID of the session to terminate
    
    Cannot terminate the current session.
    """
    try:
        user, current_session = user_session
        auth_service = AuthService(db)
        
        success = await auth_service.terminate_session(
            user_id=user.id,
            session_id=session_id,
            current_session_id=current_session.id
        )
        
        if success:
            logger.info(f"Session {session_id} terminated for user {user.email}")
            return AuthResponse(
                success=True,
                message="Session terminated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to terminate session"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error terminating session"
        )


@router.post("/change-password", response_model=AuthResponse)
async def change_user_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    
    - **current_password**: Current password for verification
    - **new_password**: New strong password
    
    Terminates all other sessions for security.
    """
    try:
        auth_service = AuthService(db)
        
        success = await auth_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        if success:
            logger.info(f"Password changed for user: {current_user.email}")
            return AuthResponse(
                success=True,
                message="Password changed successfully. Please log in again on other devices."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def auth_health_check():
    """
    Authentication service health check
    
    Returns the status of the authentication service.
    """
    return {
        "service": "authentication",
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"  # This would be current timestamp in real implementation
    }


@router.post("/verify-token", response_model=UserResponse)
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """
    Verify access token validity
    
    Returns user information if token is valid.
    Useful for frontend token validation.
    """
    return UserResponse.model_validate(current_user)