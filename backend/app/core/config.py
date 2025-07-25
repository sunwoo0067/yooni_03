"""
Application configuration settings.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "Yooni E-commerce Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TESTING: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:1234@localhost:5433/yoni_03"
    
    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI Services
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_AI_MODEL: str = "gemini-pro"
    OLLAMA_MODEL: str = "llama2"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 1024
    
    # Marketplace Platform API Keys
    # Coupang
    COUPANG_ACCESS_KEY: Optional[str] = None
    COUPANG_SECRET_KEY: Optional[str] = None
    COUPANG_VENDOR_ID: Optional[str] = None
    
    # Naver Shopping
    NAVER_CLIENT_ID: Optional[str] = None
    NAVER_CLIENT_SECRET: Optional[str] = None
    NAVER_STORE_ID: Optional[str] = None
    
    # 11번가 (11st)
    ELEVENTH_STREET_API_KEY: Optional[str] = None
    ELEVENTH_STREET_SECRET_KEY: Optional[str] = None
    ELEVENTH_STREET_SELLER_ID: Optional[str] = None
    
    # Additional Platform Keys
    GMARKET_API_KEY: Optional[str] = None
    AUCTION_API_KEY: Optional[str] = None
    INTERPARK_API_KEY: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # File Upload
    MAX_FILE_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "uploads/"
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "pdf", "csv", "xlsx"]
    
    # Background Tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    HEALTH_CHECK_INTERVAL: int = 300  # 5 minutes
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @field_validator("CORS_ALLOW_METHODS", mode="before")
    @classmethod
    def assemble_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def assemble_allowed_extensions(cls, v):
        """Parse allowed extensions from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
    
    @property
    def database_url_async(self) -> str:
        """Get asynchronous database URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings


# Database configuration for different environments
class DatabaseConfig:
    """Database configuration helper."""
    
    @staticmethod
    def get_url(async_mode: bool = False) -> str:
        """Get database URL for sync or async connections."""
        if async_mode:
            return settings.database_url_async
        return settings.database_url_sync
    
    @staticmethod
    def get_connection_args() -> dict:
        """Get database connection arguments."""
        return {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 10,
            "max_overflow": 20,
        }
    
    @staticmethod
    def get_async_connection_args() -> dict:
        """Get async database connection arguments."""
        return {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 10,
            "max_overflow": 20,
        }


# AI Configuration
class AIConfig:
    """AI service configuration helper."""
    
    @staticmethod
    def get_gemini_config() -> dict:
        """Get Gemini API configuration."""
        return {
            "api_key": settings.GEMINI_API_KEY,
            "model": settings.DEFAULT_AI_MODEL,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
        }
    
    @staticmethod
    def get_ollama_config() -> dict:
        """Get Ollama configuration."""
        return {
            "base_url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
        }


# Marketplace Configuration
class MarketplaceConfig:
    """Marketplace platform configuration helper."""
    
    @staticmethod
    def get_coupang_config() -> dict:
        """Get Coupang API configuration."""
        return {
            "access_key": settings.COUPANG_ACCESS_KEY,
            "secret_key": settings.COUPANG_SECRET_KEY,
            "vendor_id": settings.COUPANG_VENDOR_ID,
        }
    
    @staticmethod
    def get_naver_config() -> dict:
        """Get Naver Shopping API configuration."""
        return {
            "client_id": settings.NAVER_CLIENT_ID,
            "client_secret": settings.NAVER_CLIENT_SECRET,
            "store_id": settings.NAVER_STORE_ID,
        }
    
    @staticmethod
    def get_eleventh_street_config() -> dict:
        """Get 11번가 API configuration."""
        return {
            "api_key": settings.ELEVENTH_STREET_API_KEY,
            "secret_key": settings.ELEVENTH_STREET_SECRET_KEY,
            "seller_id": settings.ELEVENTH_STREET_SELLER_ID,
        }