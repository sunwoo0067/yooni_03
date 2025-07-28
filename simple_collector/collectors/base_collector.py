from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
from utils.logger import app_logger

@dataclass
class ProductData:
    """상품 데이터 클래스"""
    product_code: str
    product_info: Dict[str, Any]
    supplier: str

@dataclass
class CollectionResult:
    """수집 결과 클래스"""
    success: bool
    total_count: int = 0
    new_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class BaseCollector(ABC):
    """기본 수집기 추상 클래스"""
    
    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials
        self.logger = app_logger
        
    @property
    @abstractmethod
    def supplier_name(self) -> str:
        """공급사명"""
        pass
        
    @property
    @abstractmethod
    def supplier_code(self) -> str:
        """공급사 코드"""
        pass
        
    @abstractmethod
    def authenticate(self) -> bool:
        """API 인증"""
        pass
        
    @abstractmethod
    def collect_products(self, incremental: bool = False) -> Generator[ProductData, None, None]:
        """상품 수집"""
        pass
        
    def full_collection(self) -> CollectionResult:
        """전체 수집 실행"""
        result = CollectionResult(
            success=False,
            start_time=datetime.now()
        )
        
        try:
            self.logger.info(f"{self.supplier_name} 전체 수집 시작")
            
            # 인증 확인
            if not self.authenticate():
                result.error_message = "API 인증 실패"
                return result
                
            # 상품 수집
            for product in self.collect_products(incremental=False):
                result.total_count += 1
                
                # TODO: 데이터베이스 저장 로직
                # 지금은 로그만 출력
                self.logger.debug(f"수집된 상품: {product.product_code}")
                
            result.success = True
            result.new_count = result.total_count  # 전체 수집이므로 모두 신규
            
            self.logger.info(f"{self.supplier_name} 전체 수집 완료: {result.total_count}개")
            
        except Exception as e:
            result.error_message = str(e)
            result.error_count += 1
            self.logger.error(f"{self.supplier_name} 수집 실패: {e}")
            
        finally:
            result.end_time = datetime.now()
            
        return result
        
    def incremental_collection(self) -> CollectionResult:
        """증분 수집 실행"""
        result = CollectionResult(
            success=False,
            start_time=datetime.now()
        )
        
        try:
            self.logger.info(f"{self.supplier_name} 증분 수집 시작")
            
            # 인증 확인
            if not self.authenticate():
                result.error_message = "API 인증 실패"
                return result
                
            # 상품 수집
            for product in self.collect_products(incremental=True):
                result.total_count += 1
                
                # TODO: 데이터베이스 업데이트 로직
                # 기존 상품과 비교하여 신규/업데이트 판단
                self.logger.debug(f"증분 수집된 상품: {product.product_code}")
                
            result.success = True
            self.logger.info(f"{self.supplier_name} 증분 수집 완료: {result.total_count}개")
            
        except Exception as e:
            result.error_message = str(e)
            result.error_count += 1
            self.logger.error(f"{self.supplier_name} 증분 수집 실패: {e}")
            
        finally:
            result.end_time = datetime.now()
            
        return result