"""
젠트레이드 API 서비스 (수정된 버전)
XML API 처리
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
import logging

from app.services.wholesalers.base_wholesaler import (
    BaseWholesaler, 
    ProductData, 
    CollectionType
)

logger = logging.getLogger(__name__)


class ZentradeAPIFixed(BaseWholesaler):
    """수정된 젠트레이드 API 구현"""
    
    @property
    def wholesaler_type(self):
        return "zentrade"
    
    @property
    def name(self):
        return "젠트레이드"
    
    @property
    def base_url(self):
        return self.base_url_val
    
    @property
    def rate_limit_per_minute(self):
        return 30  # 분당 30회
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_id = credentials.get('api_key')  # 실제로는 ID
        self.api_secret = credentials.get('api_secret')  # 실제로는 m_skey
        self.base_url_val = 'https://www.zentrade.co.kr/shop/proc'
        
    async def authenticate(self) -> bool:
        """젠트레이드는 별도 인증 없이 API 키 사용"""
        return bool(self.api_id and self.api_secret)
        
    async def test_connection(self) -> Dict[str, any]:
        """연결 테스트"""
        try:
            # 상품 1개만 조회해서 테스트
            url = f"{self.base_url_val}/product_api.php"
            params = {
                'id': self.api_id,
                'm_skey': self.api_secret
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # XML 파싱 테스트
                        try:
                            # EUC-KR 디코딩
                            xml_content = content.decode('euc-kr')
                            root = ET.fromstring(xml_content)
                            
                            if root.tag == 'zentrade':
                                product_count = len(root.findall('product'))
                                return {
                                    'success': True,
                                    'message': '연결 성공',
                                    'details': {
                                        'authenticated': True,
                                        'api_accessible': True,
                                        'product_count': product_count
                                    }
                                }
                        except Exception as e:
                            logger.error(f"XML 파싱 오류: {e}")
                            
                    return {
                        'success': False,
                        'message': f'API 접근 실패 (상태 코드: {response.status})'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'message': f'연결 오류: {str(e)}'
            }
            
    async def get_categories(self) -> List[Dict[str, any]]:
        """카테고리 목록 조회 - 젠트레이드는 별도 카테고리 API 없음"""
        # 상품에서 카테고리 정보를 추출해야 함
        categories_set = set()
        
        try:
            async for product in self.collect_products(max_products=100):
                if product.category_path:
                    categories_set.add(product.category_path)
                    
            categories = [
                {'id': idx, 'name': cat} 
                for idx, cat in enumerate(sorted(categories_set))
            ]
            
            return categories
            
        except Exception as e:
            logger.error(f"카테고리 수집 오류: {e}")
            return []
            
    async def collect_products(
        self, 
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict] = None,
        max_products: Optional[int] = None
    ) -> AsyncGenerator[ProductData, None]:
        """상품 수집"""
        url = f"{self.base_url_val}/product_api.php"
        params = {
            'id': self.api_id,
            'm_skey': self.api_secret
        }
        
        # 필터 적용
        if filters:
            if filters.get('runout') is not None:
                params['runout'] = '1' if filters['runout'] else '0'
            if filters.get('opendate_s'):
                params['opendate_s'] = filters['opendate_s']
            if filters.get('opendate_e'):
                params['opendate_e'] = filters['opendate_e']
            if filters.get('goodsno'):
                params['goodsno'] = filters['goodsno']
                
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"API 요청 실패: {response.status}")
                        return
                        
                    content = await response.read()
                    
                    # EUC-KR 디코딩
                    try:
                        xml_content = content.decode('euc-kr')
                    except UnicodeDecodeError:
                        xml_content = content.decode('utf-8')
                        
                    # XML 파싱
                    root = ET.fromstring(xml_content)
                    
                    if root.tag != 'zentrade':
                        logger.error(f"예상치 못한 루트 태그: {root.tag}")
                        return
                        
                    products = root.findall('product')
                    collected_count = 0
                    
                    for product_elem in products:
                        if max_products and collected_count >= max_products:
                            return
                            
                        try:
                            # 상품 정보 추출
                            product = self._parse_product(product_elem)
                            if product:
                                yield product
                                collected_count += 1
                                
                        except Exception as e:
                            logger.error(f"상품 파싱 오류: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"상품 수집 중 오류: {e}")
            
    def _parse_product(self, product_elem: ET.Element) -> Optional[ProductData]:
        """XML 상품 정보 파싱"""
        try:
            # 기본 정보
            code = product_elem.get('code')
            if not code:
                return None
                
            # 상품명
            name_elem = product_elem.find('prdtname')
            name = self._clean_text(name_elem.text) if name_elem is not None else ''
            
            # 카테고리
            category_elem = product_elem.find('dome_category')
            category = self._clean_text(category_elem.text) if category_elem is not None else ''
            
            # 기본 정보
            baseinfo = product_elem.find('baseinfo')
            brand = baseinfo.get('brand', '') if baseinfo is not None else ''
            model = baseinfo.get('model', '') if baseinfo is not None else ''
            madein = baseinfo.get('madein', '') if baseinfo is not None else ''
            productcom = baseinfo.get('productcom', '') if baseinfo is not None else ''
            
            # 가격
            price_elem = product_elem.find('price')
            buyprice = int(price_elem.get('buyprice', '0')) if price_elem is not None else 0
            consumerprice = int(price_elem.get('consumerprice', '0')) if price_elem is not None else 0
            taxmode = price_elem.get('taxmode', 'Y') if price_elem is not None else 'Y'
            
            # 이미지
            images = []
            listimg = product_elem.find('listimg')
            if listimg is not None:
                for i in range(1, 6):
                    img_url = listimg.get(f'url{i}', '')
                    if img_url:
                        images.append(img_url)
                        
            # 옵션
            options = self._parse_options(product_elem.find('option'))
            
            # 상태
            status_elem = product_elem.find('status')
            runout = status_elem.get('runout', '0') if status_elem is not None else '0'
            opendate = status_elem.get('opendate', '') if status_elem is not None else ''
            
            # 상세 내용
            content_elem = product_elem.find('content')
            content = self._clean_text(content_elem.text) if content_elem is not None else ''
            
            # 키워드
            keyword_elem = product_elem.find('keyword')
            keywords = self._clean_text(keyword_elem.text) if keyword_elem is not None else ''
            
            # ProductData 생성
            return ProductData(
                wholesaler_type=self.wholesaler_type,
                wholesaler_product_id=code,
                name=name,
                wholesale_price=buyprice,
                retail_price=consumerprice,
                stock_quantity=0 if runout == '1' else 999,  # 재고 수량 정보 없음
                minimum_order_quantity=1,
                description=content,
                main_image_url=images[0] if images else '',
                additional_images=images[1:] if len(images) > 1 else [],
                category_path=category,
                brand=brand,
                model_name=model,
                shipping_fee=0,  # 배송비 정보 없음
                is_active=runout != '1',
                options=options,
                metadata={
                    'madein': madein,
                    'productcom': productcom,
                    'taxmode': taxmode,
                    'keywords': keywords,
                    'opendate': opendate
                }
            )
            
        except Exception as e:
            logger.error(f"상품 파싱 중 오류: {e}")
            return None
            
    def _parse_options(self, option_elem: Optional[ET.Element]) -> List[Dict]:
        """옵션 정보 파싱"""
        if option_elem is None:
            return []
            
        options = []
        opt1nm = option_elem.get('opt1nm', '옵션')
        option_text = self._clean_text(option_elem.text)
        
        if not option_text:
            return []
            
        # 옵션 항목 분리
        option_items = option_text.split('↑=↑')
        
        for item in option_items:
            if not item.strip():
                continue
                
            parts = item.split('^|^')
            if len(parts) >= 3:
                option = {
                    'name': parts[0],
                    'price': int(parts[1]) if parts[1].isdigit() else 0,
                    'retail_price': int(parts[2]) if parts[2].isdigit() else 0,
                    'image_url': parts[3] if len(parts) > 3 else '',
                    'stock': 999  # 재고 정보 없음
                }
                options.append(option)
                
        return options
        
    def _clean_text(self, text: Optional[str]) -> str:
        """CDATA 텍스트 정리"""
        if not text:
            return ''
        return text.strip()
    
    async def get_product_detail(self, product_id: str) -> Optional[ProductData]:
        """상품 상세 정보 조회"""
        # 특정 상품만 조회
        try:
            async for product in self.collect_products(filters={'goodsno': product_id}, max_products=1):
                return product
            return None
        except Exception as e:
            logger.error(f"상품 상세 조회 오류: {e}")
            return None
    
    async def get_stock_info(self, product_ids: List[str]) -> Dict[str, Dict[str, any]]:
        """재고 정보 조회"""
        stock_info = {}
        
        # 젠트레이드는 개별 재고 API가 없으므로 상품 정보에서 추출
        for product_id in product_ids:
            try:
                product = await self.get_product_detail(product_id)
                if product:
                    stock_info[product_id] = {
                        'in_stock': product.is_active,
                        'quantity': product.stock_quantity,
                        'status': 'available' if product.is_active else 'runout',
                        'options': [
                            {
                                'option_id': idx,
                                'name': opt['name'],
                                'quantity': opt.get('stock', 0)
                            }
                            for idx, opt in enumerate(product.options)
                        ]
                    }
            except Exception as e:
                logger.error(f"재고 정보 조회 오류 ({product_id}): {e}")
                
        return stock_info