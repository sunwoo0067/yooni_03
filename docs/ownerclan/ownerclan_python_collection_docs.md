# 오너클랜 상품 수집 시스템 (Python)

## 개요
오너클랜 API를 활용한 효율적인 상품 수집 시스템입니다. 2단계 수집 프로세스를 통해 대용량 상품 데이터를 안정적으로 수집하고 저장할 수 있습니다.

## 시스템 아키텍처

### 2단계 수집 프로세스
1. **1단계**: 상품 코드 수집 및 캐시 메모리 저장
2. **2단계**: 상품 상세 정보 수집 및 데이터베이스 저장

### 핵심 특징
- 유연한 검색 조건 조합
- 메모리 기반 캐시 시스템
- 배치 처리를 통한 성능 최적화
- 에러 복구 및 재시도 메커니즘
- 진행률 모니터링

## 시스템 요구사항

### Python 버전
- Python 3.8 이상

### 필수 라이브러리
```bash
pip install requests
pip install asyncio
pip install aiohttp
pip install python-dotenv
pip install sqlalchemy  # DB 연동용
pip install psycopg2-binary  # PostgreSQL용
```

### 환경 설정
```bash
# .env 파일 생성
OWNERCLAN_API_URL=https://api-sandbox.ownerclan.com/v1/graphql
OWNERCLAN_AUTH_URL=https://auth-sandbox.ownerclan.com/auth
OWNERCLAN_USERNAME=your_username
OWNERCLAN_PASSWORD=your_password
DATABASE_URL=postgresql://user:password@localhost:5432/ownerclan_db
```

## 시스템 구조

### 1. 프로젝트 디렉토리 구조
```
ownerclan_collector/
├── main.py                 # 메인 실행 파일
├── config/
│   ├── __init__.py
│   ├── settings.py         # 설정 관리
│   └── database.py         # DB 연결 설정
├── collector/
│   ├── __init__.py
│   ├── auth.py            # 인증 관리
│   ├── api_client.py      # API 클라이언트
│   ├── product_collector.py  # 상품 수집 로직
│   └── cache_manager.py   # 캐시 관리
├── models/
│   ├── __init__.py
│   ├── product.py         # 상품 모델
│   └── database_models.py # DB 모델
├── utils/
│   ├── __init__.py
│   ├── logger.py          # 로깅 설정
│   └── helpers.py         # 유틸리티 함수
├── requirements.txt
└── .env
```

### 2. 설정 관리 (config/settings.py)
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API 설정
    API_URL = os.getenv('OWNERCLAN_API_URL')
    AUTH_URL = os.getenv('OWNERCLAN_AUTH_URL')
    USERNAME = os.getenv('OWNERCLAN_USERNAME')
    PASSWORD = os.getenv('OWNERCLAN_PASSWORD')
    
    # 수집 설정
    BATCH_SIZE = 1000           # 1단계 배치 크기
    DETAIL_BATCH_SIZE = 100     # 2단계 배치 크기
    REQUEST_DELAY = 0.1         # API 호출 간격 (초)
    RETRY_COUNT = 3             # 재시도 횟수
    TIMEOUT = 30                # 요청 타임아웃 (초)
    
    # 데이터베이스 설정
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # 로깅 설정
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'collector.log'
```

### 3. 인증 관리 (collector/auth.py)
```python
import requests
import time
from typing import Optional
from config.settings import Settings

