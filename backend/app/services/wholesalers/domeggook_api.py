"""
도매매(Domeggook) API 통합 서비스 (수정된 버전)
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class DomeggookAPIFixed:
    """도매매 API 클라이언트 (수정된 버전)"""
    
    def __init__(self, api_key: str = None):
        """
        API 클라이언트 초기화
        
        Args:
            api_key: API 인증키
        """
        self.api_key = api_key or os.getenv('DOMEGGOOK_API_KEY')
        self.base_url = "https://openapi.domeggook.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DomeggookAPI-Python/1.0'
        })
        
    def _make_request(self, endpoint: str, params: Dict = None, 
                     max_retries: int = 3, delay: float = 1.0) -> Dict:
        """
        API 요청 공통 함수
        
        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            max_retries: 최대 재시도 횟수
            delay: 요청 간 지연 시간(초)
            
        Returns:
            API 응답 데이터
        """
        if params is None:
            params = {}
        
        params['api_key'] = self.api_key
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"API 호출: {url} (시도 {attempt + 1}/{max_retries})")
                response = self.session.get(url, params=params, timeout=30)
                
                logger.info(f"응답 상태: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"API 오류: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                    else:
                        raise Exception(f"API Error: {response.status_code}")
                
                data = response.json()
                
                # API 에러 체크
                if data.get('result') == 'error':
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"API 에러: {error_msg}")
                    raise Exception(f"API Error: {error_msg}")
                
                time.sleep(delay)  # Rate limiting
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay * (attempt + 1))
        
        raise Exception(f"Failed to complete request after {max_retries} attempts")
    
    async def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            # 카테고리 API로 테스트
            endpoint = "/api/category/list"
            params = {'version': '1.0'}
            
            response = self._make_request(endpoint, params)
            
            if response.get('result') == 'success' or 'data' in response:
                logger.info("도매매 API 연결 성공")
                return True
            else:
                logger.error(f"도매매 API 연결 실패: {response}")
                return False
                
        except Exception as e:
            logger.error(f"도매매 API 연결 오류: {e}")
            return False
    
    def get_categories(self) -> List[Dict]:
        """
        전체 카테고리 목록 조회 (v1.0)
        
        Returns:
            카테고리 정보 리스트
        """
        endpoint = "/api/category/list"
        params = {'version': '1.0'}
        
        try:
            response = self._make_request(endpoint, params)
            categories = response.get('data', [])
            
            logger.info(f"총 {len(categories)}개 카테고리 수집 완료")
            return categories
        except Exception as e:
            logger.error(f"카테고리 조회 실패: {e}")
            return []
    
    def filter_middle_categories(self, categories: List[Dict]) -> List[str]:
        """
        중분류 카테고리 코드만 추출
        
        Args:
            categories: 전체 카테고리 리스트
            
        Returns:
            중분류 카테고리 코드 리스트
        """
        middle_categories = []
        
        for category in categories:
            code = category.get('category_code', '')
            
            # 중분류 패턴: XX_XX_00_00_00
            parts = code.split('_')
            if len(parts) == 5 and parts[2] == '00' and parts[3] == '00' and parts[4] == '00' and parts[1] != '00':
                middle_categories.append(code)
        
        # 중복 제거 및 정렬
        middle_categories = sorted(list(set(middle_categories)))
        
        logger.info(f"중분류 카테고리 {len(middle_categories)}개 추출")
        return middle_categories
    
    def get_product_list(self, category_code: str, page: int = 1, 
                        per_page: int = 100) -> Dict:
        """
        카테고리별 상품 목록 조회 (v4.1)
        
        Args:
            category_code: 카테고리 코드
            page: 페이지 번호
            per_page: 페이지당 상품 수 (최대 100)
            
        Returns:
            상품 목록 응답 데이터
        """
        endpoint = "/api/product/list"
        params = {
            'version': '4.1',
            'category_code': category_code,
            'page': page,
            'limit': min(per_page, 100)  # 최대 100개 제한
        }
        
        try:
            response = self._make_request(endpoint, params)
            return response
        except Exception as e:
            logger.error(f"상품 목록 조회 실패: {e}")
            return {'data': {'items': []}}
    
    async def collect_all_products(self, limit: int = 100) -> List[Dict]:
        """
        전체 상품 수집 (제한된 수량)
        
        Args:
            limit: 수집할 최대 상품 수
            
        Returns:
            상품 리스트
        """
        logger.info(f"도매매 상품 수집 시작 (최대 {limit}개)")
        
        # 1. 카테고리 조회
        categories = self.get_categories()
        if not categories:
            logger.error("카테고리 조회 실패")
            return []
        
        middle_categories = self.filter_middle_categories(categories)
        if not middle_categories:
            logger.error("중분류 카테고리가 없음")
            return []
        
        # 2. 상품 수집
        all_products = []
        
        for category_code in middle_categories[:5]:  # 처음 5개 카테고리만
            try:
                logger.info(f"카테고리 {category_code} 상품 조회 중...")
                
                response = self.get_product_list(category_code, page=1, per_page=20)
                products = response.get('data', {}).get('items', [])
                
                if products:
                    # 도매매 형식을 통합 형식으로 변환
                    for product in products:
                        transformed = self._transform_product(product)
                        if transformed:
                            all_products.append(transformed)
                            
                            if len(all_products) >= limit:
                                logger.info(f"목표 수량 {limit}개 도달")
                                return all_products
                    
                    logger.info(f"카테고리 {category_code}: {len(products)}개 상품 수집")
                
            except Exception as e:
                logger.error(f"카테고리 {category_code} 수집 실패: {e}")
                continue
        
        logger.info(f"도매매 총 {len(all_products)}개 상품 수집 완료")
        return all_products
    
    def _transform_product(self, product: Dict) -> Optional[Dict]:
        """
        도매매 상품 데이터를 통합 형식으로 변환
        
        Args:
            product: 도매매 API 상품 데이터
            
        Returns:
            변환된 상품 데이터
        """
        try:
            # 상품 정보 추출
            product_id = str(product.get('product_id', ''))
            if not product_id:
                return None
            
            # 가격 정보
            price_info = product.get('price_info', {})
            dom_price = int(price_info.get('dom_price', 0))
            
            # 재고 정보
            stock_info = product.get('stock_info', {})
            stock_quantity = int(stock_info.get('quantity', 0))
            
            # 카테고리 정보
            category_info = product.get('category_info', {})
            category_name = category_info.get('category_name', '')
            
            # 이미지 정보
            images = product.get('images', [])
            main_image = images[0] if images else ''
            
            transformed = {
                'wholesaler': 'Domeggook',
                'product_id': product_id,
                'name': product.get('product_name', ''),
                'price': dom_price,
                'stock': stock_quantity,
                'category': category_name,
                'image_url': main_image,
                'supplier': product.get('supplier_name', ''),
                'status': 'active' if stock_quantity > 0 else 'out_of_stock',
                'collected_at': datetime.now().isoformat(),
                'raw_data': product
            }
            
            return transformed
            
        except Exception as e:
            logger.error(f"상품 변환 오류: {e}")
            return None
    
    def get_product_detail(self, product_id: str) -> Optional[Dict]:
        """
        상품 상세정보 조회 (v4.5)
        
        Args:
            product_id: 상품 ID
            
        Returns:
            상품 상세정보
        """
        endpoint = "/api/product/detail"
        params = {
            'version': '4.5',
            'product_id': product_id
        }
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data')
        except Exception as e:
            logger.error(f"상품 상세정보 조회 실패: {e}")
            return None