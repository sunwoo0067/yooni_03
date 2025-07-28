import requests
import json
import time
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime

from .base_collector import BaseCollector, ProductData
from utils.logger import app_logger

class DomeggookCollector(BaseCollector):
    """도매꾹 수집기 - 카테고리 기반 단순화된 버전"""
    
    @property
    def supplier_name(self) -> str:
        return "도매꾹"
        
    @property
    def supplier_code(self) -> str:
        return "domeggook"
        
    @property
    def base_url(self) -> str:
        return self.credentials.get('base_url', 'https://openapi.domeggook.com')
        
    def _get_headers(self) -> Dict[str, str]:
        """HTTP 헤더"""
        return {
            'User-Agent': 'SimpleCollector-Domeggook/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
    def authenticate(self) -> bool:
        """API 인증 확인 (테스트용)"""
        try:
            # 테스트 모드
            self.logger.info("도매꾹 인증 (테스트 모드)")
            return True
            
            # 실제 인증 코드 (API 키가 있을 때)
            # params = {
            #     'api_key': self.credentials.get('api_key'),
            #     'version': '1.0'
            # }
            # response = requests.get(
            #     f"{self.base_url}/api/category/list",
            #     params=params,
            #     headers=self._get_headers(),
            #     timeout=30
            # )
            # return response.status_code == 200
                        
        except Exception as e:
            self.logger.error(f"도매꾹 API 인증 중 오류: {e}")
            return False
            
    def collect_products(self, incremental: bool = False) -> Generator[ProductData, None, None]:
        """카테고리 기반 상품 수집"""
        self.logger.info(f"도매꾹 상품 수집 시작 (테스트 모드)")
        
        # 1단계: 카테고리 수집 (테스트 모드에서는 더미 카테고리)
        categories = self._get_test_categories()
        
        # 2단계: 중분류 카테고리만 필터링
        middle_categories = self._filter_middle_categories(categories)
        self.logger.info(f"수집 대상 중분류 카테고리: {len(middle_categories)}개")
        
        # 3단계: 각 카테고리별 상품 수집
        total_count = 0
        for category_code in middle_categories:
            self.logger.info(f"카테고리 {category_code} 수집 시작")
            
            # 테스트 모드: 카테고리당 5개씩 더미 상품 생성
            for i in range(1, 6):
                product_code = f"DG{category_code.replace('_', '')}{i:03d}"
                
                product_data = ProductData(
                    product_code=product_code,
                    product_info={
                        'product_code': product_code,
                        'product_name': f'도매꾹 테스트 상품 {category_code} - {i}',
                        'category_code': category_code,
                        'category_name': self._get_category_name(category_code),
                        'vendor_code': f'V{category_code[:2]}{i:03d}',
                        'supply_price': f'{5000 + i * 1000}',
                        'consumer_price': f'{10000 + i * 2000}',
                        'min_order_qty': 1,
                        'stock_status': 'available',
                        'images': [
                            f'https://example.com/dg_image_{product_code}_1.jpg',
                            f'https://example.com/dg_image_{product_code}_2.jpg'
                        ],
                        'options': self._generate_test_options(i),
                        'description': f'{product_code} 상품의 상세 설명입니다',
                        'shipping_info': {
                            'shipping_fee': 3000,
                            'return_fee': 3000,
                            'exchange_fee': 3000,
                            'delivery_type': '택배'
                        },
                        'product_url': f'https://domeggook.com/product/{product_code}',
                        'collected_at': datetime.now().isoformat(),
                        'supplier': 'domeggook'
                    },
                    supplier='domeggook'
                )
                
                total_count += 1
                yield product_data
                
                # 테스트용 딜레이
                time.sleep(0.1)
                
        self.logger.info(f"도매꾹 상품 수집 완료: 총 {total_count}개")
        
    def _get_test_categories(self) -> List[Dict[str, Any]]:
        """테스트용 카테고리 데이터"""
        return [
            {'code': '01_00_00_00_00', 'name': '의류', 'level': 1},
            {'code': '01_01_00_00_00', 'name': '여성의류', 'level': 2},
            {'code': '01_02_00_00_00', 'name': '남성의류', 'level': 2},
            {'code': '02_00_00_00_00', 'name': '잡화', 'level': 1},
            {'code': '02_01_00_00_00', 'name': '가방', 'level': 2},
            {'code': '02_02_00_00_00', 'name': '액세서리', 'level': 2},
            {'code': '03_00_00_00_00', 'name': '전자제품', 'level': 1},
            {'code': '03_01_00_00_00', 'name': '휴대폰액세서리', 'level': 2},
        ]
        
    def _filter_middle_categories(self, categories: List[Dict[str, Any]]) -> List[str]:
        """중분류 카테고리만 필터링 (XX_XX_00_00_00 패턴)"""
        middle_categories = []
        
        for category in categories:
            code = category.get('code', '')
            # 중분류 패턴: 두 번째 자리까지만 00이 아닌 코드
            parts = code.split('_')
            if len(parts) == 5 and parts[0] != '00' and parts[1] != '00' and all(p == '00' for p in parts[2:]):
                middle_categories.append(code)
                
        return middle_categories
        
    def _get_category_name(self, category_code: str) -> str:
        """카테고리 코드로부터 이름 생성"""
        category_map = {
            '01_01': '여성의류',
            '01_02': '남성의류',
            '02_01': '가방',
            '02_02': '액세서리',
            '03_01': '휴대폰액세서리',
        }
        
        prefix = '_'.join(category_code.split('_')[:2])
        return category_map.get(prefix, '기타')
        
    def _generate_test_options(self, index: int) -> List[Dict[str, Any]]:
        """테스트용 옵션 데이터 생성"""
        if index % 2 == 0:
            # 사이즈 옵션
            return [
                {'option_name': '사이즈', 'option_value': 'S', 'additional_price': 0},
                {'option_name': '사이즈', 'option_value': 'M', 'additional_price': 0},
                {'option_name': '사이즈', 'option_value': 'L', 'additional_price': 1000},
            ]
        else:
            # 색상 옵션
            return [
                {'option_name': '색상', 'option_value': '블랙', 'additional_price': 0},
                {'option_name': '색상', 'option_value': '화이트', 'additional_price': 0},
                {'option_name': '색상', 'option_value': '네이비', 'additional_price': 500},
            ]
    
    def _collect_category_products_real(self, category_code: str) -> Generator[ProductData, None, None]:
        """실제 카테고리별 상품 수집 (API 키가 있을 때 사용)"""
        page = 1
        page_size = 100
        
        while True:
            try:
                params = {
                    'api_key': self.credentials.get('api_key'),
                    'version': '4.1',
                    'category_code': category_code,
                    'page': page,
                    'page_size': page_size
                }
                
                response = requests.get(
                    f"{self.base_url}/api/product/list",
                    params=params,
                    headers=self._get_headers(),
                    timeout=60
                )
                
                if response.status_code != 200:
                    self.logger.error(f"API 요청 실패: HTTP {response.status_code}")
                    break
                    
                data = response.json()
                products = data.get('products', [])
                
                if not products:
                    break
                    
                for product in products:
                    try:
                        product_data = self._parse_product(product)
                        if product_data:
                            yield product_data
                    except Exception as e:
                        self.logger.error(f"상품 파싱 오류: {e}")
                        continue
                        
                # 다음 페이지로
                page += 1
                
                # Rate Limiting
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"카테고리 {category_code} 수집 중 오류: {e}")
                break
                
    def _parse_product(self, product_data: Dict[str, Any]) -> Optional[ProductData]:
        """API 응답에서 상품 데이터 파싱"""
        try:
            product_code = product_data.get('product_code')
            if not product_code:
                return None
                
            # 주문옵션 JSON 파싱
            options = []
            item_opt_json = product_data.get('itemOptJson', '')
            if item_opt_json:
                try:
                    options = json.loads(item_opt_json)
                except:
                    pass
                    
            product_info = {
                'product_code': product_code,
                'product_name': product_data.get('product_name'),
                'category_code': product_data.get('category_code'),
                'category_name': product_data.get('category_name'),
                'vendor_code': product_data.get('vendor_code'),
                'vendor_name': product_data.get('vendor_name'),
                'supply_price': product_data.get('supply_price'),
                'consumer_price': product_data.get('consumer_price'),
                'min_order_qty': product_data.get('min_order_qty', 1),
                'stock_status': product_data.get('stock_status'),
                'images': product_data.get('images', []),
                'options': options,
                'description': product_data.get('description'),
                'shipping_info': {
                    'shipping_fee': product_data.get('shipping_fee'),
                    'return_fee': product_data.get('return_fee'),
                    'exchange_fee': product_data.get('exchange_fee'),
                    'delivery_type': product_data.get('delivery_type')
                },
                'product_url': product_data.get('product_url'),
                'collected_at': datetime.now().isoformat(),
                'supplier': 'domeggook'
            }
            
            return ProductData(
                product_code=product_code,
                product_info=product_info,
                supplier='domeggook'
            )
            
        except Exception as e:
            self.logger.error(f"상품 데이터 파싱 오류: {e}")
            return None