import xml.etree.ElementTree as ET
import asyncio
import re
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from html import unescape

from .base_wholesaler import BaseWholesaler, CollectionType, ProductData, CollectionResult
from ...models.wholesaler import WholesalerType


class ZentradeAPI(BaseWholesaler):
    """젠트레이드 XML API 연동 서비스"""
    
    def __init__(self, credentials: Dict[str, Any], logger=None):
        super().__init__(credentials, logger)
        
    @property
    def wholesaler_type(self) -> WholesalerType:
        return WholesalerType.ZENTRADE
        
    @property
    def name(self) -> str:
        return "젠트레이드"
        
    @property
    def base_url(self) -> str:
        return self.credentials.get('base_url', 'https://www.zentrade.co.kr/shop/proc')
        
    @property
    def rate_limit_per_minute(self) -> int:
        return 30  # 1분당 30회 제한 (보수적 설정)
        
    def _get_default_headers(self) -> Dict[str, str]:
        """젠트레이드 전용 HTTP 헤더"""
        return {
            'User-Agent': 'YooniWholesaler-Zentrade/1.0',
            'Accept': 'application/xml, text/xml, */*',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
    def _get_api_params(self) -> Dict[str, str]:
        """기본 API 파라미터"""
        return {
            'id': self.credentials.get('api_id', ''),
            'm_skey': self.credentials.get('api_key', '')
        }
        
    async def authenticate(self) -> bool:
        """API 인증 (연결 테스트로 확인)"""
        try:
            api_id = self.credentials.get('api_id')
            api_key = self.credentials.get('api_key')
            
            if not api_id or not api_key:
                self._last_error = "API ID 또는 API Key가 제공되지 않았습니다"
                return False
                
            # 간단한 상품 조회로 인증 테스트
            params = self._get_api_params()
            
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/product_api.php",
                params=params
            )
            
            if response and response.status == 200:
                content = await response.text(encoding='euc-kr')
                
                # XML 파싱해서 정상 응답인지 확인
                try:
                    root = ET.fromstring(content)
                    if root.tag == 'zentrade':
                        self._authenticated = True
                        self.logger.info("젠트레이드 API 인증 성공")
                        return True
                    else:
                        self._last_error = "유효하지 않은 XML 응답"
                        return False
                        
                except ET.ParseError as e:
                    self._last_error = f"XML 파싱 오류: {str(e)}"
                    return False
            else:
                self._last_error = f"API 응답 오류: {response.status if response else 'No response'}"
                return False
                
        except Exception as e:
            self._last_error = f"인증 중 오류 발생: {str(e)}"
            self.logger.error(self._last_error)
            
        return False
        
    async def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        start_time = datetime.now()
        
        try:
            # 인증 테스트
            auth_result = await self.authenticate()
            if not auth_result:
                return {
                    'success': False,
                    'message': self._last_error or "인증 실패",
                    'response_time_ms': None,
                    'api_info': None,
                    'error_details': {'error_type': 'authentication_failed'}
                }
                
            # 상품 수 조회로 연결 상태 확인
            params = self._get_api_params()
            
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/product_api.php",
                params=params
            )
            
            if response and response.status == 200:
                content = await response.text(encoding='euc-kr')
                
                try:
                    root = ET.fromstring(content)
                    products = root.findall('product')
                    
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return {
                        'success': True,
                        'message': "연결 성공",
                        'response_time_ms': int(response_time),
                        'api_info': {
                            'total_products': len(products),
                            'api_type': 'XML',
                            'encoding': 'euc-kr',
                            'base_url': self.base_url
                        },
                        'error_details': None
                    }
                    
                except ET.ParseError as e:
                    return {
                        'success': False,
                        'message': f"XML 파싱 오류: {str(e)}",
                        'response_time_ms': None,
                        'api_info': None,
                        'error_details': {'error_type': 'xml_parse_error'}
                    }
            else:
                return {
                    'success': False,
                    'message': "API 응답 오류",
                    'response_time_ms': None,
                    'api_info': None,
                    'error_details': {'error_type': 'api_response_error'}
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"연결 테스트 실패: {str(e)}",
                'response_time_ms': None,
                'api_info': None,
                'error_details': {
                    'error_type': 'connection_error',
                    'error_message': str(e)
                }
            }
            
    async def get_categories(self) -> List[Dict[str, Any]]:
        """카테고리 목록 조회 (전체 상품에서 추출)"""
        categories = []
        
        try:
            params = self._get_api_params()
            
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/product_api.php",
                params=params
            )
            
            if response and response.status == 200:
                content = await response.text(encoding='euc-kr')
                root = ET.fromstring(content)
                
                category_set = set()
                
                for product in root.findall('product'):
                    dome_category = product.find('dome_category')
                    if dome_category is not None:
                        category_code = dome_category.get('dome_catecode', '')
                        category_name = self._get_cdata_text(dome_category)
                        
                        if category_code and category_name:
                            category_key = f"{category_code}_{category_name}"
                            if category_key not in category_set:
                                categories.append({
                                    'code': category_code,
                                    'name': category_name,
                                    'level': 1  # 젠트레이드는 단일 레벨
                                })
                                category_set.add(category_key)
                                
                self.logger.info(f"카테고리 {len(categories)}개 추출 완료")
                
        except Exception as e:
            self.logger.error(f"카테고리 조회 실패: {str(e)}")
            
        return categories
        
    def _get_cdata_text(self, element) -> str:
        """CDATA가 포함된 요소에서 텍스트 추출"""
        if element is None:
            return ""
            
        text = element.text or ""
        # CDATA 내용 추출
        if text.strip():
            return text.strip()
        
        # 하위 요소가 있는 경우
        if element.tail:
            text += element.tail
            
        return text.strip()
        
    async def _fetch_products_xml(
        self,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[ET.Element]:
        """상품 XML 데이터 조회"""
        try:
            request_params = self._get_api_params()
            if params:
                request_params.update(params)
                
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/product_api.php",
                params=request_params
            )
            
            if response and response.status == 200:
                content = await response.text(encoding='euc-kr')
                return ET.fromstring(content)
                
        except Exception as e:
            self.logger.error(f"상품 XML 조회 실패: {str(e)}")
            
        return None
        
    async def collect_products(
        self,
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products: int = 1000
    ) -> AsyncGenerator[ProductData, None]:
        """상품 수집"""
        if not self._authenticated:
            auth_success = await self.authenticate()
            if not auth_success:
                return
                
        try:
            # 요청 파라미터 구성
            params = {}
            
            if collection_type == CollectionType.RECENT and filters:
                # 최근 상품 필터
                days = filters.get('days', 7)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                params['opendate_s'] = start_date.strftime('%Y-%m-%d')
                params['opendate_e'] = end_date.strftime('%Y-%m-%d')
                
            elif filters:
                # 기타 필터 적용
                if 'stock_only' in filters and filters['stock_only']:
                    params['runout'] = '0'  # 정상 상품만
                    
                if 'start_date' in filters and 'end_date' in filters:
                    params['opendate_s'] = filters['start_date']
                    params['opendate_e'] = filters['end_date']
                    
            # XML 데이터 조회
            root = await self._fetch_products_xml(params)
            
            if root is None:
                return
                
            products = root.findall('product')
            collected_count = 0
            
            for product_elem in products:
                if collected_count >= max_products:
                    break
                    
                try:
                    normalized_product = self._normalize_product_data_from_xml(product_elem)
                    if normalized_product:
                        yield normalized_product
                        collected_count += 1
                        
                except Exception as e:
                    self.logger.error(f"상품 정규화 실패: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"상품 수집 중 오류: {str(e)}")
            
    def _normalize_product_data_from_xml(self, product_elem: ET.Element) -> Optional[ProductData]:
        """XML 요소를 ProductData로 변환"""
        try:
            # 상품 코드
            product_code = product_elem.get('code', '')
            if not product_code:
                return None
                
            # 상품명
            prdtname_elem = product_elem.find('prdtname')
            product_name = self._get_cdata_text(prdtname_elem) if prdtname_elem is not None else ''
            
            # 가격 정보
            price_elem = product_elem.find('price')
            wholesale_price = 0
            retail_price = 0
            
            if price_elem is not None:
                wholesale_price = self._normalize_price(price_elem.get('buyprice', '0'))
                retail_price = self._normalize_price(price_elem.get('consumerprice', '0'))
                
            # 기본 정보
            baseinfo_elem = product_elem.find('baseinfo')
            origin = ''
            manufacturer = ''
            brand = ''
            model = ''
            
            if baseinfo_elem is not None:
                origin = baseinfo_elem.get('madein', '')
                manufacturer = baseinfo_elem.get('productcom', '')
                brand = baseinfo_elem.get('brand', '')
                model = baseinfo_elem.get('model', '')
                
            # 카테고리 정보
            dome_category_elem = product_elem.find('dome_category')
            category_path = ''
            if dome_category_elem is not None:
                category_path = self._get_cdata_text(dome_category_elem)
                
            # 이미지 정보
            main_image, additional_images = self._extract_images_from_xml(product_elem)
            
            # 상품 상태
            status_elem = product_elem.find('status')
            is_in_stock = True
            open_date = None
            
            if status_elem is not None:
                runout = status_elem.get('runout', '0')
                is_in_stock = runout == '0'
                
                opendate_str = status_elem.get('opendate', '')
                if opendate_str:
                    try:
                        open_date = datetime.strptime(opendate_str, '%Y-%m-%d')
                    except ValueError:
                        pass
                        
            # 옵션 정보
            options = self._extract_options_from_xml(product_elem)
            variants = self._extract_variants_from_options(options)
            
            # 할인율 계산
            discount_rate = 0
            if wholesale_price > 0 and retail_price > wholesale_price:
                discount_rate = int((retail_price - wholesale_price) / retail_price * 100)
                
            # 상세 설명
            content_elem = product_elem.find('content')
            description = self._get_cdata_text(content_elem) if content_elem is not None else ''
            
            # 키워드
            keyword_elem = product_elem.find('keyword')
            keywords = self._get_cdata_text(keyword_elem) if keyword_elem is not None else ''
            
            return ProductData(
                wholesaler_product_id=product_code,
                wholesaler_sku=model,
                name=product_name,
                description=self._clean_html_content(description),
                category_path=category_path,
                wholesale_price=wholesale_price,
                retail_price=retail_price if retail_price != wholesale_price else None,
                discount_rate=discount_rate,
                stock_quantity=1 if is_in_stock else 0,  # 젠트레이드는 정확한 재고 수량 제공 안함
                is_in_stock=is_in_stock,
                main_image_url=main_image,
                additional_images=additional_images,
                options=options,
                variants=variants,
                shipping_info={
                    'origin': origin,
                    'manufacturer': manufacturer,
                    'brand': brand,
                    'keywords': keywords.split(',') if keywords else []
                },
                raw_data=self._xml_element_to_dict(product_elem),
                last_updated=open_date or datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"XML 상품 데이터 정규화 실패: {str(e)}")
            return None
            
    def _extract_images_from_xml(self, product_elem: ET.Element) -> tuple[Optional[str], List[str]]:
        """XML에서 이미지 URL 추출"""
        main_image = None
        additional_images = []
        
        listimg_elem = product_elem.find('listimg')
        if listimg_elem is not None:
            # 최대 5개의 이미지 URL
            for i in range(1, 6):
                url = listimg_elem.get(f'url{i}', '')
                if url:
                    if main_image is None:
                        main_image = url
                    else:
                        additional_images.append(url)
                        
        return main_image, additional_images
        
    def _extract_options_from_xml(self, product_elem: ET.Element) -> Dict[str, Any]:
        """XML에서 옵션 정보 추출"""
        options = {'has_options': False}
        
        option_elem = product_elem.find('option')
        if option_elem is not None:
            opt1nm = option_elem.get('opt1nm', '')
            option_data = self._get_cdata_text(option_elem)
            
            if opt1nm and option_data:
                options['has_options'] = True
                options['option_name'] = opt1nm
                options['raw_option_data'] = option_data
                
                # 옵션 파싱
                parsed_options = self._parse_option_string(option_data)
                options['parsed_options'] = parsed_options
                options['total_combinations'] = len(parsed_options)
                options['available_combinations'] = len([opt for opt in parsed_options if opt.get('available', True)])
                
        return options
        
    def _parse_option_string(self, option_data: str) -> List[Dict[str, Any]]:
        """옵션 문자열 파싱"""
        options = []
        
        try:
            # 옵션 구분자로 분리: ↑=↑
            option_items = option_data.split('↑=↑')
            
            for item in option_items:
                item = item.strip()
                if not item:
                    continue
                    
                # 필드 구분자로 분리: ^|^
                parts = item.split('^|^')
                
                if len(parts) >= 3:
                    option_name = parts[0].strip()
                    buy_price = self._normalize_price(parts[1])
                    consumer_price = self._normalize_price(parts[2])
                    option_image = parts[3].strip() if len(parts) > 3 else ''
                    
                    options.append({
                        'name': option_name,
                        'buy_price': buy_price,
                        'consumer_price': consumer_price,
                        'image_url': option_image,
                        'available': True  # 젠트레이드는 옵션별 품절 정보 없음
                    })
                    
        except Exception as e:
            self.logger.error(f"옵션 파싱 실패: {str(e)}")
            
        return options
        
    def _extract_variants_from_options(self, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """옵션 정보에서 변형 정보 추출"""
        variants = []
        
        if options.get('has_options') and 'parsed_options' in options:
            for i, option in enumerate(options['parsed_options']):
                variant = {
                    'id': str(i),
                    'name': option['name'],
                    'price': option['buy_price'],
                    'consumer_price': option['consumer_price'],
                    'image_url': option.get('image_url', ''),
                    'available': option.get('available', True),
                    'attributes': {
                        options.get('option_name', 'option'): option['name']
                    }
                }
                variants.append(variant)
                
        return variants
        
    def _clean_html_content(self, html_content: str) -> str:
        """HTML 태그 제거 및 텍스트 정리"""
        if not html_content:
            return ""
            
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        
        # HTML 엔티티 디코딩
        clean_text = unescape(clean_text)
        
        # 여러 줄바꿈을 하나로
        clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
        
        return clean_text.strip()
        
    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """XML 요소를 딕셔너리로 변환"""
        result = {}
        
        # 속성들
        if element.attrib:
            result['@attributes'] = element.attrib
            
        # 텍스트 내용
        if element.text and element.text.strip():
            result['text'] = element.text.strip()
            
        # 하위 요소들
        for child in element:
            child_data = self._xml_element_to_dict(child)
            
            if child.tag in result:
                # 같은 태그가 여러 개인 경우 리스트로
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
                
        return result
        
    async def get_product_detail(self, product_code: str) -> Optional[ProductData]:
        """단일 상품 상세 정보 조회"""
        try:
            params = {'goodsno': product_code}
            root = await self._fetch_products_xml(params)
            
            if root is not None:
                product_elem = root.find('product')
                if product_elem is not None:
                    return self._normalize_product_data_from_xml(product_elem)
                    
        except Exception as e:
            self.logger.error(f"상품 상세 정보 조회 실패 (Code: {product_code}): {str(e)}")
            
        return None
        
    async def get_stock_info(self, product_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """재고 정보 조회"""
        stock_info = {}
        
        # 젠트레이드는 개별 상품 조회만 지원하므로 하나씩 조회
        for product_code in product_codes:
            try:
                product_detail = await self.get_product_detail(product_code)
                
                if product_detail:
                    stock_info[product_code] = {
                        'stock_quantity': product_detail.stock_quantity,
                        'is_in_stock': product_detail.is_in_stock,
                        'last_updated': product_detail.last_updated.isoformat() if product_detail.last_updated else None
                    }
                else:
                    stock_info[product_code] = {
                        'stock_quantity': 0,
                        'is_in_stock': False,
                        'error': 'Product not found'
                    }
                    
                # Rate limiting
                await asyncio.sleep(2)  # 2초 간격 (보수적)
                
            except Exception as e:
                self.logger.error(f"재고 정보 조회 실패 (Code: {product_code}): {str(e)}")
                stock_info[product_code] = {
                    'stock_quantity': 0,
                    'is_in_stock': False,
                    'error': str(e)
                }
                
        return stock_info
        
    async def get_recent_products(self, days: int = 7, max_products: int = 1000) -> List[ProductData]:
        """최근 상품 조회"""
        recent_products = []
        
        async for product in self.collect_products(
            collection_type=CollectionType.RECENT,
            filters={'days': days},
            max_products=max_products
        ):
            recent_products.append(product)
            
        return recent_products
        
    async def get_in_stock_products(self, max_products: int = 1000) -> List[ProductData]:
        """재고 있는 상품만 조회"""
        stock_products = []
        
        async for product in self.collect_products(
            collection_type=CollectionType.ALL,
            filters={'stock_only': True},
            max_products=max_products
        ):
            stock_products.append(product)
            
        return stock_products
        
    async def get_order_info(self, order_no: str = None, personal_order_no: str = None) -> Optional[Dict[str, Any]]:
        """주문 정보 조회"""
        if not order_no and not personal_order_no:
            self.logger.error("주문번호 또는 개인주문번호 중 하나는 필수입니다")
            return None
            
        try:
            params = self._get_api_params()
            
            if order_no:
                params['ordno'] = order_no
            if personal_order_no:
                params['pordno'] = personal_order_no
                
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/order_api.php",
                params=params
            )
            
            if response and response.status == 200:
                content = await response.text(encoding='euc-kr')
                root = ET.fromstring(content)
                
                ord_info = root.find('ord_info')
                if ord_info is not None:
                    return self._parse_order_info(ord_info)
                    
        except Exception as e:
            self.logger.error(f"주문 정보 조회 실패: {str(e)}")
            
        return None
        
    def _parse_order_info(self, ord_info_elem: ET.Element) -> Dict[str, Any]:
        """주문 정보 XML 파싱"""
        order_info = {
            'zentrade_order_no': ord_info_elem.get('ordno', ''),
            'personal_order_no': ord_info_elem.get('pordno', ''),
            'order_date': self._get_element_text(ord_info_elem, 'ord_date'),
            'receiver_name': self._get_cdata_text(ord_info_elem.find('nameReceiver')),
            'receiver_phone': self._get_cdata_text(ord_info_elem.find('phoneReceiver')),
            'receiver_mobile': self._get_cdata_text(ord_info_elem.find('mobileReceiver')),
            'receiver_address': self._get_cdata_text(ord_info_elem.find('address')),
            'items': [],
            'delivery_info': {},
            'zentrade_message': self._get_cdata_text(ord_info_elem.find('zentrade_msg'))
        }
        
        # 주문 상품들
        item_num = 1
        while True:
            item_elem = ord_info_elem.find(f'ord_item{item_num}')
            if item_elem is None:
                break
                
            item_text = self._get_cdata_text(item_elem)
            if item_text:
                order_info['items'].append(item_text)
                
            item_num += 1
            
        # 배송 정보
        deli_info_elem = ord_info_elem.find('deli_info')
        if deli_info_elem is not None:
            order_info['delivery_info'] = {
                'delivery_company': deli_info_elem.get('delicom', ''),
                'tracking_number': deli_info_elem.get('delinum', '')
            }
            
        return order_info
        
    def _get_element_text(self, parent: ET.Element, tag: str) -> str:
        """요소에서 텍스트 추출"""
        elem = parent.find(tag)
        return elem.text.strip() if elem is not None and elem.text else ""