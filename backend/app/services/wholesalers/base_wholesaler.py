from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
import aiohttp
import logging
from enum import Enum

from ...utils.encryption import encrypt_data, decrypt_data
from ...models.wholesaler import WholesalerType, ConnectionStatus


class CollectionType(Enum):
    """수집 유형"""
    ALL = "all"                    # 전체 상품 수집
    RECENT = "recent"              # 최근 상품 수집
    CATEGORY = "category"          # 카테고리별 수집
    UPDATED = "updated"            # 업데이트된 상품만 수집
    NEW = "new"                    # 신상품만 수집


class ProductData:
    """표준화된 상품 데이터 구조"""
    
    def __init__(self, **kwargs):
        # 필수 필드
        self.wholesaler_product_id: str = kwargs.get('wholesaler_product_id', '')
        self.name: str = kwargs.get('name', '')
        self.wholesale_price: int = kwargs.get('wholesale_price', 0)
        
        # 선택 필드
        self.wholesaler_sku: Optional[str] = kwargs.get('wholesaler_sku')
        self.description: Optional[str] = kwargs.get('description')
        self.category_path: Optional[str] = kwargs.get('category_path')
        self.retail_price: Optional[int] = kwargs.get('retail_price')
        self.discount_rate: Optional[int] = kwargs.get('discount_rate')
        self.stock_quantity: int = kwargs.get('stock_quantity', 0)
        self.is_in_stock: bool = kwargs.get('is_in_stock', True)
        
        # 이미지
        self.main_image_url: Optional[str] = kwargs.get('main_image_url')
        self.additional_images: List[str] = kwargs.get('additional_images', [])
        
        # 옵션 및 변형
        self.options: Dict[str, Any] = kwargs.get('options', {})
        self.variants: List[Dict[str, Any]] = kwargs.get('variants', [])
        
        # 배송 정보
        self.shipping_info: Dict[str, Any] = kwargs.get('shipping_info', {})
        
        # 원본 데이터
        self.raw_data: Dict[str, Any] = kwargs.get('raw_data', {})
        
        # 메타데이터
        self.last_updated: Optional[datetime] = kwargs.get('last_updated')


class CollectionResult:
    """수집 결과"""
    
    def __init__(self):
        self.success: bool = False
        self.total_found: int = 0
        self.collected: int = 0
        self.updated: int = 0
        self.failed: int = 0
        self.errors: List[str] = []
        self.products: List[ProductData] = []
        self.execution_time: Optional[timedelta] = None
        self.summary: Dict[str, Any] = {}


class APICredentials:
    """API 인증 정보 기본 클래스"""
    
    def __init__(self, **kwargs):
        self.raw_credentials = kwargs
        
    def get(self, key: str, default: Any = None) -> Any:
        return self.raw_credentials.get(key, default)
        
    def to_dict(self) -> Dict[str, Any]:
        return self.raw_credentials.copy()


