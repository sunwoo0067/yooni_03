import json
import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta

from .base_wholesaler import BaseWholesaler, CollectionType, ProductData, CollectionResult
from ...models.wholesaler import WholesalerType


class OwnerClanAPI(BaseWholesaler):
    """오너클랜 GraphQL API 연동 서비스"""
    
    def __init__(self, credentials: Dict[str, Any], logger=None):
        super().__init__(credentials, logger)
        self._jwt_token = None
        self._token_expires_at = None
        
    @property
    def wholesaler_type(self) -> WholesalerType:
        return WholesalerType.OWNERCLAN
        
    @property
    def name(self) -> str:
        return "오너클랜"
        
    @property
    def base_url(self) -> str:
        return self.credentials.get('api_url', 'https://api-sandbox.ownerclan.com/v1/graphql')
        
    @property
    def auth_url(self) -> str:
        return self.credentials.get('auth_url', 'https://auth-sandbox.ownerclan.com/auth')
        
    @property
    def rate_limit_per_minute(self) -> int:
        return 120  # 1분당 120회 제한
        
    def _get_default_headers(self) -> Dict[str, str]:
        """오너클랜 전용 HTTP 헤더"""
        headers = {
            'User-Agent': 'YooniWholesaler-OwnerClan/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # JWT 토큰이 있으면 Authorization 헤더 추가
        if self._jwt_token:
            headers['Authorization'] = f'Bearer {self._jwt_token}'
            
        return headers
        
    async def _get_valid_token(self) -> Optional[str]:
        """유효한 JWT 토큰 반환"""
        # 토큰이 없거나 만료된 경우 재인증
        if not self._jwt_token or (self._token_expires_at and time.time() >= self._token_expires_at):
            auth_success = await self.authenticate()
            if not auth_success:
                return None
                
        return self._jwt_token
        
    async def authenticate(self) -> bool:
        """JWT 토큰 인증"""
        try:
            username = self.credentials.get('username')
            password = self.credentials.get('password')
            
            if not username or not password:
                self._last_error = "사용자명 또는 비밀번호가 제공되지 않았습니다"
                return False
                
            auth_data = {
                "service": "ownerclan",
                "userType": "seller", 
                "username": username,
                "password": password
            }
            
            response = await self._make_request(
                method='POST',
                url=self.auth_url,
                json_data=auth_data
            )
            
            if response and response.status == 200:
                data = await response.json()
                
                self._jwt_token = data.get('token')
                expires_in = data.get('expiresIn', 3600)
                
                # 토큰 만료 5분 전에 갱신하도록 설정
                self._token_expires_at = time.time() + expires_in - 300
                
                self._authenticated = True
                self.logger.info("오너클랜 JWT 토큰 인증 성공")
                return True
            else:
                self._last_error = "인증 요청 실패"
                return False
                
        except Exception as e:
            self._last_error = f"인증 중 오류 발생: {str(e)}"
            self.logger.error(self._last_error)
            
        return False
        
    async def _graphql_request(self, query: str, variables: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """GraphQL 요청 수행"""
        token = await self._get_valid_token()
        if not token:
            return None
            
        request_data = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            response = await self._make_request(
                method='POST',
                url=self.base_url,
                json_data=request_data
            )
            
            if response and response.status == 200:
                data = await response.json()
                
                # GraphQL 오류 확인
                if data.get('errors'):
                    error_messages = [err.get('message', 'Unknown error') for err in data['errors']]
                    self._last_error = f"GraphQL 오류: {', '.join(error_messages)}"
                    self.logger.error(self._last_error)
                    return None
                    
                return data.get('data')
                
        except Exception as e:
            self._last_error = f"GraphQL 요청 실패: {str(e)}"
            self.logger.error(self._last_error)
            
        return None
        
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
                
            # 간단한 쿼리로 연결 테스트
            test_query = """
                query TestConnection {
                    allItems(first: 1) {
                        pageInfo {
                            hasNextPage
                        }
                        edges {
                            node {
                                key
                                name
                            }
                        }
                    }
                }
            """
            
            result = await self._graphql_request(test_query)
            
            if result:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return {
                    'success': True,
                    'message': "연결 성공",
                    'response_time_ms': int(response_time),
                    'api_info': {
                        'api_type': 'GraphQL',
                        'base_url': self.base_url,
                        'auth_url': self.auth_url
                    },
                    'error_details': None
                }
            else:
                return {
                    'success': False,
                    'message': "GraphQL 쿼리 실패",
                    'response_time_ms': None,
                    'api_info': None,
                    'error_details': {'error_type': 'graphql_query_failed'}
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
        """카테고리 목록 조회 (오너클랜은 상품에서 카테고리를 추출)"""
        categories = []
        
        try:
            # 카테고리 정보를 포함한 상품 샘플 조회
            query = """
                query GetCategories {
                    allItems(first: 1000) {
                        edges {
                            node {
                                category {
                                    id
                                    name
                                    level
                                }
                            }
                        }
                    }
                }
            """
            
            result = await self._graphql_request(query)
            
            if result and 'allItems' in result:
                category_set = set()
                
                for edge in result['allItems']['edges']:
                    category = edge['node'].get('category')
                    if category:
                        category_key = f"{category.get('id', '')}_{category.get('name', '')}"
                        if category_key not in category_set:
                            categories.append(category)
                            category_set.add(category_key)
                            
                self.logger.info(f"카테고리 {len(categories)}개 추출 완료")
                
        except Exception as e:
            self.logger.error(f"카테고리 조회 실패: {str(e)}")
            
        return categories
        
    async def _collect_all_product_keys(
        self,
        search_conditions: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """모든 상품 키 수집"""
        product_keys = []
        
        # 기본 쿼리 (전체 상품)
        queries = [{}]
        
        # 검색 조건이 있다면 추가 쿼리 생성
        if search_conditions:
            # 키워드 검색
            if 'keywords' in search_conditions:
                for keyword in search_conditions['keywords']:
                    queries.append({'search': keyword})
                    
            # 가격 범위 검색
            if 'price_ranges' in search_conditions:
                for price_range in search_conditions['price_ranges']:
                    query_vars = {}
                    if 'min' in price_range:
                        query_vars['minPrice'] = price_range['min']
                    if 'max' in price_range:
                        query_vars['maxPrice'] = price_range['max']
                    queries.append(query_vars)
                    
        # 각 쿼리 조건으로 상품 키 수집
        collected_keys = set()
        
        for query_vars in queries:
            try:
                keys = await self._collect_product_keys_with_pagination(query_vars)
                collected_keys.update(keys)
                
                self.logger.info(f"쿼리 조건 {query_vars}: {len(keys)}개 키 수집")
                
            except Exception as e:
                self.logger.error(f"쿼리 {query_vars} 실행 실패: {str(e)}")
                
        product_keys = list(collected_keys)
        self.logger.info(f"총 {len(product_keys)}개 고유 상품 키 수집 완료")
        
        return product_keys
        
    async def _collect_product_keys_with_pagination(
        self,
        query_vars: Dict[str, Any],
        max_products: int = 10000
    ) -> List[str]:
        """페이지네이션을 통한 상품 키 수집"""
        product_keys = []
        has_next_page = True
        cursor = None
        
        query = """
            query GetAllProductKeys($after: String, $first: Int, $minPrice: Int, $maxPrice: Int, $search: String) {
                allItems(after: $after, first: $first, minPrice: $minPrice, maxPrice: $maxPrice, search: $search) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        node {
                            key
                        }
                    }
                }
            }
        """
        
        while has_next_page and len(product_keys) < max_products:
            variables = {
                'first': min(1000, max_products - len(product_keys)),
                'after': cursor,
                **query_vars
            }
            
            try:
                result = await self._graphql_request(query, variables)
                
                if not result or 'allItems' not in result:
                    break
                    
                items_data = result['allItems']
                
                # 현재 페이지의 상품 키들 추가
                for edge in items_data['edges']:
                    product_keys.append(edge['node']['key'])
                    
                # 페이지네이션 정보 업데이트
                page_info = items_data['pageInfo']
                has_next_page = page_info['hasNextPage']
                cursor = page_info['endCursor']
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"페이지네이션 수집 실패: {str(e)}")
                break
                
        return product_keys
        
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
            # 1단계: 상품 키 수집
            if collection_type == CollectionType.CATEGORY and filters and 'categories' in filters:
                # 카테고리별 검색은 별도 처리 필요
                product_keys = await self._collect_category_product_keys(filters['categories'])
            else:
                # 검색 조건 준비
                search_conditions = {}
                
                if collection_type == CollectionType.RECENT and filters:
                    # 최근 상품은 날짜 필터 추가 (오너클랜 API 스펙에 따라 조정 필요)
                    pass
                    
                if filters:
                    search_conditions.update(filters)
                    
                product_keys = await self._collect_all_product_keys(search_conditions)
                
            # 2단계: 상품 상세 정보 수집
            collected_count = 0
            batch_size = 100  # 한 번에 조회할 상품 수
            
            for i in range(0, len(product_keys), batch_size):
                if collected_count >= max_products:
                    break
                    
                batch_keys = product_keys[i:i + batch_size]
                remaining_slots = max_products - collected_count
                
                if len(batch_keys) > remaining_slots:
                    batch_keys = batch_keys[:remaining_slots]
                    
                try:
                    products = await self._get_multiple_product_details(batch_keys)
                    
                    for product_data in products:
                        if product_data:
                            # 최근 상품 필터링
                            if collection_type == CollectionType.RECENT:
                                days = filters.get('days', 7) if filters else 7
                                if not self._is_recent_product(product_data.raw_data, days):
                                    continue
                                    
                            yield product_data
                            collected_count += 1
                            
                except Exception as e:
                    self.logger.error(f"배치 처리 중 오류: {str(e)}")
                    continue
                    
                # Rate limiting
                await asyncio.sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"상품 수집 중 오류: {str(e)}")
            
    async def _collect_category_product_keys(self, category_ids: List[str]) -> List[str]:
        """카테고리별 상품 키 수집"""
        # 오너클랜 API는 카테고리 필터링을 직접 지원하지 않으므로
        # 전체 상품을 조회한 후 클라이언트에서 필터링
        all_keys = await self._collect_all_product_keys()
        
        # 상세 정보에서 카테고리 확인 (성능상 비효율적이지만 필요시 구현)
        # 실제 구현에서는 더 나은 방법을 찾아야 함
        return all_keys
        
    async def _get_multiple_product_details(self, product_keys: List[str]) -> List[Optional[ProductData]]:
        """여러 상품의 상세 정보 조회"""
        if len(product_keys) > 5000:
            self.logger.warning(f"한 번에 최대 5000개까지만 조회 가능 (요청: {len(product_keys)}개)")
            product_keys = product_keys[:5000]
            
        query = """
            query GetMultipleProducts($keys: [String!]!) {
                items(keys: $keys) {
                    key
                    name
                    model
                    production
                    origin
                    price
                    pricePolicy
                    fixedPrice
                    category {
                        id
                        name
                        level
                    }
                    shippingFee
                    shippingType
                    status
                    options {
                        id
                        price
                        quantity
                        optionAttributes {
                            name
                            value
                        }
                    }
                    taxFree
                    adultOnly
                    returnable
                    images
                    createdAt
                    updatedAt
                }
            }
        """
        
        try:
            result = await self._graphql_request(query, {'keys': product_keys})
            
            if result and 'items' in result:
                products = []
                for item_data in result['items']:
                    if item_data:  # None이 아닌 경우만 처리
                        normalized_product = self._normalize_product_data(item_data)
                        products.append(normalized_product)
                    else:
                        products.append(None)
                        
                return products
                
        except Exception as e:
            self.logger.error(f"다중 상품 조회 실패: {str(e)}")
            
        return []
        
    def _is_recent_product(self, raw_data: Dict[str, Any], days: int) -> bool:
        """최근 상품 여부 확인"""
        try:
            created_at = raw_data.get('createdAt')
            if created_at:
                # Unix timestamp 형태인 경우
                if isinstance(created_at, (int, float)):
                    created_date = datetime.fromtimestamp(created_at)
                # ISO 형태인 경우
                else:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                cutoff_date = datetime.now() - timedelta(days=days)
                return created_date >= cutoff_date
                
        except Exception as e:
            self.logger.debug(f"날짜 파싱 실패: {str(e)}")
            
        return True  # 날짜를 확인할 수 없으면 포함
        
    def _normalize_product_data(self, raw_data: Dict[str, Any]) -> Optional[ProductData]:
        """원본 데이터를 ProductData로 변환"""
        try:
            product_key = raw_data.get('key', '')
            if not product_key:
                return None
                
            # 가격 정보
            base_price = self._normalize_price(raw_data.get('price', 0))
            fixed_price = self._normalize_price(raw_data.get('fixedPrice', 0))
            wholesale_price = fixed_price if fixed_price > 0 else base_price
            
            # 옵션 처리
            options_data = raw_data.get('options', [])
            total_stock = sum(self._normalize_stock(opt.get('quantity', 0)) for opt in options_data)
            
            # 이미지 처리
            images = raw_data.get('images', [])
            main_image = images[0] if images else None
            additional_images = images[1:] if len(images) > 1 else []
            
            # 카테고리 경로 구성
            category = raw_data.get('category', {})
            category_path = category.get('name', '') if category else ''
            
            # 배송 정보
            shipping_fee = self._normalize_price(raw_data.get('shippingFee', 0))
            shipping_type = raw_data.get('shippingType', '')
            
            return ProductData(
                wholesaler_product_id=product_key,
                wholesaler_sku=raw_data.get('model', ''),
                name=raw_data.get('name', ''),
                description=raw_data.get('production', ''),
                category_path=category_path,
                wholesale_price=wholesale_price,
                retail_price=base_price if base_price != wholesale_price else None,
                discount_rate=None,
                stock_quantity=total_stock,
                is_in_stock=total_stock > 0 and raw_data.get('status') == 'ACTIVE',
                main_image_url=main_image,
                additional_images=additional_images,
                options=self._extract_options(raw_data),
                variants=self._extract_variants(options_data),
                shipping_info={
                    'shipping_fee': shipping_fee,
                    'shipping_type': shipping_type,
                    'free_shipping': shipping_fee == 0,
                    'origin': raw_data.get('origin', ''),
                    'returnable': raw_data.get('returnable', False),
                    'tax_free': raw_data.get('taxFree', False),
                    'adult_only': raw_data.get('adultOnly', False)
                },
                raw_data=raw_data,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"상품 데이터 정규화 실패: {str(e)}")
            return None
            
    def _extract_options(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """상품 옵션 정보 추출"""
        options = {}
        options_data = raw_data.get('options', [])
        
        if options_data:
            options['has_options'] = True
            options['total_combinations'] = len(options_data)
            
            # 옵션 속성별 그룹화
            attribute_groups = {}
            for option in options_data:
                for attr in option.get('optionAttributes', []):
                    attr_name = attr.get('name', '')
                    attr_value = attr.get('value', '')
                    
                    if attr_name:
                        if attr_name not in attribute_groups:
                            attribute_groups[attr_name] = set()
                        attribute_groups[attr_name].add(attr_value)
                        
            # Set을 List로 변환
            for key, values in attribute_groups.items():
                attribute_groups[key] = list(values)
                
            options['attribute_groups'] = attribute_groups
            options['available_combinations'] = len([opt for opt in options_data if opt.get('quantity', 0) > 0])
        else:
            options['has_options'] = False
            options['total_combinations'] = 0
            options['available_combinations'] = 0
            
        return options
        
    def _extract_variants(self, options_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """상품 변형 정보 추출"""
        variants = []
        
        for option in options_data:
            variant = {
                'id': option.get('id', ''),
                'price': self._normalize_price(option.get('price', 0)),
                'quantity': self._normalize_stock(option.get('quantity', 0)),
                'attributes': {}
            }
            
            # 옵션 속성들
            for attr in option.get('optionAttributes', []):
                attr_name = attr.get('name', '')
                attr_value = attr.get('value', '')
                if attr_name and attr_value:
                    variant['attributes'][attr_name] = attr_value
                    
            variants.append(variant)
            
        return variants
        
    async def get_product_detail(self, product_key: str) -> Optional[ProductData]:
        """단일 상품 상세 정보 조회"""
        query = """
            query GetProductDetail($key: String!) {
                item(key: $key) {
                    key
                    name
                    model
                    production
                    origin
                    price
                    pricePolicy
                    fixedPrice
                    category {
                        id
                        name
                        level
                    }
                    shippingFee
                    shippingType
                    status
                    options {
                        id
                        price
                        quantity
                        optionAttributes {
                            name
                            value
                        }
                    }
                    taxFree
                    adultOnly
                    returnable
                    images
                    createdAt
                    updatedAt
                }
            }
        """
        
        try:
            result = await self._graphql_request(query, {'key': product_key})
            
            if result and 'item' in result and result['item']:
                return self._normalize_product_data(result['item'])
                
        except Exception as e:
            self.logger.error(f"상품 상세 정보 조회 실패 (Key: {product_key}): {str(e)}")
            
        return None
        
    async def get_stock_info(self, product_keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """재고 정보 조회"""
        stock_info = {}
        
        try:
            products = await self._get_multiple_product_details(product_keys)
            
            for i, product in enumerate(products):
                key = product_keys[i]
                
                if product:
                    stock_info[key] = {
                        'stock_quantity': product.stock_quantity,
                        'is_in_stock': product.is_in_stock,
                        'last_updated': product.last_updated.isoformat() if product.last_updated else None,
                        'variants': [
                            {
                                'id': variant['id'],
                                'quantity': variant['quantity'],
                                'attributes': variant['attributes']
                            }
                            for variant in product.variants or []
                        ]
                    }
                else:
                    stock_info[key] = {
                        'stock_quantity': 0,
                        'is_in_stock': False,
                        'error': 'Product not found'
                    }
                    
        except Exception as e:
            self.logger.error(f"재고 정보 조회 실패: {str(e)}")
            
            # 오류 발생 시 모든 상품에 대해 오류 정보 반환
            for key in product_keys:
                stock_info[key] = {
                    'stock_quantity': 0,
                    'is_in_stock': False,
                    'error': str(e)
                }
                
        return stock_info
        
    async def get_product_histories(
        self,
        product_key: Optional[str] = None,
        history_kind: Optional[str] = None,
        date_from: Optional[int] = None,
        max_records: int = 1000
    ) -> List[Dict[str, Any]]:
        """상품 변경 이력 조회"""
        histories = []
        
        query = """
            query GetProductHistories($after: String, $first: Int, $dateFrom: Int, $kind: ItemHistoryKind, $itemKey: ID) {
                itemHistories(after: $after, first: $first, dateFrom: $dateFrom, kind: $kind, itemKey: $itemKey) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        node {
                            id
                            timestamp
                            kind
                            itemKey
                            description
                            changes {
                                field
                                oldValue
                                newValue
                            }
                        }
                    }
                }
            }
        """
        
        variables = {
            'first': min(100, max_records),
            'dateFrom': date_from,
            'kind': history_kind,
            'itemKey': product_key
        }
        
        has_next_page = True
        cursor = None
        
        try:
            while has_next_page and len(histories) < max_records:
                variables['after'] = cursor
                variables['first'] = min(100, max_records - len(histories))
                
                result = await self._graphql_request(query, variables)
                
                if not result or 'itemHistories' not in result:
                    break
                    
                histories_data = result['itemHistories']
                
                for edge in histories_data['edges']:
                    histories.append(edge['node'])
                    
                page_info = histories_data['pageInfo']
                has_next_page = page_info['hasNextPage']
                cursor = page_info['endCursor']
                
                await asyncio.sleep(0.1)  # Rate limiting
                
        except Exception as e:
            self.logger.error(f"상품 이력 조회 실패: {str(e)}")
            
        return histories