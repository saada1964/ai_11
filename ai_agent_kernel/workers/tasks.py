import os
import json
from typing import List, Dict, Any
from celery import current_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from config.logger import logger
from workers.celery import celery_app


# Create sync engine for Celery tasks
sync_engine = create_engine(
    settings.database_url_sync,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(sync_engine)


@celery_app.task(bind=True, name="process_file_task")
def process_file_task(self, file_id: int, file_path: str, user_id: int):
    """Process uploaded file for RAG (vector storage)"""
    try:
        logger.info(f"Processing file {file_id}: {file_path}")
        
        # Update file status to processing
        with SessionLocal() as db:
            db.execute(
                text("UPDATE files SET processing_status = 'processing' WHERE id = :file_id"),
                {"file_id": file_id}
            )
            db.commit()
        
        # Read and process file content
        file_content = read_file_content(file_path)
        
        if not file_content:
            raise ValueError("Could not read file content")
        
        # Split content into chunks
        chunks = split_text_into_chunks(file_content, chunk_size=500, overlap=50)
        
        # Create embeddings (placeholder - would use OpenAI embeddings in real implementation)
        embeddings = create_embeddings_placeholder(chunks)
        
        # Store chunks in database
        with SessionLocal() as db:
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                db.execute(
                    text("""
                        INSERT INTO file_chunks (file_id, chunk_index, content, embedding, file_meta_data)
                        VALUES (:file_id, :chunk_index, :content, :embedding, :meta_data)
                    """),
                    {
                        "file_id": file_id,
                        "chunk_index": i,
                        "content": chunk,
                        "embedding": f"[{','.join(map(str, embedding))}]",
                        "file_meta_data": json.dumps({"source": "uploaded_file", "chunk_size": len(chunk)})
                    }
                )
            
            # Update file status to completed
            db.execute(
                text("""
                    UPDATE files 
                    SET processing_status = 'completed', vector_count = :vector_count
                    WHERE id = :file_id
                """),
                {"file_id": file_id, "vector_count": len(chunks)}
            )
            db.commit()
        
        logger.info(f"File processing completed: {file_id} - {len(chunks)} chunks created")
        return {
            "status": "completed",
            "file_id": file_id,
            "chunks_created": len(chunks),
            "file_size": len(file_content)
        }
        
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        
        # Update file status to failed
        with SessionLocal() as db:
            db.execute(
                text("UPDATE files SET processing_status = 'failed' WHERE id = :file_id"),
                {"file_id": file_id}
            )
            db.commit()
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'file_id': file_id}
        )
        
        raise


