"""
프로덕션 레벨 설정 관리
환경 변수 기반 설정, 검증, 타입 안전성
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseSettings, PostgresDsn, RedisDsn, validator, Field
from pydantic.networks import AnyHttpUrl
import secrets
import os
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    APP_NAME: str = "Dropshipping Automation System"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = Field("production", regex="^(development|staging|production)$")
    
    # 보안
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    
    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] = []
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 데이터베이스
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: RedisDsn
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_DECODE_RESPONSES: bool = True
    
    # API 키 (암호화 필요)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # 마켓플레이스 API
    COUPANG_ACCESS_KEY: Optional[str] = None
    COUPANG_SECRET_KEY: Optional[str] = None
    COUPANG_VENDOR_ID: Optional[str] = None
    
    NAVER_CLIENT_ID: Optional[str] = None
    NAVER_CLIENT_SECRET: Optional[str] = None
    
    ELEVENTH_API_KEY: Optional[str] = None
    
    # 도매 API
    ZENTRADE_API_KEY: Optional[str] = None
    OWNERCLAN_API_KEY: Optional[str] = None
    DOMEGGOOK_API_KEY: Optional[str] = None
    
    # 이메일
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str = APP_NAME
    
    # 파일 업로드
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".xlsx", ".csv"]
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[Path] = Path("./logs/app.log")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # 모니터링
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    
    # 백업
    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"  # Cron 형식
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_S3_BUCKET: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-northeast-2"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_STORAGE_URL: Optional[RedisDsn] = None
    
    # 웹훅
    WEBHOOK_SECRET: Optional[str] = None
    WEBHOOK_TIMEOUT: int = 30
    
    # 기타
    TIMEZONE: str = "Asia/Seoul"
    LANGUAGE: str = "ko"
    CURRENCY: str = "KRW"
    
    # 프로젝트 경로
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: Optional[str]) -> str:
        if not v:
            return secrets.token_urlsafe(32)
        if len(v) < 32:
            raise ValueError("SECRET_KEY는 최소 32자 이상이어야 합니다")
        return v
    
    @validator("LOG_FILE", pre=True)
    def create_log_dir(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[Path]:
        if v:
            log_path = Path(v)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            return log_path
        return None
    
    @validator("UPLOAD_DIR", pre=True)
    def create_upload_dir(cls, v: str) -> Path:
        upload_path = Path(v)
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path
    
    @property
    def database_url_async(self) -> str:
        """비동기 데이터베이스 URL"""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENVIRONMENT == "production"
    
    @property
    def redis_url_with_password(self) -> str:
        """비밀번호가 포함된 Redis URL"""
        if self.REDIS_PASSWORD:
            redis_url = str(self.REDIS_URL)
            return redis_url.replace("redis://", f"redis://:{self.REDIS_PASSWORD}@")
        return str(self.REDIS_URL)
    
    def get_api_key(self, service: str) -> Optional[str]:
        """서비스별 API 키 반환"""
        api_keys = {
            "openai": self.OPENAI_API_KEY,
            "anthropic": self.ANTHROPIC_API_KEY,
            "coupang": self.COUPANG_ACCESS_KEY,
            "naver": self.NAVER_CLIENT_ID,
            "11st": self.ELEVENTH_API_KEY,
            "zentrade": self.ZENTRADE_API_KEY,
            "ownerclan": self.OWNERCLAN_API_KEY,
            "domeggook": self.DOMEGGOOK_API_KEY,
        }
        return api_keys.get(service.lower())
    
    def mask_sensitive_data(self) -> Dict[str, Any]:
        """민감한 데이터를 마스킹한 설정 반환"""
        config_dict = self.dict()
        sensitive_keys = [
            "SECRET_KEY", "DATABASE_URL", "REDIS_PASSWORD",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "COUPANG_SECRET_KEY", "NAVER_CLIENT_SECRET",
            "SMTP_PASSWORD", "AWS_SECRET_ACCESS_KEY",
            "WEBHOOK_SECRET"
        ]
        
        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = "***MASKED***"
        
        return config_dict
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


# 싱글톤 인스턴스
settings = Settings()