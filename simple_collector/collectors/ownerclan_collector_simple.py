import requests
import time
from typing import Dict, Any, List, Optional, Generator, Set
from datetime import datetime, timedelta
from collections import deque

from .base_collector import BaseCollector, ProductData
from config.settings import settings

class OwnerClanCollector(BaseCollector):
    """오너클랜 수집기 - 단순화된 동기 버전"""
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self._jwt_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._product_code_cache: deque = deque(maxlen=settings.OWNERCLAN_CACHE_SIZE)
        self._cached_codes: Set[str] = set()
        
    @property
    def supplier_name(self) -> str:
        return "오너클랜"
        
    @property
    def supplier_code(self) -> str:
        return "ownerclan"
        
    def authenticate(self) -> bool:
        """API 인증 (테스트용)"""
        try:
            # 테스트용 - 항상 True 반환
            self.logger.info("오너클랜 인증 (테스트 모드)")
            return True
                        
        except Exception as e:
            self.logger.error(f"오너클랜 API 인증 중 오류: {e}")
            return False
            
    def collect_products(self, incremental: bool = False) -> Generator[ProductData, None, None]:
        """2단계 상품 수집 - 테스트용"""
        
        # 1단계: 상품 코드 수집 (시뮬레이션)
        self._stage1_collect_codes()
        
        if not self._cached_codes:
            self.logger.warning("수집된 상품 코드가 없습니다")
            return
            
        # 2단계: 상세 정보 수집 (시뮬레이션)
        for product in self._stage2_collect_details():
            yield product
            
    def _stage1_collect_codes(self):
        """1단계: 상품 코드 수집 시뮬레이션"""
        self.logger.info(f"오너클랜 1단계 시작: 상품 코드 수집 (테스트 모드)")
        
        # 테스트용 더미 상품 코드 생성
        for i in range(1, 21):  # 20개 코드 생성
            product_code = f"OC{i:04d}"
            if product_code not in self._cached_codes:
                self._product_code_cache.append({
                    'code': product_code,
                    'updated_at': datetime.now().isoformat()
                })
                self._cached_codes.add(product_code)
                
        self.logger.info(f"오너클랜 1단계 완료: {len(self._cached_codes)}개 상품 코드 수집")
        
    def _stage2_collect_details(self) -> Generator[ProductData, None, None]:
        """2단계: 상세 정보 수집 시뮬레이션"""
        self.logger.info(f"오너클랜 2단계 시작: {len(self._cached_codes)}개 상품 상세 정보 수집")
        
        processed_count = 0
        
        for product_info in self._product_code_cache:
            try:
                product_code = product_info['code']
                
                # 테스트용 더미 상품 데이터 생성
                product_data = ProductData(
                    product_code=product_code,
                    product_info={
                        'product_code': product_code,
                        'product_name': f'오너클랜 테스트 상품 {product_code}',
                        'brand_name': '테스트 브랜드',
                        'category_name': '테스트 카테고리',
                        'sale_price': f'{15000 + processed_count * 1000}',
                        'supply_price': f'{12000 + processed_count * 1000}',
                        'stock_quantity': 100,
                        'product_status': 'active',
                        'images': [
                            {'imageUrl': f'https://example.com/oc_image_{product_code}.jpg', 'imageType': 'main'}
                        ],
                        'options': [],
                        'description': f'{product_code} 상품의 상세 설명입니다',
                        'specifications': {'재질': '테스트', '크기': '표준'},
                        'shipping_info': {
                            'shippingFee': 3000,
                            'returnFee': 3000,
                            'exchangeFee': 3000
                        },
                        'product_url': f'https://ownerclan.com/product/{product_code}',
                        'created_at': datetime.now().isoformat(),
                        'updated_at': product_info['updated_at'],
                        'collected_at': datetime.now().isoformat(),
                        'supplier': 'ownerclan'
                    },
                    supplier='ownerclan'
                )
                
                processed_count += 1
                yield product_data
                
                # 테스트용 딜레이
                time.sleep(0.1)
                
                if processed_count % 5 == 0:
                    self.logger.info(f"2단계 진행: {processed_count}개 처리 완료")
                    
            except Exception as e:
                self.logger.error(f"상품 {product_info['code']} 처리 중 오류: {e}")
                continue
                
        self.logger.info(f"오너클랜 2단계 완료: {processed_count}개 상품 상세 정보 수집")