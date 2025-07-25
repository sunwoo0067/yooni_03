"""
로깅 유틸리티
구조화된 로깅, 로그 로테이션, 다중 핸들러 지원
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import traceback

from ..core.config_v2 import settings


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 변환"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
        }
        
        # 추가 필드
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        
        # 예외 정보
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """컬러 출력 포매터 (개발 환경용)"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """컬러가 적용된 로그 메시지 생성"""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: Optional[str] = None,
    level: Optional[str] = None
) -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name or "dropshipping")
    
    # 이미 설정된 경우 스킵
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level or settings.LOG_LEVEL.upper()))
    logger.propagate = False
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.is_development:
        # 개발 환경: 컬러 포맷
        console_formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        # 프로덕션 환경: JSON 포맷
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (설정된 경우)
    if settings.LOG_FILE:
        try:
            # 로그 디렉토리 생성
            log_dir = settings.LOG_FILE.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 로테이팅 파일 핸들러
            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(settings.LOG_FILE),
                maxBytes=settings.LOG_MAX_SIZE,
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            
            # 파일은 항상 JSON 포맷
            file_formatter = JSONFormatter()
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.error(f"Failed to setup file handler: {e}")
    
    # 에러 로그 별도 파일 (ERROR 이상만)
    if settings.LOG_FILE:
        try:
            error_log_path = settings.LOG_FILE.parent / "error.log"
            error_handler = logging.handlers.RotatingFileHandler(
                filename=str(error_log_path),
                maxBytes=settings.LOG_MAX_SIZE,
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JSONFormatter())
            logger.addHandler(error_handler)
            
        except Exception as e:
            logger.error(f"Failed to setup error handler: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 가져오기"""
    return logging.getLogger(name)


class LoggerMixin:
    """로거 믹스인 클래스"""
    
    @property
    def logger(self) -> logging.Logger:
        """로거 속성"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def log_info(self, message: str, **kwargs):
        """INFO 로그"""
        self.logger.info(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """WARNING 로그"""
        self.logger.warning(message, extra=kwargs)
    
    def log_error(self, message: str, exc_info: bool = True, **kwargs):
        """ERROR 로그"""
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """DEBUG 로그"""
        self.logger.debug(message, extra=kwargs)


def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    logger = get_logger(func.__module__)
    
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func_name} failed: {e}", exc_info=True)
            raise
    
    return wrapper


# 기본 로거 설정
root_logger = setup_logger()