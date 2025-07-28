import xml.etree.ElementTree as ET
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from html import unescape

from .base_collector import BaseCollector, ProductData

class ZentradeCollector(BaseCollector):
    """젠트레이드 수집기 - 3,500개 상품 전체 수집"""
    
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
        
    async def authenticate(self) -> bool:
        """API 인증 확인"""
        try:
            params = self._get_api_params()
            params.update({
                'proc': 'get_product_list',
                'start': '1',
                'limit': '1'  # 1개만 테스트
            })
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    data=params,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        # XML 파싱 가능한지 확인
                        ET.fromstring(text)
                        self.logger.info("젠트레이드 API 인증 성공")
                        return True
                    else:
                        self.logger.error(f"젠트레이드 API 인증 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"젠트레이드 API 인증 중 오류: {e}")
            return False
            
    async def collect_products(self, incremental: bool = False) -> AsyncGenerator[ProductData, None]:
        """상품 수집 - 3,500개 전체 수집"""
        batch_size = 100  # 한 번에 100개씩 요청
        total_collected = 0
        start_index = 1
        
        self.logger.info(f"젠트레이드 상품 수집 시작 (incremental={incremental})")
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    # API 요청 파라미터 구성
                    params = self._get_api_params()
                    params.update({
                        'proc': 'get_product_list',
                        'start': str(start_index),
                        'limit': str(batch_size)
                    })
                    
                    # API 요청
                    async with session.post(
                        self.base_url,
                        data=params,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        
                        if response.status != 200:
                            self.logger.error(f"API 요청 실패: HTTP {response.status}")
                            break
                            
                        xml_text = await response.text()
                        
                        # XML 파싱
                        try:
                            root = ET.fromstring(xml_text)
                        except ET.ParseError as e:
                            self.logger.error(f"XML 파싱 실패: {e}")
                            break
                            
                        # 상품 데이터 추출
                        products = root.findall('.//product')
                        
                        if not products:
                            self.logger.info("더 이상 수집할 상품이 없습니다")
                            break
                            
                        # 각 상품 처리
                        for product_xml in products:
                            try:
                                product_data = self._parse_product_xml(product_xml)
                                if product_data:
                                    yield product_data
                                    total_collected += 1
                                    
                            except Exception as e:
                                self.logger.error(f"상품 파싱 오류: {e}")
                                continue
                                
                        self.logger.info(f"배치 수집 완료: {start_index}~{start_index + len(products) - 1} ({total_collected}개 누적)")
                        
                        # 다음 배치로 이동
                        start_index += batch_size
                        
                        # 3,500개 제한 확인 (안전장치)
                        if total_collected >= 3500:
                            self.logger.info("젠트레이드 최대 상품 수(3,500개) 도달")
                            break
                            
                        # API 호출 간격 (Rate Limiting)
                        await asyncio.sleep(2)  # 2초 대기
                        
                except Exception as e:
                    self.logger.error(f"배치 수집 중 오류: {e}")
                    break
                    
        self.logger.info(f"젠트레이드 상품 수집 완료: 총 {total_collected}개")
        
    def _parse_product_xml(self, product_xml: ET.Element) -> Optional[ProductData]:
        """XML에서 상품 데이터 추출"""
        try:
            # 필수 필드 추출
            product_code = self._get_xml_text(product_xml, 'product_code')
            if not product_code:
                return None
                
            # 모든 상품 정보를 JSON으로 구성
            product_info = {
                'product_code': product_code,
                'product_name': self._get_xml_text(product_xml, 'product_name'),
                'price': self._get_xml_text(product_xml, 'price'),
                'sale_price': self._get_xml_text(product_xml, 'sale_price'),
                'category': self._get_xml_text(product_xml, 'category'),
                'brand': self._get_xml_text(product_xml, 'brand'),
                'model': self._get_xml_text(product_xml, 'model'),
                'description': self._get_xml_text(product_xml, 'description'),
                'images': self._extract_images(product_xml),
                'spec': self._extract_spec(product_xml),
                'stock_status': self._get_xml_text(product_xml, 'stock_status'),
                'shipping_fee': self._get_xml_text(product_xml, 'shipping_fee'),
                'return_fee': self._get_xml_text(product_xml, 'return_fee'),
                'url': self._get_xml_text(product_xml, 'url'),
                'collected_at': datetime.now().isoformat(),
                'supplier': 'zentrade'
            }
            
            return ProductData(
                product_code=product_code,
                product_info=product_info,
                supplier='zentrade'
            )
            
        except Exception as e:
            self.logger.error(f"상품 XML 파싱 오류: {e}")
            return None
            
    def _get_xml_text(self, element: ET.Element, tag: str) -> str:
        """XML에서 텍스트 추출 (HTML 디코딩 포함)"""
        try:
            elem = element.find(tag)
            if elem is not None and elem.text:
                return unescape(elem.text.strip())
            return ""
        except Exception:
            return ""
            
    def _extract_images(self, product_xml: ET.Element) -> List[str]:
        """이미지 URL 추출"""
        images = []
        try:
            # 이미지 요소들 찾기
            img_elements = product_xml.findall('.//image') + product_xml.findall('.//img_url')
            for img_elem in img_elements:
                if img_elem.text:
                    images.append(img_elem.text.strip())
        except Exception:
            pass
        return images
        
    def _extract_spec(self, product_xml: ET.Element) -> Dict[str, str]:
        """상품 스펙 추출"""
        spec = {}
        try:
            spec_element = product_xml.find('specification')
            if spec_element is not None:
                for spec_item in spec_element:
                    if spec_item.tag and spec_item.text:
                        spec[spec_item.tag] = spec_item.text.strip()
        except Exception:
            pass
        return spec