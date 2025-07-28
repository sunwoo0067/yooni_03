from loguru import logger
from config.settings import settings
import sys

def setup_logger():
    """로거 설정"""
    
    # 기본 로거 제거
    logger.remove()
    
    # 콘솔 로거 추가
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 파일 로거 추가 (설정된 경우)
    if settings.LOG_FILE:
        logger.add(
            settings.LOG_FILE,
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",  # 10MB마다 로테이션
            retention="30 days",  # 30일 보관
            compression="zip"  # 압축 저장
        )
    
    return logger

# 글로벌 로거 인스턴스
app_logger = setup_logger()