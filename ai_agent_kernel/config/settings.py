from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/ai_agent_kernel"
    database_url_sync: str = "postgresql+psycopg2://postgres:password@localhost:5432/ai_agent_kernel"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API Keys
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    
    # Security & Authentication
    secret_key: str = "your-ultra-secure-secret-key-for-jwt-tokens-minimum-32-characters-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    max_sessions_per_user: int = 5
    
    # Password Security
    password_min_length: int = 8
    password_hash_rounds: int = 12
    
    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Model Settings
    default_planner_model: str = "llama-3.1-8b-instant"
    default_summarizer_model: str = "gpt-3.5-turbo"
    max_tokens: int = 4000
    temperature: float = 0.7
    
    # Tools
    available_tools: List[str] = ["web_search_serper", "wikipedia_search", "advanced_calculator"]
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()