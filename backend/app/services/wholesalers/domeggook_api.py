import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta

from .base_wholesaler import BaseWholesaler, CollectionType, ProductData, CollectionResult
from ...models.wholesaler import WholesalerType
from ...core.performance import redis_cache, batch_process, optimize_memory_usage


class DomeggookAPI(BaseWholesaler):
    """도매매(도매꾹) API 연동 서비스"""
    
    def __init__(self, credentials: Dict[str, Any], logger=None):
        super().__init__(credentials, logger)
        self._categories_cache = {}
        self._middle_categories_cache = []
        
    @property
    def wholesaler_type(self) -> WholesalerType:
        return WholesalerType.DOMEGGOOK
        
    @property
    def name(self) -> str:
        return "도매매(도매꾹)"
        
    @property
    def base_url(self) -> str:
        return "https://openapi.domeggook.com"
        
    @property
    def rate_limit_per_minute(self) -> int:
        return 60  # 1분당 60회 제한
        
    def _get_default_headers(self) -> Dict[str, str]:
        """도매꾹 전용 HTTP 헤더"""
        return {
            'User-Agent': 'YooniWholesaler-Domeggook/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
    async def authenticate(self) -> bool:
        """API 인증 (API 키 검증)"""
        try:
            api_key = self.credentials.get('api_key')
            if not api_key:
                self._last_error = "API 키가 제공되지 않았습니다"
                return False
                
            # 카테고리 조회로 API 키 유효성 검증
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/api/category/list",
                params={
                    'api_key': api_key,
                    'version': '1.0'
                }
            )
            
            if response and response.status == 200:
                data = await response.json()
                if data.get('result') == 'success':
                    self._authenticated = True
                    self.logger.info("도매매 API 인증 성공")
                    return True
                else:
                    self._last_error = f"API 인증 실패: {data.get('message', 'Unknown error')}"
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
                
            # 기본 정보 조회
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/api/category/list",
                params={
                    'api_key': self.credentials.get('api_key'),
                    'version': '1.0'
                }
            )
            
            if response and response.status == 200:
                data = await response.json()
                categories = data.get('data', [])
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return {
                    'success': True,
                    'message': "연결 성공",
                    'response_time_ms': int(response_time),
                    'api_info': {
                        'total_categories': len(categories),
                        'api_version': '1.0',
                        'base_url': self.base_url
                    },
                    'error_details': None
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
            
    @redis_cache(expiration=3600)
    async def get_categories(self) -> List[Dict[str, Any]]:
        """카테고리 목록 조회"""
        if self._categories_cache:
            return list(self._categories_cache.values())
            
        try:
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/api/category/list",
                params={
                    'api_key': self.credentials.get('api_key'),
                    'version': '1.0'
                }
            )
            
            if response and response.status == 200:
                data = await response.json()
                if data.get('result') == 'success':
                    categories = data.get('data', [])
                    
                    # 카테고리 캐시 저장
                    for category in categories:
                        category_code = category.get('category_code', '')
                        if category_code:
                            self._categories_cache[category_code] = category
                            
                    self.logger.info(f"카테고리 {len(categories)}개 조회 완료")
                    return categories
                    
        except Exception as e:
            self.logger.error(f"카테고리 조회 실패: {str(e)}")
            
        return []
        
    def _filter_middle_categories(self, categories: List[Dict[str, Any]]) -> List[str]:
        """중분류 카테고리 코드 추출"""
        if self._middle_categories_cache:
            return self._middle_categories_cache
            
        middle_categories = []
        
        for category in categories:
            code = category.get('category_code', '')
            
            # 중분류 패턴: XX_XX_00_00_00
            if code.endswith('_00_00_00') and not code.endswith('_00_00_00_00'):
                middle_categories.append(code)
                
        # 중복 제거 및 정렬
        middle_categories = sorted(list(set(middle_categories)))
        self._middle_categories_cache = middle_categories
        
        self.logger.info(f"중분류 카테고리 {len(middle_categories)}개 추출")
        return middle_categories
        
    async def _get_product_list_page(
        self,
        category_code: str,
        page: int = 1,
        per_page: int = 100
    ) -> Dict[str, Any]:
        """카테고리별 상품 목록 한 페이지 조회"""
        try:
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/api/product/list",
                params={
                    'api_key': self.credentials.get('api_key'),
                    'version': '4.1',
                    'category_code': category_code,
                    'page': page,
                    'limit': min(per_page, 100)  # 최대 100개 제한
                }
            )
            
            if response and response.status == 200:
                data = await response.json()
                if data.get('result') == 'success':
                    return data
                else:
                    self.logger.warning(f"API 응답 오류: {data.get('message')}")
                    
        except Exception as e:
            self.logger.error(f"상품 목록 조회 실패 (카테고리: {category_code}, 페이지: {page}): {str(e)}")
            
        return {}
        
    @optimize_memory_usage
    async def _collect_category_products(self, category_code: str) -> List[Dict[str, Any]]:
        """특정 카테고리의 모든 상품 수집"""
        all_products = []
        page = 1
        
        self.logger.info(f"카테고리 {category_code} 상품 수집 시작")
        
        while True:
            try:
                response_data = await self._get_product_list_page(category_code, page)
                products = response_data.get('data', {}).get('items', [])
                
                if not products:
                    break
                    
                all_products.extend(products)
                
                # 페이지네이션 정보 확인
                pagination = response_data.get('data', {}).get('pagination', {})
                current_page = pagination.get('current_page', page)
                total_pages = pagination.get('total_pages', 1)
                
                self.logger.debug(
                    f"카테고리 {category_code}: {current_page}/{total_pages} 페이지 완료 "
                    f"({len(products)}개 상품)"
                )
                
                if current_page >= total_pages:
                    break
                    
                page += 1
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"카테고리 {category_code}, 페이지 {page} 수집 실패: {str(e)}")
                break
                
        self.logger.info(f"카테고리 {category_code} 총 {len(all_products)}개 상품 수집 완료")
        return all_products
        
    @batch_process(batch_size=100)
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
            # 수집할 카테고리 결정
            if collection_type == CollectionType.CATEGORY and filters and 'categories' in filters:
                category_codes = filters['categories']
            else:
                categories = await self.get_categories()
                category_codes = self._filter_middle_categories(categories)
                
            collected_count = 0
            
            for category_code in category_codes:
                if collected_count >= max_products:
                    break
                    
                try:
                    products = await self._collect_category_products(category_code)
                    
                    for product_data in products:
                        if collected_count >= max_products:
                            break
                            
                        # 최근 상품 필터링
                        if collection_type == CollectionType.RECENT:
                            days = filters.get('days', 7) if filters else 7
                            if not self._is_recent_product(product_data, days):
                                continue
                                
                        # ProductData 객체로 변환
                        normalized_product = self._normalize_product_data(product_data)
                        if normalized_product:
                            yield normalized_product
                            collected_count += 1
                            
                except Exception as e:
                    self.logger.error(f"카테고리 {category_code} 처리 중 오류: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"상품 수집 중 오류: {str(e)}")
            
    def _is_recent_product(self, product_data: Dict[str, Any], days: int) -> bool:
        """최근 상품 여부 확인"""
        try:
            # 상품 등록일 확인 (도매꾹 API 스펙에 따라 조정 필요)
            reg_date_str = product_data.get('reg_date', '')
            if reg_date_str:
                reg_date = datetime.strptime(reg_date_str, '%Y-%m-%d %H:%M:%S')
                cutoff_date = datetime.now() - timedelta(days=days)
                return reg_date >= cutoff_date
        except:
            pass
            
        return True  # 날짜를 확인할 수 없으면 포함
        
    def _normalize_product_data(self, raw_data: Dict[str, Any]) -> Optional[ProductData]:
        """원본 데이터를 ProductData로 변환"""
        try:
            product_id = raw_data.get('product_id', '')
            if not product_id:
                return None
                
            # 가격 정보 추출
            wholesale_price = self._normalize_price(raw_data.get('domPrice', 0))
            retail_price = self._normalize_price(raw_data.get('consumerPrice', 0))
            
            # 재고 정보
            stock_quantity = self._normalize_stock(raw_data.get('stock', 0))
            is_in_stock = stock_quantity > 0 and raw_data.get('status', '') != 'sold_out'
            
            # 이미지 처리
            main_image, additional_images = self._extract_images(raw_data)
            
            # 카테고리 경로
            category_path = raw_data.get('categoryName', '')
            
            # 할인율 계산
            discount_rate = 0
            if wholesale_price > 0 and retail_price > wholesale_price:
                discount_rate = int((retail_price - wholesale_price) / retail_price * 100)
                
            return ProductData(
                wholesaler_product_id=product_id,
                wholesaler_sku=raw_data.get('sku', ''),
                name=raw_data.get('itemName', ''),
                description=raw_data.get('itemInfo', ''),
                category_path=category_path,
                wholesale_price=wholesale_price,
                retail_price=retail_price,
                discount_rate=discount_rate,
                stock_quantity=stock_quantity,
                is_in_stock=is_in_stock,
                main_image_url=main_image,
                additional_images=additional_images,
                options=self._extract_options(raw_data),
                shipping_info=self._extract_shipping_info(raw_data),
                raw_data=raw_data,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"상품 데이터 정규화 실패: {str(e)}")
            return None
            
    def _extract_images(self, data: Dict[str, Any]) -> tuple[Optional[str], List[str]]:
        """이미지 URL 추출"""
        main_image = None
        additional_images = []
        
        # 메인 이미지
        main_img = data.get('mainImage', '') or data.get('image_url', '')
        if main_img:
            main_image = main_img
            
        # 추가 이미지들
        img_list = data.get('imageList', [])
        if isinstance(img_list, list):
            additional_images = [img for img in img_list if img and img != main_image]
        elif isinstance(img_list, str) and img_list:
            # 콤마로 구분된 문자열인 경우
            additional_images = [img.strip() for img in img_list.split(',') if img.strip() != main_image]
            
        return main_image, additional_images
        
    def _extract_options(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """상품 옵션 정보 추출"""
        options = {}
        
        # 주문옵션 JSON 파싱
        option_json_str = data.get('itemOptJson', '')
        if option_json_str:
            try:
                option_data = json.loads(option_json_str)
                options['option_data'] = option_data
                options['has_options'] = True
                
                # 옵션 조합 추출
                if 'data' in option_data:
                    combinations = []
                    for key, value in option_data['data'].items():
                        combination = {
                            'key': key,
                            'name': value.get('name', ''),
                            'price': value.get('domPrice', 0),
                            'quantity': value.get('qty', 0),
                            'status': value.get('hid', 0),
                            'available': value.get('hid') == 0 and value.get('qty', 0) > 0
                        }
                        combinations.append(combination)
                    options['combinations'] = combinations
                    
            except json.JSONDecodeError:
                self.logger.warning(f"옵션 JSON 파싱 실패: {data.get('product_id', 'unknown')}")
                options['has_options'] = False
        else:
            options['has_options'] = False
            
        return options
        
    def _extract_shipping_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """배송 정보 추출"""
        shipping_info = {}
        
        # 배송비 정보
        shipping_cost = data.get('shippingCost', 0)
        free_shipping_min = data.get('freeShippingMin', 0)
        
        shipping_info.update({
            'shipping_cost': self._normalize_price(shipping_cost),
            'free_shipping_minimum': self._normalize_price(free_shipping_min),
            'shipping_method': data.get('shippingMethod', ''),
            'delivery_days': data.get('deliveryDays', 0)
        })
        
        return shipping_info
        
    async def get_product_detail(self, product_id: str) -> Optional[ProductData]:
        """상품 상세 정보 조회"""
        try:
            response = await self._make_request(
                method='GET',
                url=f"{self.base_url}/api/product/detail",
                params={
                    'api_key': self.credentials.get('api_key'),
                    'version': '4.5',
                    'product_id': product_id
                }
            )
            
            if response and response.status == 200:
                data = await response.json()
                if data.get('result') == 'success':
                    item_info = data.get('data', {}).get('itemInfo', {})
                    if item_info:
                        return self._normalize_product_data(item_info)
                        
        except Exception as e:
            self.logger.error(f"상품 상세 정보 조회 실패 (ID: {product_id}): {str(e)}")
            
        return None
        
    @batch_process(batch_size=50)
    async def get_stock_info(self, product_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """재고 정보 조회"""
        stock_info = {}
        
        # 도매꾹은 개별 상품 조회로 재고 확인
        for product_id in product_ids:
            try:
                product_detail = await self.get_product_detail(product_id)
                if product_detail:
                    stock_info[product_id] = {
                        'stock_quantity': product_detail.stock_quantity,
                        'is_in_stock': product_detail.is_in_stock,
                        'last_updated': product_detail.last_updated.isoformat()
                    }
                    
            except Exception as e:
                self.logger.error(f"재고 정보 조회 실패 (ID: {product_id}): {str(e)}")
                stock_info[product_id] = {
                    'stock_quantity': 0,
                    'is_in_stock': False,
                    'error': str(e)
                }
                
            # Rate limiting
            await asyncio.sleep(0.5)
            
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
        
    async def get_category_products(
        self,
        category_codes: List[str],
        max_products: int = 1000
    ) -> List[ProductData]:
        """카테고리별 상품 조회"""
        category_products = []
        
        async for product in self.collect_products(
            collection_type=CollectionType.CATEGORY,
            filters={'categories': category_codes},
            max_products=max_products
        ):
            category_products.append(product)
            
        return category_products