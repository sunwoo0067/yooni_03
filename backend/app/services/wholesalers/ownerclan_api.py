"""
오너클랜 API 서비스 (수정된 버전)
JWT 토큰이 텍스트로 반환되는 것을 처리
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timezone
import logging

from app.services.wholesalers.base_wholesaler import (
    BaseWholesaler, 
    ProductData, 
    CollectionType
)
from app.core.retry import async_retry, RETRYABLE_EXCEPTIONS

logger = logging.getLogger(__name__)


class OwnerClanAPIFixed(BaseWholesaler):
    """수정된 오너클랜 API 구현"""
    
    @property
    def wholesaler_type(self):
        return "ownerclan"
    
    @property
    def name(self):
        return "오너클랜"
    
    @property
    def base_url(self):
        return self.api_url
    
    @property
    def rate_limit_per_minute(self):
        return 60  # 분당 60회
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.username = credentials.get('username')
        self.password = credentials.get('password')
        
        # Production URL 사용 (Sandbox도 가능)
        use_sandbox = credentials.get('use_sandbox', False)
        if use_sandbox:
            self.auth_url = credentials.get('auth_url', 'https://auth-sandbox.ownerclan.com/auth')
            self.api_url = credentials.get('api_url', 'https://api-sandbox.ownerclan.com/v1/graphql')
        else:
            self.auth_url = credentials.get('auth_url', 'https://auth.ownerclan.com/auth')
            self.api_url = credentials.get('api_url', 'https://api.ownerclan.com/v1/graphql')
            
        self.token = None
        self.token_expires_at = None
        
    @async_retry(
        max_attempts=3,
        delay=1.0,
        exceptions=(aiohttp.ClientError, ConnectionError, TimeoutError),
        log_errors=True
    )
    async def authenticate(self) -> bool:
        """JWT 토큰 발급 (텍스트로 반환되는 것 처리)"""
        auth_data = {
            "service": "ownerclan",
            "userType": "seller",
            "username": self.username,
            "password": self.password
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.auth_url, json=auth_data) as response:
                    if response.status == 200:
                        # 응답이 JSON이 아닌 순수 토큰 텍스트로 오는 경우 처리
                        response_text = await response.text()
                        response_text = response_text.strip()
                        
                        # JWT 토큰 형식 확인
                        if response_text.startswith('eyJ') and len(response_text) > 100:
                            self.token = response_text
                            # 토큰 만료 시간 설정 (기본 1시간)
                            self.token_expires_at = datetime.now(timezone.utc).timestamp() + 3600
                            logger.info(f"오너클랜 인증 성공 (토큰 길이: {len(self.token)})")
                            return True
                        else:
                            # JSON 응답 시도
                            try:
                                data = json.loads(response_text)
                                if 'token' in data:
                                    self.token = data['token']
                                    expires_in = data.get('expiresIn', 3600)
                                    self.token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in
                                    logger.info("오너클랜 인증 성공 (JSON 응답)")
                                    return True
                            except json.JSONDecodeError:
                                pass
                                
                            logger.error(f"예상치 못한 토큰 형식: {response_text[:50]}...")
                            return False
                    else:
                        logger.error(f"오너클랜 인증 실패: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"오너클랜 인증 중 오류: {e}")
            return False
            
    async def test_connection(self) -> Dict[str, any]:
        """연결 테스트"""
        try:
            # 인증 시도
            auth_success = await self.authenticate()
            
            if auth_success and self.token:
                # 간단한 GraphQL 쿼리로 테스트
                query = """
                query TestConnection {
                    allItems(first: 1) {
                        edges {
                            node {
                                key
                                name
                            }
                        }
                    }
                }
                """
                
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.token}'
                    }
                    
                    async with session.post(
                        self.api_url, 
                        headers=headers,
                        json={'query': query}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'errors' not in data:
                                return {
                                    'success': True,
                                    'message': '연결 성공',
                                    'details': {
                                        'authenticated': True,
                                        'api_accessible': True,
                                        'environment': 'production' if 'sandbox' not in self.api_url else 'sandbox'
                                    }
                                }
                                
            return {
                'success': False,
                'message': '인증 실패' if not auth_success else 'API 접근 실패'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'연결 오류: {str(e)}'
            }
            
    async def get_categories(self) -> List[Dict[str, any]]:
        """카테고리 목록 조회"""
        await self._ensure_authenticated()
        
        query = """
        query GetCategories {
            categories {
                id
                name
                level
                parentId
            }
        }
        """
        
        try:
            result = await self._graphql_request(query)
            categories = result.get('data', {}).get('categories', [])
            return categories
        except Exception as e:
            logger.error(f"카테고리 조회 오류: {e}")
            return []
            
    async def collect_products(
        self, 
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict] = None,
        max_products: Optional[int] = None
    ) -> AsyncGenerator[ProductData, None]:
        """상품 수집"""
        await self._ensure_authenticated()
        
        # 필터 설정
        graphql_filters = {}
        if filters:
            if 'search' in filters:
                graphql_filters['search'] = filters['search']
            if 'minPrice' in filters:
                graphql_filters['minPrice'] = filters['minPrice']
            if 'maxPrice' in filters:
                graphql_filters['maxPrice'] = filters['maxPrice']
                
        # 페이지네이션을 통한 전체 상품 수집
        cursor = None
        collected_count = 0
        
        while True:
            query = """
            query GetAllItems($after: String, $first: Int, $search: String, $minPrice: Int, $maxPrice: Int) {
                allItems(after: $after, first: $first, search: $search, minPrice: $minPrice, maxPrice: $maxPrice) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        cursor
                        node {
                            key
                            name
                            model
                            price
                            status
                            category {
                                id
                                name
                            }
                            options {
                                id
                                price
                                quantity
                                optionAttributes {
                                    name
                                    value
                                }
                            }
                            images
                            shippingFee
                            shippingType
                            taxFree
                            adultOnly
                            returnable
                            createdAt
                            updatedAt
                        }
                    }
                }
            }
            """
            
            variables = {
                'first': 100,  # 한 번에 100개씩
                'after': cursor,
                **graphql_filters
            }
            
            try:
                result = await self._graphql_request(query, variables)
                data = result.get('data', {}).get('allItems', {})
                edges = data.get('edges', [])
                page_info = data.get('pageInfo', {})
                
                for edge in edges:
                    product_data = edge.get('node', {})
                    
                    # ProductData 객체 생성
                    product = ProductData(
                        wholesaler_type=self.WHOLESALER_TYPE,
                        wholesaler_product_id=product_data.get('key'),
                        name=product_data.get('name', ''),
                        wholesale_price=product_data.get('price', 0),
                        retail_price=int(product_data.get('price', 0) * 1.5),  # 예상 소매가
                        stock_quantity=sum(
                            opt.get('quantity', 0) for opt in product_data.get('options', [])
                        ),
                        minimum_order_quantity=1,
                        description='',  # 상세 설명은 별도 API 필요
                        main_image_url=product_data.get('images', [''])[0] if product_data.get('images') else '',
                        additional_images=product_data.get('images', [])[1:] if len(product_data.get('images', [])) > 1 else [],
                        category_path=product_data.get('category', {}).get('name', ''),
                        brand=product_data.get('brand', ''),
                        model_name=product_data.get('model', ''),
                        shipping_fee=product_data.get('shippingFee', 0),
                        is_active=product_data.get('status') == 'available',
                        options=self._parse_options(product_data.get('options', [])),
                        metadata={
                            'shippingType': product_data.get('shippingType'),
                            'taxFree': product_data.get('taxFree'),
                            'adultOnly': product_data.get('adultOnly'),
                            'returnable': product_data.get('returnable')
                        }
                    )
                    
                    yield product
                    collected_count += 1
                    
                    if max_products and collected_count >= max_products:
                        return
                        
                # 다음 페이지 확인
                if not page_info.get('hasNextPage'):
                    break
                    
                cursor = page_info.get('endCursor')
                
            except Exception as e:
                logger.error(f"상품 수집 중 오류: {e}")
                break
                
    async def _ensure_authenticated(self):
        """인증 상태 확인 및 갱신"""
        if not self.token or (self.token_expires_at and datetime.now(timezone.utc).timestamp() >= self.token_expires_at):
            await self.authenticate()
            
    async def _graphql_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """GraphQL 요청"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'errors' in data:
                        raise Exception(f"GraphQL 오류: {data['errors']}")
                        
                    return data
                else:
                    raise Exception(f"API 요청 실패: {response.status}")
                    
    def _parse_options(self, options_data: List[Dict]) -> List[Dict]:
        """옵션 정보 파싱"""
        options = []
        
        for opt in options_data:
            option = {
                'name': ' / '.join(
                    f"{attr['name']}: {attr['value']}" 
                    for attr in opt.get('optionAttributes', [])
                ),
                'price': opt.get('price', 0),
                'stock': opt.get('quantity', 0),
                'option_id': opt.get('id')
            }
            options.append(option)
            
        return options
    
    async def get_product_detail(self, product_id: str) -> Optional[ProductData]:
        """상품 상세 정보 조회"""
        await self._ensure_authenticated()
        
        query = """
        query GetItem($key: String!) {
            item(key: $key) {
                key
                name
                model
                price
                status
                category {
                    id
                    name
                }
                options {
                    id
                    price
                    quantity
                    optionAttributes {
                        name
                        value
                    }
                }
                images
                shippingFee
                shippingType
                taxFree
                adultOnly
                returnable
                createdAt
                updatedAt
            }
        }
        """
        
        try:
            result = await self._graphql_request(query, {'key': product_id})
            product_data = result.get('data', {}).get('item')
            
            if not product_data:
                return None
                
            return ProductData(
                wholesaler_type=self.wholesaler_type,
                wholesaler_product_id=product_data.get('key'),
                name=product_data.get('name', ''),
                wholesale_price=product_data.get('price', 0),
                retail_price=int(product_data.get('price', 0) * 1.5),
                stock_quantity=sum(
                    opt.get('quantity', 0) for opt in product_data.get('options', [])
                ),
                minimum_order_quantity=1,
                description='',
                main_image_url=product_data.get('images', [''])[0] if product_data.get('images') else '',
                additional_images=product_data.get('images', [])[1:] if len(product_data.get('images', [])) > 1 else [],
                category_path=product_data.get('category', {}).get('name', ''),
                brand=product_data.get('brand', ''),
                model_name=product_data.get('model', ''),
                shipping_fee=product_data.get('shippingFee', 0),
                is_active=product_data.get('status') == 'available',
                options=self._parse_options(product_data.get('options', [])),
                metadata={
                    'shippingType': product_data.get('shippingType'),
                    'taxFree': product_data.get('taxFree'),
                    'adultOnly': product_data.get('adultOnly'),
                    'returnable': product_data.get('returnable')
                }
            )
            
        except Exception as e:
            logger.error(f"상품 상세 조회 오류: {e}")
            return None
    
    async def get_stock_info(self, product_ids: List[str]) -> Dict[str, Dict[str, any]]:
        """재고 정보 조회"""
        await self._ensure_authenticated()
        
        query = """
        query GetItems($keys: [String!]!) {
            items(keys: $keys) {
                key
                status
                options {
                    id
                    quantity
                    optionAttributes {
                        name
                        value
                    }
                }
            }
        }
        """
        
        try:
            result = await self._graphql_request(query, {'keys': product_ids})
            items = result.get('data', {}).get('items', [])
            
            stock_info = {}
            for item in items:
                key = item.get('key')
                total_stock = sum(opt.get('quantity', 0) for opt in item.get('options', []))
                
                stock_info[key] = {
                    'in_stock': total_stock > 0 and item.get('status') == 'available',
                    'quantity': total_stock,
                    'status': item.get('status'),
                    'options': [
                        {
                            'option_id': opt.get('id'),
                            'name': ' / '.join(
                                f"{attr['name']}: {attr['value']}" 
                                for attr in opt.get('optionAttributes', [])
                            ),
                            'quantity': opt.get('quantity', 0)
                        }
                        for opt in item.get('options', [])
                    ]
                }
                
            return stock_info
            
        except Exception as e:
            logger.error(f"재고 정보 조회 오류: {e}")
            return {}