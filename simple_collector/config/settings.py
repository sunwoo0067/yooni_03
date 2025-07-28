from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://postgres:1234@localhost:5433/yoni_03"
    
    # API 설정
    API_TITLE: str = "Simple Product Collector"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "단순화된 상품 수집 시스템"
    
    # 로그 설정
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/app.log"
    
    # 수집 설정
    COLLECTION_BATCH_SIZE: int = 100
    OWNERCLAN_CACHE_SIZE: int = 5000  # 오너클랜 캐시 크기
    
    # 도매처 API 키 (환경변수에서 로드)
    # Zentrade
    ZENTRADE_API_ID: Optional[str] = None
    ZENTRADE_API_KEY: Optional[str] = None
    ZENTRADE_BASE_URL: str = "https://www.zentrade.co.kr/shop/proc"
    
    # OwnerClan
    OWNERCLAN_USERNAME: Optional[str] = None
    OWNERCLAN_PASSWORD: Optional[str] = None
    OWNERCLAN_API_URL: str = "https://api.ownerclan.com/v1/graphql"
    OWNERCLAN_AUTH_URL: str = "https://auth.ownerclan.com/auth"
    
    # Domeggook
    DOMEGGOOK_API_KEY: Optional[str] = None
    DOMEGGOOK_BASE_URL: str = "https://openapi.domeggook.com"
    
    # 업로드 설정
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 설정 인스턴스 생성
settings = Settings()

# 디렉토리 생성
Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
if settings.LOG_FILE:
    Path(settings.LOG_FILE).parent.mkdir(exist_ok=True)