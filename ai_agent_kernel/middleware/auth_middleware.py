"""
Authentication middleware for FastAPI
"""

import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.logger import logger
from config.settings import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication and security middleware
    """
    
    def __init__(self, app, excluded_paths: list[str] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/auth/register", "/auth/login", "/auth/refresh",
            "/", "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Record start time for performance monitoring
        start_time = time.time()
        
        try:
            # Skip middleware for excluded paths
            if self._is_excluded_path(request.url.path):
                response = await call_next(request)
                self._log_request(request, response, start_time)
                return response
            
            # Add security headers to all responses
            response = await call_next(request)
            self._add_security_headers(response)
            self._log_request(request, response, start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"}
            )
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from authentication"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    def _log_request(self, request: Request, response: Response, start_time: float) -> None:
        """Log request information"""
        process_time = time.time() - start_time
        
        # Log level based on response status
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"
        else:
            log_level = "info"
        
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", "")[:100]  # Truncate for logging
        }
        
        getattr(logger, log_level)(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s",
            extra=log_data
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP (behind proxy)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis for this
        self.window_size = 60  # 1 minute window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute"
                },
                headers={"Retry-After": "60"}
            )
        
        # Record request
        self._record_request(client_ip, current_time)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited"""
        if client_ip not in self.request_counts:
            return False
        
        # Count requests in current window
        recent_requests = [
            timestamp for timestamp in self.request_counts[client_ip]
            if current_time - timestamp < self.window_size
        ]
        
        return len(recent_requests) >= self.requests_per_minute
    
    def _record_request(self, client_ip: str, current_time: float) -> None:
        """Record a request for rate limiting"""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        self.request_counts[client_ip].append(current_time)
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old entries to prevent memory leak"""
        cutoff_time = current_time - self.window_size
        
        for client_ip in list(self.request_counts.keys()):
            self.request_counts[client_ip] = [
                timestamp for timestamp in self.request_counts[client_ip]
                if timestamp > cutoff_time
            ]
            
            # Remove empty entries
            if not self.request_counts[client_ip]:
                del self.request_counts[client_ip]


class CORSMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware with enhanced security
    """
    
    def __init__(
        self, 
        app, 
        allowed_origins: list[str] = None,
        allowed_methods: list[str] = None,
        allowed_headers: list[str] = None
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"] if settings.debug else []
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or [
            "Authorization", "Content-Type", "X-Requested-With", "Accept"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("Origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: str = None) -> None:
        """Add CORS headers to response"""
        if origin and (origin in self.allowed_origins or "*" in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours