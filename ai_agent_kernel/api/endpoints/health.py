from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.database import get_db
from config.settings import settings
from config.logger import logger

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Basic health check endpoint"""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "AI Agent Kernel",
            "version": "1.0.0",
            "environment": settings.environment,
            "database": "connected",
            "debug": settings.debug
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail="Service unhealthy"
        )


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with system information"""
    try:
        # Database check
        db_result = await db.execute(text("SELECT version(), current_database(), current_user"))
        db_info = db_result.fetchone()
        
        # Count active models
        models_result = await db.execute(
            text("SELECT COUNT(*) FROM llm_models WHERE is_active = true")
        )
        active_models = models_result.scalar()
        
        # Count active tools
        tools_result = await db.execute(
            text("SELECT COUNT(*) FROM tools WHERE is_active = true")
        )
        active_tools = tools_result.scalar()
        
        return {
            "status": "healthy",
            "service": "AI Agent Kernel",
            "version": "1.0.0",
            "environment": settings.environment,
            "debug": settings.debug,
            "components": {
                "database": {
                    "status": "connected",
                    "version": db_info[0] if db_info else "unknown",
                    "database": db_info[1] if db_info else "unknown",
                    "user": db_info[2] if db_info else "unknown"
                },
                "models": {
                    "status": "available" if active_models > 0 else "none",
                    "active_count": active_models,
                    "default_planner": settings.default_planner_model
                },
                "tools": {
                    "status": "available" if active_tools > 0 else "none", 
                    "active_count": active_tools,
                    "available_tools": settings.available_tools
                }
            },
            "configuration": {
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "redis_url": settings.redis_url
            }
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "components": {
                "database": {"status": "disconnected"},
                "models": {"status": "unknown"},
                "tools": {"status": "unknown"}
            }
        }