"""
Authentication related Pydantic schemas
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class UserRegister(BaseModel):
    """User registration schema"""
    
    # ## ==> ==> ==> التصحيح الأول: regex -> pattern <== <== <==
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern="^[a-zA-Z0-9_-]+$"
    )
    
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    # ## ==> ==> ==> التصحيح الثاني: @validator -> @field_validator <== <== <==
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Validates and sanitizes the username.
        """
        # 1. تحويل إلى أحرف صغيرة أولاً
        v_lower = v.lower()
        
        # 2. التحقق من الأسماء المحجوزة
        if v_lower in ['admin', 'root', 'system', 'api', 'null', 'undefined']:
            raise ValueError('Username not allowed')
            
        # 3. إرجاع القيمة النظيفة
        return v_lower

class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: str
    balance: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class SessionInfo(BaseModel):
    """Session information schema"""
    id: int
    device_info: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    last_activity: datetime
    created_at: datetime
    is_current: bool = False
    
    class Config:
        from_attributes = True


class ActiveSessionsResponse(BaseModel):
    """Active sessions response schema"""
    sessions: list[SessionInfo]
    total_count: int


class LogoutRequest(BaseModel):
    """Logout request schema"""
    logout_all: bool = False


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class ResetPasswordRequest(BaseModel):
    """Reset password request schema"""
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    """Reset password confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8)


class DeviceInfo(BaseModel):
    """Device information schema"""
    device_type: Optional[str] = None  # mobile, desktop, tablet
    os: Optional[str] = None
    browser: Optional[str] = None
    app_version: Optional[str] = None


class AuthResponse(BaseModel):
    """Generic auth response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None