from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    balance: Optional[int] = None
    memory_profile: Optional[Dict[str, Any]] = None


class User(UserBase):
    id: int
    balance: int
    memory_profile: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# LLM Model Schemas
class LLMModelBase(BaseModel):
    name: str
    provider: str
    api_endpoint: Optional[str] = None
    api_standard: str
    price_per_million_tokens: float
    role: str
    max_tokens: Optional[int] = 4000
    temperature: Optional[float] = 0.7
    is_active: Optional[bool] = True


class LLMModelCreate(LLMModelBase):
    pass


class LLMModel(LLMModelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Tool Schemas
class ToolBase(BaseModel):
    name: str
    description: str
    function_name: str
    price_usd: Optional[float] = 0.0
    api_key_name: Optional[str] = None
    is_active: Optional[bool] = True
    parameters: Optional[Dict[str, Any]] = None


class ToolCreate(ToolBase):
    pass


class Tool(ToolBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Conversation Schemas
class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    user_id: int


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None


class Conversation(ConversationBase):
    id: int
    user_id: int
    summary: Optional[str]
    total_messages: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Message Schemas
class MessageBase(BaseModel):
    role: str
    content: str


class MessageCreate(MessageBase):
    conversation_id: int
    user_id: int
    tokens_used: Optional[int] = 0
    cost_usd: Optional[float] = 0.0


class Message(MessageBase):
    id: int
    conversation_id: int
    user_id: int
    tokens_used: int
    cost_usd: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# File Schemas
class FileBase(BaseModel):
    filename: str
    original_filename: str
    file_type: Optional[str] = None


class FileUpload(FileBase):
    user_id: int


class File(FileBase):
    id: int
    user_id: int
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    processing_status: str
    vector_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Agent Request Schemas
class AgentRequest(BaseModel):
    query: str
    user_id: int
    conversation_id: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class AgentResponse(BaseModel):
    response: str
    usage_log_id: int
    conversation_id: int
    tokens_used: int
    cost_usd: float