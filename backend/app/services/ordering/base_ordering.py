"""
발주 서비스 기본 클래스
"""
import logging
import aiohttp
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.order_core import DropshippingOrder
from app.models.wholesaler import Wholesaler

logger = logging.getLogger(__name__)


class BaseOrderingService(ABC):
    """발주 서비스 기본 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def submit_order(self, dropshipping_order: DropshippingOrder, supplier: Wholesaler) -> Dict:
        """
        공급업체에 주문 제출
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            supplier: 공급업체 정보
            
        Returns:
            Dict: 발주 결과
        """
        pass
    
    @abstractmethod
    async def check_order_status(self, supplier_order_id: str, supplier: Wholesaler) -> Dict:
        """
        공급업체 주문 상태 확인
        
        Args:
            supplier_order_id: 공급업체 주문 ID
            supplier: 공급업체 정보
            
        Returns:
            Dict: 상태 확인 결과
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, supplier_order_id: str, supplier: Wholesaler, reason: str = "") -> Dict:
        """
        공급업체 주문 취소
        
        Args:
            supplier_order_id: 공급업체 주문 ID
            supplier: 공급업체 정보
            reason: 취소 사유
            
        Returns:
            Dict: 취소 결과
        """
        pass
    
    @abstractmethod
    async def get_tracking_info(self, tracking_number: str, supplier: Wholesaler) -> Dict:
        """
        배송 추적 정보 조회
        
        Args:
            tracking_number: 배송 추적 번호
            supplier: 공급업체 정보
            
        Returns:
            Dict: 추적 정보
        """
        pass
    
    @abstractmethod
    async def check_product_availability(self, product_ids: List[str], supplier: Wholesaler) -> Dict:
        """
        상품 재고 확인
        
        Args:
            product_ids: 상품 ID 리스트
            supplier: 공급업체 정보
            
        Returns:
            Dict: 재고 확인 결과
        """
        pass
    
    async def _make_api_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Optional[aiohttp.ClientResponse]:
        """
        API 요청 실행 (재시도 로직 포함)
        
        Args:
            method: HTTP 메서드
            url: 요청 URL
            params: 쿼리 파라미터
            data: 요청 데이터
            headers: 요청 헤더
            retry_count: 현재 재시도 횟수
            
        Returns:
            Optional[aiohttp.ClientResponse]: 응답 객체
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        try:
            # 기본 헤더 설정
            request_headers = {
                'User-Agent': 'YooniDropshipping/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            if headers:
                request_headers.update(headers)
            
            # 요청 실행
            async with self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data if data else None,
                headers=request_headers
            ) as response:
                
                # 응답 로깅
                logger.debug(f"API 요청: {method.upper()} {url} -> {response.status}")
                
                # 성공적인 응답
                if 200 <= response.status < 300:
                    return response
                
                # 재시도 가능한 오류 (5xx, 429)
                if (response.status >= 500 or response.status == 429) and retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))  # 지수 백오프
                    return await self._make_api_request(
                        method, url, params, data, headers, retry_count + 1
                    )
                
                # 클라이언트 오류 (4xx)
                logger.warning(f"API 클라이언트 오류: {response.status} {url}")
                return response
                
        except aiohttp.ClientError as e:
            logger.error(f"API 요청 중 네트워크 오류: {str(e)}")
            
            # 네트워크 오류 재시도
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                return await self._make_api_request(
                    method, url, params, data, headers, retry_count + 1
                )
            
            raise
        
        except Exception as e:
            logger.error(f"API 요청 중 예외 발생: {str(e)}", exc_info=True)
            raise
    
    def _normalize_price(self, price_value: Any) -> float:
        """가격 정규화"""
        try:
            if isinstance(price_value, (int, float)):
                return float(price_value)
            elif isinstance(price_value, str):
                # 문자열에서 숫자만 추출
                import re
                numbers = re.findall(r'\d+\.?\d*', price_value.replace(',', ''))
                if numbers:
                    return float(numbers[0])
            return 0.0
        except:
            return 0.0
    
    def _normalize_stock(self, stock_value: Any) -> int:
        """재고 정규화"""
        try:
            if isinstance(stock_value, int):
                return stock_value
            elif isinstance(stock_value, str):
                import re
                numbers = re.findall(r'\d+', stock_value.replace(',', ''))
                if numbers:
                    return int(numbers[0])
            elif isinstance(stock_value, float):
                return int(stock_value)
            return 0
        except:
            return 0
    
    def _validate_order_data(self, order_data: Dict) -> Dict:
        """주문 데이터 검증"""
        validation_result = {
            'valid': True,
            'errors': []
        }
        
        # 필수 필드 검증
        required_fields = ['order_number', 'items', 'shipping_address', 'orderer']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                validation_result['errors'].append(f'필수 필드 누락: {field}')
                validation_result['valid'] = False
        
        # 주문 상품 검증
        if 'items' in order_data:
            items = order_data['items']
            if not isinstance(items, list) or len(items) == 0:
                validation_result['errors'].append('주문 상품이 없습니다')
                validation_result['valid'] = False
            else:
                for i, item in enumerate(items):
                    item_required = ['product_id', 'quantity', 'unit_price']
                    for field in item_required:
                        if field not in item:
                            validation_result['errors'].append(f'상품 {i+1}에서 필수 필드 누락: {field}')
                            validation_result['valid'] = False
        
        # 배송지 정보 검증
        if 'shipping_address' in order_data:
            address = order_data['shipping_address']
            address_required = ['recipient_name', 'phone', 'address1']
            for field in address_required:
                if field not in address or not address[field]:
                    validation_result['errors'].append(f'배송지 정보 누락: {field}')
                    validation_result['valid'] = False
        
        return validation_result
    
    def _format_phone_number(self, phone: str) -> str:
        """전화번호 형식 정규화"""
        if not phone:
            return ""
        
        # 숫자만 추출
        import re
        numbers = re.sub(r'[^\d]', '', phone)
        
        # 한국 전화번호 형식으로 변환
        if len(numbers) == 11 and numbers.startswith('010'):
            return f"{numbers[:3]}-{numbers[3:7]}-{numbers[7:]}"
        elif len(numbers) == 10:
            if numbers.startswith('02'):
                return f"{numbers[:2]}-{numbers[2:6]}-{numbers[6:]}"
            else:
                return f"{numbers[:3]}-{numbers[3:6]}-{numbers[6:]}"
        
        return phone  # 변환할 수 없으면 원본 반환
    
    def _format_address(self, address_data: Dict) -> str:
        """주소 형식 정규화"""
        try:
            parts = []
            
            if address_data.get('address1'):
                parts.append(address_data['address1'])
            if address_data.get('address2'):
                parts.append(address_data['address2'])
            if address_data.get('city'):
                parts.append(address_data['city'])
            if address_data.get('state'):
                parts.append(address_data['state'])
            if address_data.get('postal_code'):
                parts.append(f"({address_data['postal_code']})")
            
            return ' '.join(parts)
        except:
            return ""
    
    async def _log_request(self, method: str, url: str, data: Optional[Dict] = None, response_status: Optional[int] = None):
        """요청 로깅"""
        log_data = {
            'method': method,
            'url': url,
            'timestamp': datetime.utcnow().isoformat(),
            'response_status': response_status
        }
        
        if data:
            # 민감한 정보 마스킹
            safe_data = self._mask_sensitive_data(data)
            log_data['request_data'] = safe_data
        
        logger.info(f"API 요청 로그: {log_data}")
    
    def _mask_sensitive_data(self, data: Dict) -> Dict:
        """민감한 정보 마스킹"""
        if not isinstance(data, dict):
            return data
        
        masked_data = data.copy()
        sensitive_keys = ['api_key', 'secret_key', 'password', 'token', 'phone', 'email']
        
        for key, value in masked_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    masked_data[key] = '***'
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_data(value)
        
        return masked_data
    
    async def health_check(self, supplier: Wholesaler) -> Dict:
        """공급업체 API 상태 확인"""
        try:
            start_time = datetime.utcnow()
            
            # 간단한 API 호출로 상태 확인 (각 공급업체별로 구현)
            result = await self.check_product_availability([], supplier)
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                'success': True,
                'supplier': supplier.name,
                'response_time_ms': int(response_time * 1000),
                'status': 'healthy',
                'last_checked': end_time.isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'supplier': supplier.name,
                'status': 'unhealthy',
                'error': str(e),
                'last_checked': datetime.utcnow().isoformat()
            }