class BaseWholesaler(ABC):
    """도매처 API 연동 추상 클래스"""
    
    def __init__(self, credentials: Dict[str, Any], logger: logging.Logger = None):
        self.credentials = APICredentials(**credentials)
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
        self._last_error: Optional[str] = None
        
    @property
    @abstractmethod
    def wholesaler_type(self) -> WholesalerType:
        """도매처 유형 반환"""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """도매처 이름 반환"""
        pass
        
    @property
    @abstractmethod
    def base_url(self) -> str:
        """API 기본 URL 반환"""
        pass
        
    @property
    @abstractmethod
    def rate_limit_per_minute(self) -> int:
        """분당 요청 제한 수 반환"""
        pass
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """API 인증 수행
        
        Returns:
            bool: 인증 성공 여부
        """
        pass
        
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """연결 테스트
        
        Returns:
            Dict[str, Any]: 테스트 결과
            {
                'success': bool,
                'message': str,
                'response_time_ms': int,
                'api_info': dict
            }
        """
        pass
        
    @abstractmethod
    async def get_categories(self) -> List[Dict[str, Any]]:
        """카테고리 목록 조회
        
        Returns:
            List[Dict[str, Any]]: 카테고리 목록
        """
        pass
        
    @abstractmethod
    async def collect_products(
        self,
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products: int = 1000
    ) -> AsyncGenerator[ProductData, None]:
        """상품 수집
        
        Args:
            collection_type: 수집 유형
            filters: 수집 조건
            max_products: 최대 수집 상품 수
            
        Yields:
            ProductData: 수집된 상품 데이터
        """
        pass
        
    @abstractmethod
    async def get_product_detail(self, product_id: str) -> Optional[ProductData]:
        """상품 상세 정보 조회
        
        Args:
            product_id: 상품 ID
            
        Returns:
            Optional[ProductData]: 상품 데이터
        """
        pass
        
    @abstractmethod
    async def get_stock_info(self, product_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """재고 정보 조회
        
        Args:
            product_ids: 상품 ID 목록
            
        Returns:
            Dict[str, Dict[str, Any]]: 상품별 재고 정보
        """
        pass
        
    # 공통 메서드들
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
        
    async def initialize(self):
        """세션 초기화"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_default_headers()
            )
            self.logger.info(f"{self.name} 세션 초기화 완료")
            
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info(f"{self.name} 세션 종료")
            
    def _get_default_headers(self) -> Dict[str, str]:
        """기본 HTTP 헤더 반환"""
        return {
            'User-Agent': 'YooniWholesaler/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Optional[aiohttp.ClientResponse]:
        """HTTP 요청 수행
        
        Args:
            method: HTTP 메서드
            url: 요청 URL
            headers: 추가 헤더
            params: URL 파라미터
            data: 폼 데이터
            json_data: JSON 데이터
            timeout: 타임아웃 (초)
            
        Returns:
            Optional[aiohttp.ClientResponse]: 응답 객체
        """
        if not self.session:
            await self.initialize()
            
        try:
            request_headers = self._get_default_headers()
            if headers:
                request_headers.update(headers)
                
            self.logger.debug(f"{method} {url} 요청 시작")
            
            async with self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                data=data,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                self.logger.debug(f"응답: {response.status}")
                return response
                
        except asyncio.TimeoutError:
            error_msg = f"요청 타임아웃: {url}"
            self.logger.error(error_msg)
            self._last_error = error_msg
            return None
            
        except Exception as e:
            error_msg = f"요청 실패: {url} - {str(e)}"
            self.logger.error(error_msg)
            self._last_error = error_msg
            return None
            
    def _normalize_price(self, price: Any) -> int:
        """가격 정규화 (정수형 원 단위로 변환)"""
        if price is None:
            return 0
            
        # 문자열인 경우 숫자만 추출
        if isinstance(price, str):
            price = ''.join(filter(str.isdigit, price))
            if not price:
                return 0
                
        try:
            return int(float(price))
        except (ValueError, TypeError):
            return 0
            
    def _normalize_stock(self, stock: Any) -> int:
        """재고 수량 정규화"""
        if stock is None:
            return 0
            
        try:
            return max(0, int(stock))
        except (ValueError, TypeError):
            return 0
            
    def _extract_images(self, data: Dict[str, Any]) -> tuple[Optional[str], List[str]]:
        """이미지 URL 추출
        
        Returns:
            tuple: (메인 이미지 URL, 추가 이미지 URL 목록)
        """
        main_image = None
        additional_images = []
        
        # 도매처별로 구현 필요
        return main_image, additional_images
        
    def _build_category_path(self, categories: List[Dict[str, Any]]) -> str:
        """카테고리 경로 구성"""
        if not categories:
            return ""
            
        # 카테고리 이름들을 '>' 로 연결
        names = []
        for cat in categories:
            if isinstance(cat, dict):
                name = cat.get('name') or cat.get('category_name', '')
            else:
                name = str(cat)
            if name:
                names.append(name)
                
        return ' > '.join(names)
        
    def get_last_error(self) -> Optional[str]:
        """마지막 오류 메시지 반환"""
        return self._last_error
        
    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        return self._authenticated
        
    async def collect_all_products(
        self,
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products: int = 1000,
        batch_size: int = 100
    ) -> CollectionResult:
        """전체 상품 수집 실행
        
        Args:
            collection_type: 수집 유형
            filters: 수집 조건
            max_products: 최대 수집 상품 수
            batch_size: 배치 크기
            
        Returns:
            CollectionResult: 수집 결과
        """
        start_time = datetime.now()
        result = CollectionResult()
        
        try:
            self.logger.info(f"{self.name} 상품 수집 시작 (타입: {collection_type.value})")
            
            # 인증 확인
            if not self._authenticated:
                auth_success = await self.authenticate()
                if not auth_success:
                    result.errors.append("API 인증 실패")
                    return result
                    
            collected_count = 0
            async for product in self.collect_products(collection_type, filters, max_products):
                if collected_count >= max_products:
                    break
                    
                result.products.append(product)
                collected_count += 1
                result.collected += 1
                
                if collected_count % batch_size == 0:
                    self.logger.info(f"진행률: {collected_count}/{max_products}")
                    
            result.success = True
            result.total_found = result.collected
            
        except Exception as e:
            error_msg = f"{self.name} 상품 수집 중 오류: {str(e)}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            
        finally:
            result.execution_time = datetime.now() - start_time
            result.summary = {
                'wholesaler': self.name,
                'collection_type': collection_type.value,
                'execution_time_seconds': result.execution_time.total_seconds(),
                'success_rate': result.collected / max(result.total_found, 1) * 100
            }
            
            self.logger.info(
                f"{self.name} 수집 완료: "
                f"{result.collected}개 수집, "
                f"{len(result.errors)}개 오류, "
                f"소요시간: {result.execution_time}"
            )
            
        return result