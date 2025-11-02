from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generator, Optional
import json
import asyncio
from datetime import datetime
from database.database import get_db
from core.orchestrator import orchestrator
from schemas.schemas import AgentRequest
from config.logger import logger

router = APIRouter()


@router.post("/invoke")
async def invoke_agent(
    request: AgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Standard non-streaming agent invocation"""
    try:
        logger.info(f"Processing agent request: {request.query[:100]}...")
        
        # Process the request
        result = await orchestrator.process_request(db, request)
        
        return {
            "response": result["response"],
            "conversation_id": result["conversation_id"],
            "intent": result["intent"],
            "tokens_used": result.get("tokens_used", 0),
            "cost_usd": result.get("cost_usd", 0.0),
            "plan_description": result.get("plan_description", "")
        }
        
    except Exception as e:
        logger.error(f"Agent invocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoke-stream")
async def invoke_agent_stream(
    request: AgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Streaming agent invocation with real-time response"""
    
    async def generate_stream() -> Generator[str, None, None]:
        """Generate streaming response"""
        try:
            logger.info(f"Starting streaming request: {request.query[:100]}...")
            
            # Yield initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing your request...'})}\n\n"
            
            # Process the request
            result = await orchestrator.process_request(db, request)
            
            # If this is a direct answer, stream the response word by word
            if result["intent"] == "direct_answer":
                response_text = result["response"]
                words = response_text.split()
                
                for i, word in enumerate(words):
                    chunk_data = {
                        "type": "chunk",
                        "content": word + " ",
                        "conversation_id": result["conversation_id"],
                        "progress": f"{i+1}/{len(words)}"
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    # Small delay for streaming effect
                    await asyncio.sleep(0.05)
                
                # Send final message
                final_data = {
                    "type": "complete",
                    "response": response_text,
                    "conversation_id": result["conversation_id"],
                    "tokens_used": result.get("tokens_used", 0),
                    "cost_usd": result.get("cost_usd", 0.0),
                    "intent": result["intent"]
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                
            else:
                # For plan execution, show step-by-step progress
                plan_description = result.get("plan_description", "Executing plan...")
                
                steps = ["Analyzing request", "Creating plan", "Executing tools", "Compiling results"]
                
                for i, step in enumerate(steps):
                    step_data = {
                        "type": "step",
                        "step": step,
                        "progress": f"{i+1}/{len(steps)}",
                        "conversation_id": result["conversation_id"]
                    }
                    yield f"data: {json.dumps(step_data)}\n\n"
                    await asyncio.sleep(0.3)
                
                # Send final response
                final_data = {
                    "type": "complete", 
                    "response": result["response"],
                    "conversation_id": result["conversation_id"],
                    "tokens_used": result.get("tokens_used", 0),
                    "cost_usd": result.get("cost_usd", 0.0),
                    "intent": result["intent"],
                    "plan_description": plan_description
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        
        # Send end marker
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation messages"""
    try:
        from sqlalchemy import text
        
        # Get conversation info
        conv_result = await db.execute(
            text("""
                SELECT c.*, u.username 
                FROM conversations c 
                JOIN users u ON c.user_id = u.id 
                WHERE c.id = :conversation_id
            """),
            {"conversation_id": conversation_id}
        )
        
        conversation = conv_result.fetchone()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        msg_result = await db.execute(
            text("""
                SELECT role, content, tokens_used, cost_usd, created_at
                FROM messages 
                WHERE conversation_id = :conversation_id 
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            """),
            {"conversation_id": conversation_id, "limit": limit, "offset": offset}
        )
        
        messages = []
        for row in msg_result.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "tokens_used": row[2],
                "cost_usd": float(row[3]) if row[3] else 0.0,
                "created_at": row[4].isoformat() if row[4] else None
            })
        
        # Reverse to get chronological order
        messages.reverse()
        
        return {
            "conversation": {
                "id": conversation[0],
                "user_id": conversation[1],
                "username": conversation[6],
                "title": conversation[2],
                "summary": conversation[3],
                "total_messages": conversation[4],
                "created_at": conversation[5].isoformat() if conversation[5] else None,
                "updated_at": conversation[7].isoformat() if conversation[7] else None
            },
            "messages": messages,
            "has_more": len(messages) == limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))