@celery_app.task(bind=True, name="update_conversation_summary_task")
def update_conversation_summary_task(self, conversation_id: int):
    """Update conversation summary using recent messages"""
    try:
        logger.info(f"Updating conversation summary: {conversation_id}")
        
        with SessionLocal() as db:
            # Get recent messages
            result = db.execute(
                text("""
                    SELECT role, content 
                    FROM messages 
                    WHERE conversation_id = :conversation_id 
                    ORDER BY created_at DESC 
                    LIMIT 20
                """),
                {"conversation_id": conversation_id}
            )
            
            messages = []
            for row in result.fetchall():
                messages.append({"role": row[0], "content": row[1]})
            
            if len(messages) < 4:  # Only update if we have enough messages
                logger.info(f"Not enough messages to summarize conversation {conversation_id}")
                return {"status": "skipped", "reason": "insufficient_messages"}
            
            # Generate summary (placeholder implementation)
            summary = generate_conversation_summary(messages)
            
            # Update conversation
            db.execute(
                text("""
                    UPDATE conversations 
                    SET summary = :summary, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :conversation_id
                """),
                {"conversation_id": conversation_id, "summary": summary}
            )
            db.commit()
        
        logger.info(f"Conversation summary updated: {conversation_id}")
        return {
            "status": "completed",
            "conversation_id": conversation_id,
            "summary_length": len(summary),
            "messages_analyzed": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Conversation summary update failed: {e}")
        raise


@celery_app.task(bind=True, name="cleanup_old_files_task")
def cleanup_old_files_task(self, days_old: int = 30):
    """Clean up old uploaded files"""
    try:
        logger.info(f"Cleaning up files older than {days_old} days")
        
        with SessionLocal() as db:
            # Get old files
            result = db.execute(
                text("""
                    SELECT id, file_path 
                    FROM files 
                    WHERE created_at < CURRENT_DATE - INTERVAL ':days days'
                      AND processing_status = 'completed'
                """),
                {"days": days_old}
            )
            
            deleted_count = 0
            for row in result.fetchall():
                file_id, file_path = row
                
                try:
                    # Delete physical file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Delete from database
                    db.execute(
                        text("DELETE FROM files WHERE id = :file_id"),
                        {"file_id": file_id}
                    )
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_id}: {e}")
            
            db.commit()
        
        logger.info(f"Cleanup completed: {deleted_count} files deleted")
        return {
            "status": "completed",
            "deleted_files": deleted_count,
            "days_old": days_old
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise


@celery_app.task(bind=True, name="generate_usage_report_task")
def generate_usage_report_task(self, user_id: int = None, days: int = 7):
    """Generate usage report for users"""
    try:
        logger.info(f"Generating usage report: user_id={user_id}, days={days}")
        
        with SessionLocal() as db:
            if user_id:
                # Specific user report
                result = db.execute(
                    text("""
                        SELECT 
                            action_type,
                            SUM(cost_usd) as total_cost,
                            COUNT(*) as usage_count,
                            SUM(input_tokens + output_tokens) as total_tokens
                        FROM usage_logs 
                        WHERE user_id = :user_id 
                            AND created_at >= CURRENT_DATE - INTERVAL ':days days'
                        GROUP BY action_type
                    """),
                    {"user_id": user_id, "days": days}
                )
                
                user_result = db.execute(
                    text("SELECT username FROM users WHERE id = :user_id"),
                    {"user_id": user_id}
                )
                username = user_result.scalar() or f"User {user_id}"
                
                report_data = {
                    "user_id": user_id,
                    "username": username,
                    "period_days": days,
                    "by_action_type": {}
                }
                
                for row in result.fetchall():
                    action_type = row[0]
                    report_data["by_action_type"][action_type] = {
                        "total_cost": float(row[1]) if row[1] else 0.0,
                        "usage_count": row[2] or 0,
                        "total_tokens": row[3] or 0
                    }
            else:
                # Overall system report
                result = db.execute(
                    text("""
                        SELECT 
                            u.username,
                            ul.action_type,
                            SUM(ul.cost_usd) as total_cost,
                            COUNT(*) as usage_count,
                            SUM(ul.input_tokens + ul.output_tokens) as total_tokens
                        FROM usage_logs ul
                        JOIN users u ON ul.user_id = u.id
                        WHERE ul.created_at >= CURRENT_DATE - INTERVAL ':days days'
                        GROUP BY u.username, ul.action_type
                        ORDER BY u.username, ul.action_type
                    """),
                    {"days": days}
                )
                
                report_data = {
                    "period_days": days,
                    "overall": {
                        "total_users": 0,
                        "total_cost": 0.0,
                        "total_requests": 0
                    },
                    "by_user": {}
                }
                
                for row in result.fetchall():
                    username, action_type, total_cost, usage_count, total_tokens = row
                    
                    if username not in report_data["by_user"]:
                        report_data["by_user"][username] = {
                            "total_cost": 0.0,
                            "total_requests": 0,
                            "by_action_type": {}
                        }
                    
                    report_data["by_user"][username]["total_cost"] += float(total_cost) if total_cost else 0.0
                    report_data["by_user"][username]["total_requests"] += usage_count or 0
                    report_data["by_user"][username]["by_action_type"][action_type] = {
                        "total_cost": float(total_cost) if total_cost else 0.0,
                        "usage_count": usage_count or 0,
                        "total_tokens": total_tokens or 0
                    }
                
                # Calculate overall totals
                for username, user_data in report_data["by_user"].items():
                    report_data["overall"]["total_users"] += 1
                    report_data["overall"]["total_cost"] += user_data["total_cost"]
                    report_data["overall"]["total_requests"] += user_data["total_requests"]
        
        logger.info(f"Usage report generated: {report_data}")
        return {
            "status": "completed",
            "report_data": report_data
        }
        
    except Exception as e:
        logger.error(f"Usage report generation failed: {e}")
        raise


# Helper functions

def read_file_content(file_path: str) -> str:
    """Read content from various file types"""
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_path.endswith('.md'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_path.endswith('.pdf'):
            # Placeholder for PDF processing
            # Would use PyPDF2 or pdfplumber in real implementation
            return "PDF content extraction not implemented yet"
        elif file_path.endswith('.docx'):
            # Placeholder for DOCX processing
            # Would use python-docx in real implementation
            return "DOCX content extraction not implemented yet"
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def split_text_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending within the last 50 characters
            sentence_end = text.rfind('.', start + chunk_size - 50, end)
            if sentence_end > start:
                end = sentence_end + 1
            else:
                # Look for space
                space_pos = text.rfind(' ', start, end)
                if space_pos > start:
                    end = space_pos
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = max(start + chunk_size - overlap, end)
    
    return chunks


def create_embeddings_placeholder(texts: List[str]) -> List[List[float]]:
    """Create placeholder embeddings (would use OpenAI embeddings in real implementation)"""
    import random
    random.seed(42)  # For reproducible results
    
    embeddings = []
    for _ in texts:
        # Create a 1536-dimensional random vector (OpenAI ada-002 dimension)
        embedding = [random.uniform(-1, 1) for _ in range(1536)]
        embeddings.append(embedding)
    
    return embeddings


def generate_conversation_summary(messages: List[Dict[str, str]]) -> str:
    """Generate a simple conversation summary"""
    if not messages:
        return "Empty conversation."
    
    # Simple heuristic-based summary
    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
    
    summary_parts = []
    
    if user_messages:
        first_user_msg = user_messages[0]["content"][:100]
        summary_parts.append(f"Started with question about: {first_user_msg}")
    
    if len(user_messages) > 1:
        summary_parts.append(f"Involved {len(user_messages)} user interactions")
    
    if assistant_messages:
        summary_parts.append(f"Generated {len(assistant_messages)} responses")
    
    return ". ".join(summary_parts) + "."


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'cleanup_old_files_task',
        'schedule': 86400.0,  # Every 24 hours
        'kwargs': {'days_old': 30}
    },
    'update-conversation-summaries': {
        'task': 'update_conversation_summary_task',
        'schedule': 3600.0,  # Every hour
        'kwargs': {}  # This would need to iterate through conversations
    },
    'generate-daily-report': {
        'task': 'generate_usage_report_task',
        'schedule': 86400.0,  # Every 24 hours
        'kwargs': {'days': 1}
    }
}