class AuthManager:
    def __init__(self):
        self.token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        self.settings = Settings()
    
    async def get_token(self) -> str:
        """JWT 토큰 획득 또는 갱신"""
        if self.token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.token
        
        return await self._authenticate()
    
    async def _authenticate(self) -> str:
        """인증 수행"""
        auth_data = {
            "service": "ownerclan",
            "userType": "seller",
            "username": self.settings.USERNAME,
            "password": self.settings.PASSWORD
        }
        
        try:
            response = requests.post(
                self.settings.AUTH_URL,
                json=auth_data,
                timeout=self.settings.TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data['token']
            # 토큰 만료 시간 설정 (실제 응답에서 받은 expiresIn 사용)
            expires_in = data.get('expiresIn', 3600)  # 기본 1시간
            self.token_expires_at = time.time() + expires_in - 300  # 5분 여유
            
            return self.token
            
        except requests.RequestException as e:
            raise Exception(f"인증 실패: {e}")
```

### 4. API 클라이언트 (collector/api_client.py)
```python
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from collector.auth import AuthManager
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

class OwnerClanAPIClient:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.settings = Settings()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.TIMEOUT)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_graphql_request(self, query: str, variables: Dict = None) -> Dict:
        """GraphQL 요청 실행"""
        if not self.session:
            raise Exception("Session not initialized. Use async context manager.")
        
        token = await self.auth_manager.get_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        for attempt in range(self.settings.RETRY_COUNT):
            try:
                async with self.session.post(
                    self.settings.API_URL,
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if 'errors' in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        raise Exception(f"GraphQL error: {data['errors'][0]['message']}")
                    
                    return data
                    
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.settings.RETRY_COUNT - 1:
                    raise
                await asyncio.sleep(self.settings.REQUEST_DELAY * (attempt + 1))
    
    async def fetch_all_items(self, params: Dict) -> Optional[Dict]:
        """전체 상품 조회"""
        query = """
            query GetAllItems($after: String, $first: Int, $minPrice: Int, $maxPrice: Int, $search: String) {
                allItems(after: $after, first: $first, minPrice: $minPrice, maxPrice: $maxPrice, search: $search) {
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        startCursor
                        endCursor
                    }
                    edges {
                        cursor
                        node {
                            key
                        }
                    }
                }
            }
        """
        
        response = await self.make_graphql_request(query, params)
        return response.get('data', {}).get('allItems')
    
    async def fetch_item_histories(self, params: Dict) -> Optional[Dict]:
        """상품 변경 이력 조회"""
        query = """
            query GetItemHistories($after: String, $first: Int, $dateFrom: Int, $dateTo: Int) {
                itemHistories(after: $after, first: $first, dateFrom: $dateFrom, dateTo: $dateTo) {
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        startCursor
                        endCursor
                    }
                    edges {
                        cursor
                        node {
                            itemKey
                            timestamp
                            kind
                        }
                    }
                }
            }
        """
        
        response = await self.make_graphql_request(query, params)
        return response.get('data', {}).get('itemHistories')
    
    async def fetch_detailed_items(self, keys: List[str]) -> List[Dict]:
        """상품 상세 정보 조회"""
        query = """
            query GetItems($keys: [String!]!) {
                items(keys: $keys) {
                    createdAt
                    updatedAt
                    key
                    name
                    model
                    production
                    origin
                    price
                    category {
                        id
                        name
                        level
                    }
                    content
                    shippingFee
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
                    returnable
                    images
                }
            }
        """
        
        response = await self.make_graphql_request(query, {'keys': keys})
        return response.get('data', {}).get('items', [])
```

### 5. 캐시 관리 (collector/cache_manager.py)
```python
from typing import Set, List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class CacheManager:
    def __init__(self):
        self.product_keys: Set[str] = set()
        self.metadata: Dict[str, Any] = {}
    
    def add_product_key(self, key: str) -> bool:
        """상품 키 추가 (중복 제거)"""
        if key not in self.product_keys:
            self.product_keys.add(key)
            return True
        return False
    
    def add_product_keys(self, keys: List[str]) -> int:
        """상품 키 일괄 추가"""
        initial_size = len(self.product_keys)
        self.product_keys.update(keys)
        added_count = len(self.product_keys) - initial_size
        logger.info(f"캐시에 {added_count}개 새로운 상품 키 추가")
        return added_count
    
    def get_all_keys(self) -> List[str]:
        """모든 상품 키 반환"""
        return list(self.product_keys)
    
    def get_cache_size(self) -> int:
        """캐시 크기 반환"""
        return len(self.product_keys)
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self.product_keys.clear()
        self.metadata.clear()
        logger.info("캐시가 초기화되었습니다")
    
    def set_metadata(self, key: str, value: Any) -> None:
        """메타데이터 설정"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Any:
        """메타데이터 조회"""
        return self.metadata.get(key)
    
    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 정보"""
        return {
            'total_keys': len(self.product_keys),
            'metadata': self.metadata.copy()
        }
```

### 6. 상품 수집기 (collector/product_collector.py)
```python
import asyncio
import time
from typing import List, Dict, Any, Callable
from collector.api_client import OwnerClanAPIClient
from collector.cache_manager import CacheManager
from config.settings import Settings
from utils.logger import get_logger
from utils.helpers import chunk_list

logger = get_logger(__name__)

class ProductCollector:
    def __init__(self):
        self.settings = Settings()
        self.cache_manager = CacheManager()
    
    async def collect_product_keys(self, search_conditions: Dict) -> List[str]:
        """1단계: 상품 코드 수집"""
        logger.info("1단계: 상품 코드 수집 시작")
        
        async with OwnerClanAPIClient() as api_client:
            strategies = self._build_search_strategies(search_conditions)
            
            for strategy in strategies:
                logger.info(f"검색 전략 실행: {strategy['name']}")
                await self._execute_search_strategy(api_client, strategy)
                # API 호출 간격 조정
                await asyncio.sleep(self.settings.REQUEST_DELAY)
        
        total_keys = self.cache_manager.get_cache_size()
        logger.info(f"1단계 완료: 총 {total_keys}개 상품 코드 수집")
        
        return self.cache_manager.get_all_keys()
    
    def _build_search_strategies(self, conditions: Dict) -> List[Dict]:
        """검색 전략 구성"""
        strategies = []
        
        # 전체 조회
        if conditions.get('include_all', False):
            strategies.append({
                'name': '전체 상품 조회',
                'type': 'pagination',
                'params': {'first': self.settings.BATCH_SIZE}
            })
        
        # 가격 범위별 조회
        for i, price_range in enumerate(conditions.get('price_ranges', [])):
            strategies.append({
                'name': f'가격 범위 조회 {i + 1}',
                'type': 'price_range',
                'params': {
                    'first': self.settings.BATCH_SIZE,
                    'minPrice': price_range['min'],
                    'maxPrice': price_range['max']
                }
            })
        
        # 키워드별 조회
        for keyword in conditions.get('keywords', []):
            strategies.append({
                'name': f'키워드 검색: {keyword}',
                'type': 'keyword',
                'params': {
                    'first': self.settings.BATCH_SIZE,
                    'search': keyword
                }
            })
        
        # 조합 검색
        if conditions.get('combined_search', False):
            strategies.extend(self._build_combined_strategies(conditions))
        
        # 날짜 기반 조회
        for date_range in conditions.get('date_ranges', []):
            strategies.append({
                'name': f'날짜 범위 조회',
                'type': 'date_range',
                'params': {
                    'first': self.settings.BATCH_SIZE,
                    'dateFrom': date_range['from'],
                    'dateTo': date_range.get('to')
                }
            })
        
        return strategies
    
    def _build_combined_strategies(self, conditions: Dict) -> List[Dict]:
        """조합 검색 전략 구성"""
        combined_strategies = []
        keywords = conditions.get('keywords', [])
        price_ranges = conditions.get('price_ranges', [])
        
        for keyword in keywords:
            for i, price_range in enumerate(price_ranges):
                combined_strategies.append({
                    'name': f'조합 검색: {keyword} ({price_range["min"]}-{price_range["max"]})',
                    'type': 'combined',
                    'params': {
                        'first': self.settings.BATCH_SIZE,
                        'search': keyword,
                        'minPrice': price_range['min'],
                        'maxPrice': price_range['max']
                    }
                })
        
        return combined_strategies
    
    async def _execute_search_strategy(self, api_client: OwnerClanAPIClient, strategy: Dict):
        """검색 전략 실행"""
        has_next_page = True
        cursor = None
        page_count = 0
        
        while has_next_page:
            try:
                params = strategy['params'].copy()
                if cursor:
                    params['after'] = cursor
                
                if strategy['type'] == 'date_range':
                    result = await api_client.fetch_item_histories(params)
                    if result and result.get('edges'):
                        keys = [edge['node']['itemKey'] for edge in result['edges'] 
                               if edge['node'].get('itemKey')]
                else:
                    result = await api_client.fetch_all_items(params)
                    if result and result.get('edges'):
                        keys = [edge['node']['key'] for edge in result['edges'] 
                               if edge['node'].get('key')]
                
                if result and result.get('edges'):
                    added_count = self.cache_manager.add_product_keys(keys)
                    page_count += 1
                    
                    logger.info(f"{strategy['name']} - 페이지 {page_count}: "
                              f"{len(keys)}개 조회, {added_count}개 신규 추가, "
                              f"총 {self.cache_manager.get_cache_size()}개")
                    
                    has_next_page = result.get('pageInfo', {}).get('hasNextPage', False)
                    cursor = result.get('pageInfo', {}).get('endCursor')
                    
                    await asyncio.sleep(self.settings.REQUEST_DELAY)
                else:
                    has_next_page = False
                    
            except Exception as e:
                logger.error(f"전략 실행 실패 ({strategy['name']}): {e}")
                has_next_page = False
    
    async def collect_detailed_products(self, 
                                      product_keys: List[str], 
                                      save_callback: Callable) -> List[Dict]:
        """2단계: 상품 상세 정보 수집"""
        logger.info("2단계: 상품 상세 정보 수집 시작")
        
        total_keys = len(product_keys)
        batches = chunk_list(product_keys, self.settings.DETAIL_BATCH_SIZE)
        
        logger.info(f"총 {total_keys}개 상품을 {len(batches)}개 배치로 처리")
        
        processed_count = 0
        all_results = []
        
        async with OwnerClanAPIClient() as api_client:
            for i, batch in enumerate(batches):
                try:
                    logger.info(f"배치 {i + 1}/{len(batches)} 처리 중... ({len(batch)}개)")
                    
                    batch_results = await api_client.fetch_detailed_items(batch)
                    
                    if batch_results:
                        await save_callback(batch_results)
                        all_results.extend(batch_results)
                        processed_count += len(batch_results)
                    
                    progress = (processed_count / total_keys) * 100
                    logger.info(f"진행률: {processed_count}/{total_keys} ({progress:.1f}%)")
                    
                    await asyncio.sleep(self.settings.REQUEST_DELAY)
                    
                except Exception as e:
                    logger.error(f"배치 {i + 1} 처리 실패: {e}")
                    continue
        
        logger.info(f"2단계 완료: 총 {len(all_results)}개 상품 수집 완료")
        return all_results
```

### 7. 데이터베이스 모델 (models/database_models.py)
```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(Text, nullable=True)
    model = Column(String(255), nullable=True)
    production = Column(String(255), nullable=True)
    origin = Column(String(100), nullable=True)
    price = Column(Float, nullable=True)
    content = Column(Text, nullable=True)
    shipping_fee = Column(Integer, nullable=True)
    status = Column(String(50), nullable=True)
    tax_free = Column(Boolean, default=False)
    returnable = Column(Boolean, default=True)
    category_data = Column(JSON, nullable=True)
    options_data = Column(JSON, nullable=True)
    images_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ownerclan_created_at = Column(Integer, nullable=True)
    ownerclan_updated_at = Column(Integer, nullable=True)

class CollectionHistory(Base):
    __tablename__ = 'collection_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_type = Column(String(50), nullable=False)  # 'keys' or 'details'
    total_count = Column(Integer, nullable=False)
    success_count = Column(Integer, nullable=False)
    error_count = Column(Integer, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    search_conditions = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 8. 메인 실행 파일 (main.py)
```python
import asyncio
import time
from typing import List, Dict
from sqlalchemy.orm import sessionmaker
from config.database import engine, init_database
from models.database_models import Product, CollectionHistory
from collector.product_collector import ProductCollector
from utils.logger import get_logger

logger = get_logger(__name__)

class OwnerClanCollectionService:
    def __init__(self):
        self.collector = ProductCollector()
        self.Session = sessionmaker(bind=engine)
    
    async def save_products_to_database(self, products: List[Dict]) -> None:
        """상품 데이터를 데이터베이스에 저장"""
        session = self.Session()
        try:
            for product_data in products:
                # 기존 상품 확인
                existing_product = session.query(Product).filter_by(
                    key=product_data['key']
                ).first()
                
                if existing_product:
                    # 업데이트
                    self._update_product(existing_product, product_data)
                else:
                    # 신규 추가
                    new_product = self._create_product(product_data)
                    session.add(new_product)
            
            session.commit()
            logger.info(f"데이터베이스에 {len(products)}개 상품 저장 완료")
            
        except Exception as e:
            session.rollback()
            logger.error(f"데이터베이스 저장 실패: {e}")
            raise
        finally:
            session.close()
    
    def _create_product(self, data: Dict) -> Product:
        """상품 객체 생성"""
        return Product(
            key=data['key'],
            name=data.get('name'),
            model=data.get('model'),
            production=data.get('production'),
            origin=data.get('origin'),
            price=data.get('price'),
            content=data.get('content'),
            shipping_fee=data.get('shippingFee'),
            status=data.get('status'),
            tax_free=data.get('taxFree', False),
            returnable=data.get('returnable', True),
            category_data=data.get('category'),
            options_data=data.get('options'),
            images_data=data.get('images'),
            ownerclan_created_at=data.get('createdAt'),
            ownerclan_updated_at=data.get('updatedAt')
        )
    
    def _update_product(self, product: Product, data: Dict) -> None:
        """기존 상품 정보 업데이트"""
        product.name = data.get('name', product.name)
        product.model = data.get('model', product.model)
        product.production = data.get('production', product.production)
        product.origin = data.get('origin', product.origin)
        product.price = data.get('price', product.price)
        product.content = data.get('content', product.content)
        product.shipping_fee = data.get('shippingFee', product.shipping_fee)
        product.status = data.get('status', product.status)
        product.tax_free = data.get('taxFree', product.tax_free)
        product.returnable = data.get('returnable', product.returnable)
        product.category_data = data.get('category', product.category_data)
        product.options_data = data.get('options', product.options_data)
        product.images_data = data.get('images', product.images_data)
        product.ownerclan_updated_at = data.get('updatedAt', product.ownerclan_updated_at)
    
    def save_collection_history(self, collection_type: str, stats: Dict) -> None:
        """수집 이력 저장"""
        session = self.Session()
        try:
            history = CollectionHistory(
                collection_type=collection_type,
                total_count=stats['total_count'],
                success_count=stats['success_count'],
                error_count=stats['error_count'],
                duration_seconds=stats['duration_seconds'],
                search_conditions=stats.get('search_conditions')
            )
            session.add(history)
            session.commit()
            logger.info(f"수집 이력 저장 완료: {collection_type}")
        except Exception as e:
            session.rollback()
            logger.error(f"수집 이력 저장 실패: {e}")
        finally:
            session.close()
    
    async def run_full_collection(self, search_conditions: Dict) -> Dict:
        """전체 수집 프로세스 실행"""
        logger.info("오너클랜 상품 수집 프로세스 시작")
        
        start_time = time.time()
        total_stats = {
            'keys_collected': 0,
            'products_saved': 0,
            'errors': 0
        }
        
        try:
            # 1단계: 상품 코드 수집
            keys_start_time = time.time()
            product_keys = await self.collector.collect_product_keys(search_conditions)
            keys_duration = time.time() - keys_start_time
            
            total_stats['keys_collected'] = len(product_keys)
            
            # 1단계 이력 저장
            self.save_collection_history('keys', {
                'total_count': len(product_keys),
                'success_count': len(product_keys),
                'error_count': 0,
                'duration_seconds': keys_duration,
                'search_conditions': search_conditions
            })
            
            if not product_keys:
                logger.warning("수집된 상품 코드가 없습니다.")
                return total_stats
            
            # 2단계: 상품 상세 정보 수집
            details_start_time = time.time()
            detailed_products = await self.collector.collect_detailed_products(
                product_keys, 
                self.save_products_to_database
            )
            details_duration = time.time() - details_start_time
            
            total_stats['products_saved'] = len(detailed_products)
            
            # 2단계 이력 저장
            self.save_collection_history('details', {
                'total_count': len(product_keys),
                'success_count': len(detailed_products),
                'error_count': len(product_keys) - len(detailed_products),
                'duration_seconds': details_duration
            })
            
        except Exception as e:
            logger.error(f"수집 프로세스 실패: {e}")
            total_stats['errors'] += 1
            raise
        
        total_duration = time.time() - start_time
        logger.info(f"전체 수집 프로세스 완료 (소요시간: {total_duration:.2f}초)")
        logger.info(f"최종 결과: {total_stats}")
        
        return total_stats

async def main():
    """메인 실행 함수"""
    # 데이터베이스 초기화
    init_database()
    
    # 검색 조건 설정
    search_conditions = {
        'include_all': True,
        'keywords': ['스마트폰', '노트북', '태블릿'],
        'price_ranges': [
            {'min': 0, 'max': 50000},
            {'min': 50000, 'max': 200000},
            {'min': 200000, 'max': 1000000}
        ],
        'combined_search': True,
        'date_ranges': [
            {
                'from': int(time.time()) - (30 * 24 * 60 * 60),  # 30일 전
                'to': int(time.time())  # 현재
            }
        ]
    }
    
    # 수집 서비스 실행
    service = OwnerClanCollectionService()
    try:
        results = await service.run_full_collection(search_conditions)
        print(f"수집 완료: {results}")
    except Exception as e:
        logger.error(f"실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 사용 방법

### 1. 환경 설정
```bash
# 프로젝트 클론 및 설정
git clone <repository>
cd ownerclan_collector

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 실제 값 입력
```

### 2. 데이터베이스 설정
```python
# config/database.py
from sqlalchemy import create_engine
from models.database_models import Base
from config.settings import Settings

settings = Settings()
engine = create_engine(settings.DATABASE_URL)

def init_database():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)
```

### 3. 실행
```bash
# 기본 실행
python main.py

# 로그 레벨 조정하여 실행
LOG_LEVEL=DEBUG python main.py
```

### 4. 커스텀 실행 예제
```python
import asyncio
from main import OwnerClanCollectionService

async def custom_collection():
    service = OwnerClanCollectionService()
    
    # 특정 조건으로 수집
    conditions = {
        'keywords': ['iPhone', 'Samsung'],
        'price_ranges': [
            {'min': 500000, 'max': 1500000}
        ]
    }
    
    results = await service.run_full_collection(conditions)
    print(f"수집 결과: {results}")

# 실행
asyncio.run(custom_collection())
```

## 모니터링 및 로깅

### 로그 설정 (utils/logger.py)
```python
import logging
import os
from config.settings import Settings

def get_logger(name: str) -> logging.Logger:
    """로거 설정 및 반환"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 로그 레벨 설정
        logger.setLevel(getattr(logging, Settings.LOG_LEVEL))
        
        # 포매터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 파일 핸들러
        if Settings.LOG_FILE:
            file_handler = logging.FileHandler(Settings.LOG_FILE)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    return logger
```

### 진행률 모니터링
- 실시간 로그를 통한 진행률 확인
- 배치별 처리 상황 모니터링
- 에러 발생 시 자동 로깅 및 계속 진행

### 성능 최적화 팁
1. **배치 크기 조정**: 네트워크 상황에 맞게 `BATCH_SIZE`, `DETAIL_BATCH_SIZE` 조정
2. **요청 간격 조정**: `REQUEST_DELAY`를 통한 API 호출 속도 제어
3. **재시도 설정**: `RETRY_COUNT`로 일시적 오류 대응
4. **메모리 관리**: 대용량 수집 시 캐시 주기적 정리

이 시스템을 통해 안정적이고 효율적인 오너클랜 상품 데이터 수집이 가능합니다.