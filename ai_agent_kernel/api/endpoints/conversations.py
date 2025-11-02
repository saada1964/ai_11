"""
Enhanced conversations API with authentication and proper ORM usage
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, delete, and_, func
from typing import List, Optional
from datetime import datetime, timezone

from database.database import get_db
from models.models import Conversation, Message, User
from schemas.auth_schemas import UserResponse
from api.dependencies import get_current_active_user
from config.logger import logger


router = APIRouter()


# Pydantic models for conversations
from pydantic import BaseModel

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    summary: Optional[str] = None

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    summary: Optional[str]
    total_messages: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    per_page: int

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    role: str
    content: str
    tokens_used: int
    cost_usd: float
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation for the authenticated user"""
    try:
        conversation = Conversation(
            user_id=current_user.id,
            title=conversation_data.title or "New Conversation",
            summary=conversation_data.summary
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(f"Conversation created: {conversation.id} for user {current_user.id}")
        
        return ConversationResponse.model_validate(conversation)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Create conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.get("/", response_model=ConversationListResponse)
async def get_user_conversations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of conversations to return")
):
    """Get conversations for the authenticated user"""
    try:
        # Get total count
        count_result = await db.execute(
            select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
        )
        total = count_result.scalar()
        
        # Get conversations
        conversations_query = select(Conversation).where(
            Conversation.user_id == current_user.id
        ).order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
        
        result = await db.execute(conversations_query)
        conversations = result.scalars().all()
        
        conversation_responses = [
            ConversationResponse.model_validate(conv) for conv in conversations
        ]
        
        return ConversationListResponse(
            conversations=conversation_responses,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit
        )
        
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation (only if owned by user)"""
    try:
        result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return ConversationResponse.model_validate(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a conversation (only if owned by user)"""
    try:
        # Get conversation
        result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        for field, value in update_dict.items():
            setattr(conversation, field, value)
        
        conversation.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(f"Conversation updated: {conversation_id} by user {current_user.id}")
        
        return ConversationResponse.model_validate(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation (only if owned by user)"""
    try:
        # Get conversation
        result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete conversation (cascade will delete messages)
        await db.delete(conversation)
        await db.commit()
        
        logger.info(f"Conversation deleted: {conversation_id} by user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return")
):
    """Get messages from a conversation (only if owned by user)"""
    try:
        # Verify conversation ownership
        conv_result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages_query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(skip).limit(limit)
        
        result = await db.execute(messages_query)
        messages = result.scalars().all()
        
        return [MessageResponse.model_validate(msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation messages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.post("/{conversation_id}/summary", response_model=dict)
async def update_conversation_summary(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate and update conversation summary using AI"""
    try:
        # Verify conversation ownership
        conv_result = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get recent messages for summary
        messages_query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(20)
        
        result = await db.execute(messages_query)
        messages = result.scalars().all()
        
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No messages to summarize"
            )
        
        # Generate summary using AI (placeholder implementation)
        try:
            # This would integrate with your AI system
            # For now, create a simple summary
            message_count = len(messages)
            recent_topics = []
            
            for msg in messages:
                if len(msg.content) > 50:
                    recent_topics.append(msg.content[:50] + "...")
                if len(recent_topics) >= 3:
                    break
            
            if recent_topics:
                summary = f"Conversation covering {', '.join(recent_topics[:2])} and other topics ({message_count} messages)"
            else:
                summary = f"Conversation with {message_count} messages"
            
        except Exception:
            summary = f"Conversation with {len(messages)} messages"
        
        # Update conversation summary
        conversation.summary = summary
        conversation.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Summary updated for conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "summary": summary,
            "messages_analyzed": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update conversation summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update summary"
        )