"""
통합된 애플리케이션 설정
V2의 프로덕션 레벨 기능과 V1의 AI 설정을 결합
"""
import os
import secrets
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from functools import lru_cache
from pydantic import Field, validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """애플리케이션 환경"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """통합 애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    # ==================
    # 애플리케이션 기본 설정
    # ==================
    PROJECT_NAME: str = Field(default="Yooni Dropshipping System", description="프로젝트 이름")
    VERSION: str = Field(default="1.0.0", description="API 버전")
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT, description="실행 환경")
    DEBUG: bool = Field(default=False, description="디버그 모드")
    
    # main.py 호환성을 위한 별칭
    @property
    def APP_NAME(self) -> str:
        return self.PROJECT_NAME
    
    @property
    def APP_VERSION(self) -> str:
        return self.VERSION
    
    # API 설정
    API_V1_STR: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = Field(default=["*"])
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004", "http://localhost:3005", "http://localhost:3006", "http://localhost:3010"]
    )
    
    # CORS 설정 (main.py에서 사용하는 이름으로 추가)
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return self.BACKEND_CORS_ORIGINS
    
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # ==================
    # 보안 설정
    # ==================
    SECRET_KEY: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe(32)))
    JWT_SECRET_KEY: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe(32)))
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 암호화
    ENCRYPTION_KEY: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe(32)))
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # 이메일 설정
    SMTP_HOST: str = Field(default="", description="SMTP 서버 호스트")
    SMTP_PORT: int = Field(default=587, description="SMTP 서버 포트")
    SMTP_USERNAME: str = Field(default="", description="SMTP 사용자명")
    SMTP_PASSWORD: SecretStr = Field(default_factory=lambda: SecretStr(""), description="SMTP 비밀번호")
    SMTP_FROM_EMAIL: str = Field(default="noreply@yooni.com", description="발신자 이메일")
    SMTP_FROM_NAME: str = Field(default="Yooni Dropshipping", description="발신자 이름")
    SMTP_TLS: bool = Field(default=True, description="TLS 사용 여부")
    
    # 프론트엔드 URL
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="프론트엔드 URL")
    
    # ==================
    # 데이터베이스 설정
    # ==================
    DATABASE_URL: str = Field(
        default="sqlite:///./yooni_dropshipping.db",
        description="메인 데이터베이스 URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DATABASE_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DATABASE_ECHO: bool = False
    
    # 백업 설정
    BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL_HOURS: int = 24
    BACKUP_RETENTION_DAYS: int = 7
    BACKUP_PATH: str = "./backups"
    
    # ==================
    # AI 서비스 설정 (V1에서 통합)
    # ==================
    # Google Gemini
    GEMINI_API_KEY: Optional[SecretStr] = None
    GEMINI_MODEL: str = "gemini-pro"
    
    # Ollama (로컬 LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    
    # OpenAI
    OPENAI_API_KEY: Optional[SecretStr] = None
    OPENAI_MODEL: str = "gpt-4"
    
    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet"
    
    # AI 공통 설정
    DEFAULT_AI_PROVIDER: str = "gemini"  # gemini, openai, anthropic, ollama
    AI_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    AI_MAX_TOKENS: int = Field(default=1024, ge=1, le=32000)
    AI_TIMEOUT_SECONDS: int = 60
    AI_MAX_RETRIES: int = 3
    AI_CACHE_ENABLED: bool = True
    AI_CACHE_TTL_SECONDS: int = 3600
    
    # ==================
    # 마켓플레이스 API 설정
    # ==================
    # 쿠팡
    COUPANG_ACCESS_KEY: Optional[SecretStr] = None
    COUPANG_SECRET_KEY: Optional[SecretStr] = None
    COUPANG_VENDOR_ID: Optional[str] = None
    COUPANG_API_URL: str = "https://api-gateway.coupang.com"
    
    # 네이버
    NAVER_CLIENT_ID: Optional[SecretStr] = None
    NAVER_CLIENT_SECRET: Optional[SecretStr] = None
    NAVER_STORE_ID: Optional[str] = None
    NAVER_API_URL: str = "https://api.commerce.naver.com"
    
    # 11번가
    ELEVEN_ST_API_KEY: Optional[SecretStr] = None
    ELEVEN_ST_SECRET_KEY: Optional[SecretStr] = None
    ELEVEN_ST_SELLER_ID: Optional[str] = None
    ELEVEN_ST_API_URL: str = "https://api.11st.co.kr"
    
    # ==================
    # 도매 사이트 설정
    # ==================
    # 오너클랜
    OWNERCLAN_USERNAME: Optional[str] = None
    OWNERCLAN_PASSWORD: Optional[SecretStr] = None
    OWNERCLAN_API_URL: str = "https://api-sandbox.ownerclan.com/v1/graphql"
    
    # 도매꾹
    DOMEGGOOK_API_KEY: Optional[SecretStr] = None
    DOMEGGOOK_API_URL: str = "https://domeggook.com/api/v2"
    
    # 젠트레이드
    ZENTRADE_ACCESS_KEY: Optional[SecretStr] = None
    ZENTRADE_SECRET_KEY: Optional[SecretStr] = None
    ZENTRADE_API_URL: str = "https://api.zentrade.co.kr"
    
    # ==================
    # 캐싱 및 큐 설정
    # ==================
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 300
    CACHE_KEY_PREFIX: str = "yooni:"
    
    # 캐시 압축 설정
    CACHE_COMPRESSION_ENABLED: bool = True
    CACHE_COMPRESSION_THRESHOLD: int = 1024  # 1KB 이상만 압축
    CACHE_COMPRESSION_LEVEL: int = 6  # gzip 압축 레벨 (1-9, 기본값 6)
    
    # ==================
    # Redis 설정
    # ==================
    REDIS_HOST: str = Field(default="localhost", description="Redis 호스트")
    REDIS_PORT: int = Field(default=6379, description="Redis 포트")
    REDIS_DB: int = Field(default=0, description="Redis 데이터베이스 번호")
    REDIS_PASSWORD: Optional[SecretStr] = Field(default=None, description="Redis 비밀번호")
    REDIS_SSL: bool = Field(default=False, description="Redis SSL 사용 여부")
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis 연결 풀 크기")
    
    # Redis Cluster 설정
    REDIS_CLUSTER_ENABLED: bool = False
    REDIS_CLUSTER_NODES: Optional[List[str]] = None  # ["host1:7000", "host2:7001", ...]
    REDIS_CLUSTER_PASSWORD: Optional[SecretStr] = None
    
    # Celery 설정
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_TIME_LIMIT: int = 300
    CELERY_TASK_SOFT_TIME_LIMIT: int = 240
    
    # ==================
    # 파일 업로드 설정
    # ==================
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_DOCUMENT_EXTENSIONS: List[str] = [".pdf", ".xlsx", ".csv", ".txt"]
    
    # ==================
    # 로깅 및 모니터링
    # ==================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # ==================
    # 레이트 리미팅
    # ==================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_STORAGE_URL: Optional[str] = None
    
    # ==================
    # 웹훅 설정
    # ==================
    WEBHOOK_TIMEOUT_SECONDS: int = 30
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_DELAY_SECONDS: int = 60
    
    # ==================
    # 검증 및 유틸리티 메서드
    # ==================
    @validator("ENVIRONMENT", pre=True)
    def validate_environment(cls, v: Union[str, Environment]) -> Environment:
        """환경 설정 검증"""
        if isinstance(v, str):
            try:
                return Environment(v.lower())
            except ValueError:
                raise ValueError(f"Invalid environment: {v}")
        return v
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: str, values: Dict[str, Any]) -> str:
        """데이터베이스 URL 검증 및 환경별 조정"""
        if not v:
            env = values.get("ENVIRONMENT", Environment.DEVELOPMENT)
            if env == Environment.DEVELOPMENT:
                return "sqlite:///./yooni_dropshipping.db"
            else:
                raise ValueError("DATABASE_URL must be set for non-development environments")
        return v
    
    @validator("LOG_LEVEL", pre=True)
    def validate_log_level(cls, v: str, values: Dict[str, Any]) -> str:
        """로그 레벨 환경별 조정"""
        env = values.get("ENVIRONMENT", Environment.DEVELOPMENT)
        if env == Environment.DEVELOPMENT and not v:
            return "DEBUG"
        elif env == Environment.PRODUCTION and not v:
            return "INFO"
        return v.upper()
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def is_staging(self) -> bool:
        """스테이징 환경 여부"""
        return self.ENVIRONMENT == Environment.STAGING
    
    def get_masked_value(self, key: str) -> str:
        """민감한 값 마스킹"""
        value = getattr(self, key, None)
        if value is None:
            return "Not Set"
        
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        
        if len(str(value)) <= 8:
            return "*" * len(str(value))
        
        visible_chars = 4
        return f"{str(value)[:visible_chars]}{'*' * (len(str(value)) - visible_chars * 2)}{str(value)[-visible_chars:]}"
    
    def get_db_settings(self) -> Dict[str, Any]:
        """데이터베이스 설정 반환"""
        return {
            "url": self.DATABASE_URL,
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_timeout": self.DATABASE_POOL_TIMEOUT,
            "echo": self.DATABASE_ECHO
        }
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """AI 서비스 설정 반환"""
        return {
            "provider": self.DEFAULT_AI_PROVIDER,
            "temperature": self.AI_TEMPERATURE,
            "max_tokens": self.AI_MAX_TOKENS,
            "timeout": self.AI_TIMEOUT_SECONDS,
            "cache_enabled": self.AI_CACHE_ENABLED,
            "models": {
                "gemini": self.GEMINI_MODEL,
                "openai": self.OPENAI_MODEL,
                "anthropic": self.ANTHROPIC_MODEL,
                "ollama": self.OLLAMA_MODEL
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스 반환 (캐싱)"""
    return Settings()


# 개발 환경 간편 설정 헬퍼
class DevelopmentSettings(Settings):
    """개발 환경 전용 설정"""
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./yooni_dev.db"
    LOG_LEVEL: str = "DEBUG"
    DATABASE_ECHO: bool = True
    BACKUP_ENABLED: bool = False
    RATE_LIMIT_ENABLED: bool = False


# 설정 내보내기
settings = get_settings()