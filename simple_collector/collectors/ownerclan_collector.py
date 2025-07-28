import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, AsyncGenerator, Set
from datetime import datetime, timedelta
from collections import deque

from .base_collector import BaseCollector, ProductData
from config.settings import settings

class OwnerClanCollector(BaseCollector):
    """오너클랜 2단계 수집기 - 740만개 상품 중 캐시 기반 수집"""
    
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
        
    @property
    def base_url(self) -> str:
        return self.credentials.get('api_url', 'https://api-sandbox.ownerclan.com/v1/graphql')
        
    @property
    def auth_url(self) -> str:
        return self.credentials.get('auth_url', 'https://auth-sandbox.ownerclan.com/auth')
        
    def _get_headers(self) -> Dict[str, str]:
        """HTTP 헤더"""
        headers = {
            'User-Agent': 'SimpleCollector-OwnerClan/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if self._jwt_token:
            headers['Authorization'] = f'Bearer {self._jwt_token}'
            
        return headers
        
    async def _get_jwt_token(self) -> bool:
        """JWT 토큰 발급"""
        try:
            # 기존 토큰이 유효하면 재사용
            if self._jwt_token and self._token_expires_at and datetime.now() < self._token_expires_at:
                return True
                
            auth_data = {
                'username': self.credentials.get('username'),
                'password': self.credentials.get('password')
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.auth_url,
                    json=auth_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        token_data = await response.json()
                        self._jwt_token = token_data.get('access_token')
                        
                        # 토큰 만료 시간 설정 (보통 1시간, 안전하게 50분으로 설정)
                        self._token_expires_at = datetime.now() + timedelta(minutes=50)
                        
                        self.logger.info("오너클랜 JWT 토큰 발급 완료")
                        return True
                    else:
                        self.logger.error(f"JWT 토큰 발급 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"JWT 토큰 발급 중 오류: {e}")
            return False
            
    async def authenticate(self) -> bool:
        """API 인증"""
        return await self._get_jwt_token()
        
    async def collect_products(self, incremental: bool = False) -> AsyncGenerator[ProductData, None]:
        """2단계 상품 수집"""
        
        # 1단계: 상품 코드 수집
        await self._stage1_collect_codes()
        
        if not self._cached_codes:
            self.logger.warning("수집된 상품 코드가 없습니다")
            return
            
        # 2단계: 상세 정보 수집
        async for product in self._stage2_collect_details():
            yield product
            
    async def _stage1_collect_codes(self):
        """1단계: 상품 코드 수집 (5,000개까지 캐시)"""
        self.logger.info(f"오너클랜 1단계 시작: 상품 코드 수집 (목표: {settings.OWNERCLAN_CACHE_SIZE}개)")
        
        page = 1
        page_size = 100
        collected_count = 0
        
        # GraphQL 쿼리 - 상품 코드만 조회
        query = '''
        query GetProductCodes($page: Int!, $pageSize: Int!) {
            products(page: $page, pageSize: $pageSize) {
                nodes {
                    productCode
                    updatedAt
                }
                totalCount
                hasNextPage
            }
        }
        '''
        
        async with aiohttp.ClientSession() as session:
            while collected_count < settings.OWNERCLAN_CACHE_SIZE:
                try:
                    # JWT 토큰 확인
                    if not await self._get_jwt_token():
                        break
                        
                    # GraphQL 요청
                    request_data = {
                        'query': query,
                        'variables': {
                            'page': page,
                            'pageSize': page_size
                        }
                    }
                    
                    async with session.post(
                        self.base_url,
                        json=request_data,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        
                        if response.status != 200:
                            self.logger.error(f"1단계 API 요청 실패: HTTP {response.status}")
                            break
                            
                        result = await response.json()
                        
                        if 'errors' in result:
                            self.logger.error(f"GraphQL 오류: {result['errors']}")
                            break
                            
                        products = result.get('data', {}).get('products', {})
                        nodes = products.get('nodes', [])
                        
                        if not nodes:
                            self.logger.info("더 이상 수집할 상품 코드가 없습니다")
                            break
                            
                        # 상품 코드 캐시에 저장
                        for product in nodes:
                            product_code = product.get('productCode')
                            if product_code and product_code not in self._cached_codes:
                                self._product_code_cache.append({
                                    'code': product_code,
                                    'updated_at': product.get('updatedAt')
                                })
                                self._cached_codes.add(product_code)
                                collected_count += 1
                                
                                if collected_count >= settings.OWNERCLAN_CACHE_SIZE:
                                    break
                                    
                        self.logger.info(f"1단계 진행: 페이지 {page}, 누적 {collected_count}개")
                        
                        # 다음 페이지로
                        page += 1
                        
                        # Rate Limiting (1분당 120회 제한)
                        await asyncio.sleep(0.5)  # 0.5초 대기
                        
                        # 더 이상 페이지가 없으면 종료
                        if not products.get('hasNextPage', False):
                            break
                            
                except Exception as e:
                    self.logger.error(f"1단계 수집 중 오류: {e}")
                    break
                    
        self.logger.info(f"오너클랜 1단계 완료: {len(self._cached_codes)}개 상품 코드 수집")
        
    async def _stage2_collect_details(self) -> AsyncGenerator[ProductData, None]:
        """2단계: 상세 정보 수집"""
        self.logger.info(f"오너클랜 2단계 시작: {len(self._cached_codes)}개 상품 상세 정보 수집")
        
        # GraphQL 쿼리 - 상품 상세 정보 조회
        query = '''
        query GetProductDetail($productCode: String!) {
            product(productCode: $productCode) {
                productCode
                productName
                brandName
                categoryName
                salePrice
                supplyPrice
                stockQuantity
                productStatus
                images {
                    imageUrl
                    imageType
                }
                options {
                    optionName
                    optionValue
                    additionalPrice
                }
                description
                specifications
                shippingInfo {
                    shippingFee
                    returnFee
                    exchangeFee
                }
                createdAt
                updatedAt
                productUrl
            }
        }
        '''
        
        batch_size = 5  # 동시 요청 수 제한
        semaphore = asyncio.Semaphore(batch_size)
        processed_count = 0
        
        async def process_product_code(session: aiohttp.ClientSession, product_info: Dict[str, Any]) -> Optional[ProductData]:
            async with semaphore:
                try:
                    # JWT 토큰 확인
                    if not await self._get_jwt_token():
                        return None
                        
                    request_data = {
                        'query': query,
                        'variables': {
                            'productCode': product_info['code']
                        }
                    }
                    
                    async with session.post(
                        self.base_url,
                        json=request_data,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        
                        if response.status != 200:
                            self.logger.warning(f"상품 {product_info['code']} 조회 실패: HTTP {response.status}")
                            return None
                            
                        result = await response.json()
                        
                        if 'errors' in result:
                            self.logger.warning(f"상품 {product_info['code']} GraphQL 오류: {result['errors']}")
                            return None
                            
                        product_data = result.get('data', {}).get('product')
                        if not product_data:
                            return None
                            
                        # 상품 정보 구성
                        product_info_json = {
                            'product_code': product_data.get('productCode'),
                            'product_name': product_data.get('productName'),
                            'brand_name': product_data.get('brandName'),
                            'category_name': product_data.get('categoryName'),
                            'sale_price': product_data.get('salePrice'),
                            'supply_price': product_data.get('supplyPrice'),
                            'stock_quantity': product_data.get('stockQuantity'),
                            'product_status': product_data.get('productStatus'),
                            'images': product_data.get('images', []),
                            'options': product_data.get('options', []),
                            'description': product_data.get('description'),
                            'specifications': product_data.get('specifications'),
                            'shipping_info': product_data.get('shippingInfo', {}),
                            'product_url': product_data.get('productUrl'),
                            'created_at': product_data.get('createdAt'),
                            'updated_at': product_data.get('updatedAt'),
                            'collected_at': datetime.now().isoformat(),
                            'supplier': 'ownerclan'
                        }
                        
                        return ProductData(
                            product_code=product_data.get('productCode'),
                            product_info=product_info_json,
                            supplier='ownerclan'
                        )
                        
                except Exception as e:
                    self.logger.error(f"상품 {product_info['code']} 처리 중 오류: {e}")
                    return None
                finally:
                    # Rate Limiting
                    await asyncio.sleep(0.5)
                    
        # 배치 처리
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for product_info in self._product_code_cache:
                task = process_product_code(session, product_info)
                tasks.append(task)
                
                # 배치 크기만큼 모이면 실행
                if len(tasks) >= batch_size:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, ProductData):
                            processed_count += 1
                            yield result
                            
                    tasks = []
                    
                    self.logger.info(f"2단계 진행: {processed_count}개 처리 완료")
                    
            # 남은 작업 처리
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, ProductData):
                        processed_count += 1
                        yield result
                        
        self.logger.info(f"오너클랜 2단계 완료: {processed_count}개 상품 상세 정보 수집")