import requests
import xml.etree.ElementTree as ET
import time
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime
from html import unescape

from .base_collector import BaseCollector, ProductData

class ZentradeCollector(BaseCollector):
    """젠트레이드 수집기 - 단순화된 동기 버전"""
    
    @property
    def supplier_name(self) -> str:
        return "젠트레이드"
        
    @property
    def supplier_code(self) -> str:
        return "zentrade"
        
    @property
    def base_url(self) -> str:
        return self.credentials.get('base_url', 'https://www.zentrade.co.kr/shop/proc')
        
    def _get_api_params(self) -> Dict[str, str]:
        """기본 API 파라미터"""
        return {
            'id': self.credentials.get('api_id', ''),
            'm_skey': self.credentials.get('api_key', '')
        }
        
    def _get_headers(self) -> Dict[str, str]:
        """HTTP 헤더"""
        return {
            'User-Agent': 'SimpleCollector-Zentrade/1.0',
            'Accept': 'application/xml, text/xml, */*',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
    def authenticate(self) -> bool:
        """API 인증 확인 (테스트용 - 실제 API 키 없어도 True 반환)"""
        try:
            # 실제 환경에서는 아래 주석을 해제하고 사용
            # params = self._get_api_params()
            # params.update({
            #     'proc': 'get_product_list',
            #     'start': '1',
            #     'limit': '1'
            # })
            # 
            # response = requests.post(
            #     self.base_url,
            #     data=params,
            #     headers=self._get_headers(),
            #     timeout=30
            # )
            # 
            # if response.status_code == 200:
            #     ET.fromstring(response.text)
            #     return True
            
            # 테스트용 - 항상 True 반환
            self.logger.info("젠트레이드 인증 (테스트 모드)")
            return True
                        
        except Exception as e:
            self.logger.error(f"젠트레이드 API 인증 중 오류: {e}")
            return False
            
    def collect_products(self, incremental: bool = False) -> Generator[ProductData, None, None]:
        """상품 수집 - 테스트용 더미 데이터"""
        self.logger.info(f"젠트레이드 상품 수집 시작 (테스트 모드)")
        
        # 테스트용 더미 데이터 생성
        for i in range(1, 11):  # 10개만 생성
            try:
                product_data = ProductData(
                    product_code=f"ZT{i:04d}",
                    product_info={
                        'product_code': f"ZT{i:04d}",
                        'product_name': f'테스트 상품 {i}',
                        'price': f'{10000 + i * 1000}',
                        'sale_price': f'{9000 + i * 1000}',
                        'category': '테스트 카테고리',
                        'brand': '테스트 브랜드',
                        'description': f'테스트 상품 {i}의 설명입니다',
                        'images': [f'https://example.com/image{i}.jpg'],
                        'stock_status': 'available',
                        'shipping_fee': '3000',
                        'return_fee': '3000',
                        'url': f'https://zentrade.co.kr/product/{i}',
                        'collected_at': datetime.now().isoformat(),
                        'supplier': 'zentrade'
                    },
                    supplier='zentrade'
                )
                
                yield product_data
                
                # 테스트용 딜레이
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"상품 생성 오류: {e}")
                continue
                
        self.logger.info("젠트레이드 상품 수집 완료 (테스트 모드): 10개")