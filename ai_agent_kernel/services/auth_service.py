"""
Authentication service for managing user authentication and sessions
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, desc
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status, Request
import asyncio

from models.models import User, ActiveSession
from schemas.auth_schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse, 
    SessionInfo, DeviceInfo, ActiveSessionsResponse
)
from utils.security import SecurityUtils, JWTManager, get_client_ip, get_user_agent, parse_device_info
from config.settings import settings
from config.logger import logger


class AuthService:
    """Authentication service class"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_user(self, user_data: UserRegister) -> UserResponse:
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = await self.db.execute(
                select(User).where(
                    (User.email == user_data.email) | 
                    (User.username == user_data.username)
                )
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email or username already exists"
                )
            
            # Validate password strength
            is_strong, message = SecurityUtils.validate_password_strength(user_data.password)
            if not is_strong:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
            
            # Hash password and create user
            hashed_password = SecurityUtils.hash_password(user_data.password)
            
            new_user = User(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password,
                balance=100000,  # Starting balance
                is_active=True
            )
            
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            
            logger.info(f"New user registered: {new_user.email}")
            return UserResponse.model_validate(new_user)
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error registering user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user account"
            )
    
    async def authenticate_user(self, credentials: UserLogin, request: Request) -> TokenResponse:
        """Authenticate user and create session"""
        try:
            # Get user by email
            result = await self.db.execute(
                select(User).where(User.email == credentials.email)
            )
            user = result.scalar_one_or_none()
            
            if not user or not SecurityUtils.verify_password(credentials.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is disabled"
                )
            
            # Create tokens and session
            tokens = await self._create_user_session(user, request)
            
            logger.info(f"User authenticated: {user.email}")
            return tokens
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )
    
    async def refresh_token(self, refresh_token: str, request: Request) -> TokenResponse:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = JWTManager.verify_token(refresh_token, "refresh")
            user_id = int(payload.get("sub"))
            session_id = payload.get("session_id")
            
            # Get user and session
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Verify session exists and is active
            session_result = await self.db.execute(
                select(ActiveSession).where(
                    and_(
                        ActiveSession.id == session_id,
                        ActiveSession.user_id == user_id,
                        ActiveSession.refresh_token == SecurityUtils.hash_token(refresh_token),
                        ActiveSession.is_active == True,
                        ActiveSession.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
            session = session_result.scalar_one_or_none()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
            
            # Create new tokens
            access_token = JWTManager.create_access_token({
                "sub": str(user.id),
                "email": user.email,
                "session_id": session.id
            })
            
            new_refresh_token = JWTManager.create_refresh_token({
                "sub": str(user.id),
                "session_id": session.id
            })
            
            # Update session with new refresh token
            session.refresh_token = SecurityUtils.hash_token(new_refresh_token)
            session.last_activity = datetime.now(timezone.utc)
            session.ip_address = get_client_ip(request)
            
            await self.db.commit()
            
            logger.info(f"Token refreshed for user: {user.email}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=settings.access_token_expire_minutes * 60,
                user=UserResponse.model_validate(user)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )
    
    async def logout_user(self, user_id: int, session_id: Optional[int] = None, logout_all: bool = False) -> bool:
        """Logout user (single session or all sessions)"""
        try:
            if logout_all:
                # Deactivate all user sessions
                await self.db.execute(
                    update(ActiveSession)
                    .where(ActiveSession.user_id == user_id)
                    .values(is_active=False)
                )
            elif session_id:
                # Deactivate specific session
                await self.db.execute(
                    update(ActiveSession)
                    .where(
                        and_(
                            ActiveSession.user_id == user_id,
                            ActiveSession.id == session_id
                        )
                    )
                    .values(is_active=False)
                )
            
            await self.db.commit()
            
            logger.info(f"User {user_id} logged out (all sessions: {logout_all})")
            return True
            
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            return False
    
    async def get_active_sessions(self, user_id: int, current_session_id: Optional[int] = None) -> ActiveSessionsResponse:
        """Get all active sessions for a user"""
        try:
            result = await self.db.execute(
                select(ActiveSession)
                .where(
                    and_(
                        ActiveSession.user_id == user_id,
                        ActiveSession.is_active == True,
                        ActiveSession.expires_at > datetime.now(timezone.utc)
                    )
                )
                .order_by(desc(ActiveSession.last_activity))
            )
            sessions = result.scalars().all()
            
            session_info = []
            for session in sessions:
                session_info.append(SessionInfo(
                    id=session.id,
                    device_info=session.device_info,
                    ip_address=session.ip_address,
                    user_agent=session.user_agent,
                    last_activity=session.last_activity,
                    created_at=session.created_at,
                    is_current=(session.id == current_session_id)
                ))
            
            return ActiveSessionsResponse(
                sessions=session_info,
                total_count=len(session_info)
            )
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving sessions"
            )
    
    async def terminate_session(self, user_id: int, session_id: int, current_session_id: int) -> bool:
        """Terminate a specific session"""
        try:
            if session_id == current_session_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot terminate current session"
                )
            
            result = await self.db.execute(
                update(ActiveSession)
                .where(
                    and_(
                        ActiveSession.id == session_id,
                        ActiveSession.user_id == user_id
                    )
                )
                .values(is_active=False)
            )
            
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            await self.db.commit()
            logger.info(f"Session {session_id} terminated for user {user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error terminating session: {e}")
            return False
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            # Get user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not SecurityUtils.verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Validate new password strength
            is_strong, message = SecurityUtils.validate_password_strength(new_password)
            if not is_strong:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
            
            # Update password
            user.hashed_password = SecurityUtils.hash_password(new_password)
            await self.db.commit()
            
            # Invalidate all sessions except current one (for security)
            # This forces re-login on all other devices
            await self.db.execute(
                update(ActiveSession)
                .where(ActiveSession.user_id == user_id)
                .values(is_active=False)
            )
            await self.db.commit()
            
            logger.info(f"Password changed for user: {user.email}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False
    
    async def _create_user_session(self, user: User, request: Request) -> TokenResponse:
        """Create a new session for authenticated user"""
        try:
            # Clean up expired sessions
            await self._cleanup_expired_sessions(user.id)
            
            # Check session limit
            active_sessions_count = await self.db.execute(
                select(ActiveSession)
                .where(
                    and_(
                        ActiveSession.user_id == user.id,
                        ActiveSession.is_active == True,
                        ActiveSession.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
            active_count = len(active_sessions_count.scalars().all())
            
            if active_count >= settings.max_sessions_per_user:
                # Remove oldest session
                oldest_session = await self.db.execute(
                    select(ActiveSession)
                    .where(
                        and_(
                            ActiveSession.user_id == user.id,
                            ActiveSession.is_active == True
                        )
                    )
                    .order_by(ActiveSession.last_activity.asc())
                    .limit(1)
                )
                oldest = oldest_session.scalar_one_or_none()
                if oldest:
                    oldest.is_active = False
            
            # Create new session
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)
            device_info = parse_device_info(user_agent)
            
            session = ActiveSession(
                user_id=user.id,
                session_token=SecurityUtils.generate_secure_token(),
                refresh_token="",  # Will be set below
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
                last_activity=datetime.now(timezone.utc)
            )
            
            self.db.add(session)
            await self.db.flush()  # Get session ID
            
            # Create tokens
            access_token = JWTManager.create_access_token({
                "sub": str(user.id),
                "email": user.email,
                "session_id": session.id
            })
            
            refresh_token = JWTManager.create_refresh_token({
                "sub": str(user.id),
                "session_id": session.id
            })
            
            # Update session with hashed refresh token
            session.refresh_token = SecurityUtils.hash_token(refresh_token)
            
            await self.db.commit()
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.access_token_expire_minutes * 60,
                user=UserResponse.model_validate(user)
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating session"
            )
    
    async def _cleanup_expired_sessions(self, user_id: int):
        """Clean up expired sessions for a user"""
        try:
            await self.db.execute(
                update(ActiveSession)
                .where(
                    and_(
                        ActiveSession.user_id == user_id,
                        ActiveSession.expires_at <= datetime.now(timezone.utc)
                    )
                )
                .values(is_active=False)
            )
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
    
    async def verify_session(self, access_token: str) -> Tuple[User, ActiveSession]:
        """Verify access token and return user and session"""
        try:
            # Decode token
            payload = JWTManager.verify_token(access_token, "access")
            user_id = int(payload.get("sub"))
            session_id = payload.get("session_id")
            
            # Get user and session
            result = await self.db.execute(
                select(User, ActiveSession)
                .join(ActiveSession, User.id == ActiveSession.user_id)
                .where(
                    and_(
                        User.id == user_id,
                        ActiveSession.id == session_id,
                        ActiveSession.is_active == True,
                        ActiveSession.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
            user_session = result.first()
            
            if not user_session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session"
                )
            
            user, session = user_session
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is disabled"
                )
            
            # Update last activity
            session.last_activity = datetime.now(timezone.utc)
            await self.db.commit()
            
            return user, session
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session verification failed"
            )