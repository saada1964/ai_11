from fastapi import FastAPI, Depends, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
import json
import asyncio
from typing import Generator
from config.settings import settings
from config.logger import setup_logging, logger
from database.database import init_db, close_db
from core.orchestrator import orchestrator
from core.tools import tool_registry
from core.accounting import accounting_service
from api.endpoints import agent, models, tools, conversations, health, auth
from api.credit_api import credit_router
from middleware.auth_middleware import AuthMiddleware, RateLimitMiddleware
from api.endpoints import websocket as websocket_router
from schemas.schemas import AgentRequest

# Setup logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title="AI Agent Kernel",
    description="Dynamic AI Agent Kernel with multi-user support and extensible tools",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add custom middleware
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(models.router, prefix="/models", tags=["Models"])
app.include_router(tools.router, prefix="/tools", tags=["Tools"])
app.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
app.include_router(credit_router, prefix="/credit", tags=["Credit"])

#app.include_router(websocket_router.router, prefix="", tags=["WebSocket"])
app.include_router(websocket_router.router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting AI Agent Kernel...")
        
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize tool registry with default tools
        default_tools = [
            {
                "name": "web_search_serper",
                "description": "Fast web search using Serper.dev",
                "function_name": "web_search_serper",
                "price_usd": 0.001,
                "api_key_name": "SERPER_API_KEY",
                "is_active": True,
                "parameters": {"query": "search query string"}
            },
            {
                "name": "wikipedia_search", 
                "description": "Search Wikipedia articles",
                "function_name": "wikipedia_search",
                "price_usd": 0.0001,
                "api_key_name": None,
                "is_active": True,
                "parameters": {"query": "search query", "language": "en"}
            },
            {
                "name": "advanced_calculator",
                "description": "Safe mathematical calculator",
                "function_name": "advanced_calculator", 
                "price_usd": 0.00001,
                "api_key_name": None,
                "is_active": True,
                "parameters": {"expression": "mathematical expression"}
            }
        ]
        
        #tool_registry.load_tools_to_db(default_tools)
        logger.info("Tool registry initialized")
        
        logger.info("AI Agent Kernel started successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Shutting down AI Agent Kernel...")
        
        # Close database connections
        await close_db()
        
        logger.info("AI Agent Kernel shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Add custom exception handlers





@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging and a valid JSONResponse."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
    status_code=exc.status_code,
    content={"detail": exc.detail},
    headers=exc.headers
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions with a valid JSONResponse."""
    logger.error(f"Unexpected error: {exc} - {request.url}", exc_info=True) # exc_info=True لطباعة Traceback
    return JSONResponse(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    content={"detail": "An internal server error occurred."}
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "AI Agent Kernel",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "endpoints": {
            "health": "/health",
            "auth": "/auth",
            "agent": "/agent/invoke", 
            "models": "/models",
            "tools": "/tools",
            "conversations": "/conversations",
            "credit": "/credit",
            "websocket": "/ws"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )