"""
마켓플레이스 API 수집기 (v2 - 분리된 테이블 구조)
"""

import asyncio
import aiohttp
import hmac
import hashlib
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from ..config.settings import settings
from ..database.models_v2 import MarketplaceProduct, WholesaleProduct, ProductMapping
from ..database.models import ApiCredential
from ..database.connection import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text


class CoupangCollector:
    """쿠팡 오픈 API 수집기"""
    
    def __init__(self, access_key: str, secret_key: str, vendor_id: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.vendor_id = vendor_id
        self.base_url = "https://api-gateway.coupang.com"
        
    def _generate_hmac(self, method: str, url: str, query_string: str = "") -> Dict[str, str]:
        """HMAC 인증 헤더 생성"""
        datetime_now = time.strftime('%y%m%d')
        datetime_str = time.strftime('%Y-%m-%dT%H:%M:%S')
        
        path = url.replace(self.base_url, "")
        message = f"{datetime_now}{method}{path}{query_string}"
        
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "Authorization": f"CEA algorithm=HmacSHA256, access-key={self.access_key}, signed-date={datetime_str}, signature={signature}",
            "Content-Type": "application/json;charset=UTF-8"
        }
        
    async def get_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        """쿠팡 상품 목록 조회"""
        products = []
        next_token = None
        
        async with aiohttp.ClientSession() as session:
            while len(products) < limit:
                url = f"{self.base_url}/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
                
                params = {
                    "vendorId": self.vendor_id,
                    "status": "APPROVED",
                    "limit": min(50, limit - len(products))
                }
                if next_token:
                    params["nextToken"] = next_token
                    
                query_string = urlencode(params)
                full_url = f"{url}?{query_string}"
                
                headers = self._generate_hmac("GET", url, query_string)
                
                try:
                    async with session.get(full_url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for item in data.get("data", []):
                                product = {
                                    "marketplace_product_id": f"coupang_{item['sellerProductId']}",
                                    "marketplace": "coupang",
                                    "product_name": item["productName"],
                                    "selling_price": item["salePrice"],
                                    "listing_info": item,
                                    "status": item["status"].lower() if item["status"] else "active",
                                    "stock_quantity": item.get("stockQuantity", 0),
                                    "marketplace_category": item.get("categoryName", ""),
                                    "marketplace_url": f"https://www.coupang.com/vp/products/{item['productId']}",
                                    "coupang_product_id": item["productId"],
                                    "seller_product_id": item["sellerProductId"]
                                }
                                products.append(product)
                                
                            next_token = data.get("nextToken")
                            if not next_token:
                                break
                                
                        else:
                            print(f"쿠팡 API 오류: {response.status}")
                            break
                            
                except Exception as e:
                    print(f"쿠팡 수집 오류: {e}")
                    break
                    
        return products


class NaverCollector:
    """네이버 스마트스토어 API 수집기"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.commerce.naver.com"
        self.token = None
        
    async def _get_token(self) -> str:
        """OAuth 토큰 획득"""
        if self.token:
            return self.token
            
        url = "https://api.commerce.naver.com/external/v1/oauth2/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result["access_token"]
                    return self.token
                else:
                    raise Exception(f"네이버 토큰 획득 실패: {response.status}")
                    
    async def get_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        """네이버 상품 목록 조회"""
        products = []
        token = await self._get_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            page = 1
            while len(products) < limit:
                url = f"{self.base_url}/external/v2/products"
                
                params = {
                    "page": page,
                    "size": min(100, limit - len(products))
                }
                
                try:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for item in data.get("contents", []):
                                product = {
                                    "marketplace_product_id": f"naver_{item['id']}",
                                    "marketplace": "naver",
                                    "product_name": item["name"],
                                    "selling_price": item["salePrice"],
                                    "listing_info": item,
                                    "status": "active" if item.get("statusType") == "SALE" else "paused",
                                    "stock_quantity": item.get("stockQuantity", 0),
                                    "marketplace_category": " > ".join([c["name"] for c in item.get("category", {}).get("wholeCategoryName", [])]),
                                    "marketplace_url": f"https://smartstore.naver.com/products/{item['id']}",
                                    "naver_product_id": item["id"]
                                }
                                products.append(product)
                                
                            if len(data.get("contents", [])) == 0:
                                break
                            page += 1
                            
                        else:
                            print(f"네이버 API 오류: {response.status}")
                            break
                            
                except Exception as e:
                    print(f"네이버 수집 오류: {e}")
                    break
                    
        return products


class ElevenStreetCollector:
    """11번가 오픈 API 수집기"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.11st.co.kr/rest"
        
    async def get_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        """11번가 상품 목록 조회"""
        products = []
        
        headers = {
            "openapikey": self.api_key,
            "Content-Type": "application/xml"
        }
        
        async with aiohttp.ClientSession() as session:
            page = 1
            while len(products) < limit:
                url = f"{self.base_url}/prodmarketservice/prodmarket"
                
                xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
                <ProductSearchRequest>
                    <page>{page}</page>
                    <pageSize>{min(100, limit - len(products))}</pageSize>
                </ProductSearchRequest>"""
                
                try:
                    async with session.post(url, headers=headers, data=xml_data) as response:
                        if response.status == 200:
                            xml_content = await response.text()
                            root = ET.fromstring(xml_content)
                            
                            for product_elem in root.findall(".//product"):
                                product = {
                                    "marketplace_product_id": f"11st_{product_elem.findtext('productCode')}",
                                    "marketplace": "11st",
                                    "product_name": product_elem.findtext("productName"),
                                    "selling_price": int(product_elem.findtext("sellingPrice", "0")),
                                    "listing_info": {
                                        "productCode": product_elem.findtext("productCode"),
                                        "productName": product_elem.findtext("productName"),
                                        "sellingPrice": product_elem.findtext("sellingPrice"),
                                        "productPrice": product_elem.findtext("productPrice"),
                                        "stockQuantity": product_elem.findtext("stockQuantity")
                                    },
                                    "status": "active" if product_elem.findtext("productStatusType") == "Y" else "paused",
                                    "stock_quantity": int(product_elem.findtext("stockQuantity", "0")),
                                    "marketplace_category": product_elem.findtext("categoryName", ""),
                                    "marketplace_url": f"https://www.11st.co.kr/products/{product_elem.findtext('productCode')}",
                                    "eleven_product_code": product_elem.findtext("productCode")
                                }
                                products.append(product)
                                
                            total_count = int(root.findtext(".//totalCount", "0"))
                            if page * 100 >= total_count:
                                break
                            page += 1
                            
                        else:
                            print(f"11번가 API 오류: {response.status}")
                            break
                            
                except Exception as e:
                    print(f"11번가 수집 오류: {e}")
                    break
                    
        return products


class MarketplaceCollectorV2:
    """통합 마켓플레이스 수집기 (v2)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.collectors = {}
        self._initialize_collectors()
        
    def _initialize_collectors(self):
        """API 크레덴셜 로드 및 수집기 초기화"""
        # 쿠팡 크레덴셜
        coupang_cred = self.db.query(ApiCredential).filter(
            ApiCredential.supplier_code == "coupang"
        ).first()
        if coupang_cred and coupang_cred.api_config:
            self.collectors["coupang"] = CoupangCollector(
                access_key=coupang_cred.api_config.get("access_key"),
                secret_key=coupang_cred.api_config.get("secret_key"),
                vendor_id=coupang_cred.api_config.get("vendor_id")
            )
            
        # 네이버 크레덴셜
        naver_cred = self.db.query(ApiCredential).filter(
            ApiCredential.supplier_code == "naver"
        ).first()
        if naver_cred and naver_cred.api_config:
            self.collectors["naver"] = NaverCollector(
                client_id=naver_cred.api_config.get("client_id"),
                client_secret=naver_cred.api_config.get("client_secret")
            )
            
        # 11번가 크레덴셜
        eleven_cred = self.db.query(ApiCredential).filter(
            ApiCredential.supplier_code == "11st"
        ).first()
        if eleven_cred and eleven_cred.api_config:
            self.collectors["11st"] = ElevenStreetCollector(
                api_key=eleven_cred.api_config.get("api_key")
            )
            
    async def collect_all(self, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """모든 마켓플레이스에서 상품 수집"""
        results = {}
        
        for marketplace, collector in self.collectors.items():
            try:
                print(f"{marketplace} 수집 시작...")
                products = await collector.get_products(limit)
                results[marketplace] = products
                print(f"{marketplace} 수집 완료: {len(products)}개")
                
                # DB에 저장
                self._save_products(products)
                
            except Exception as e:
                print(f"{marketplace} 수집 실패: {e}")
                results[marketplace] = []
                
        return results
        
    def _save_products(self, products: List[Dict[str, Any]]):
        """수집된 마켓플레이스 상품을 DB에 저장"""
        for product_data in products:
            try:
                # 기존 상품 확인
                existing = self.db.query(MarketplaceProduct).filter(
                    MarketplaceProduct.marketplace_product_id == product_data["marketplace_product_id"]
                ).first()
                
                if existing:
                    # 업데이트
                    for key, value in product_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.now()
                    existing.last_synced_at = datetime.now()
                else:
                    # 신규 생성
                    new_product = MarketplaceProduct(**product_data)
                    new_product.created_at = datetime.now()
                    new_product.updated_at = datetime.now()
                    new_product.last_synced_at = datetime.now()
                    self.db.add(new_product)
                    
                self.db.commit()
                
            except Exception as e:
                print(f"상품 저장 오류 ({product_data.get('marketplace_product_id')}): {e}")
                self.db.rollback()
                
    async def match_with_wholesale(self, marketplace_product_id: str, wholesale_product_code: str, confidence: float = 1.0):
        """마켓플레이스 상품과 도매 상품 매핑"""
        try:
            # 마켓플레이스 상품 확인
            mp_product = self.db.query(MarketplaceProduct).filter(
                MarketplaceProduct.marketplace_product_id == marketplace_product_id
            ).first()
            
            if not mp_product:
                raise Exception("마켓플레이스 상품을 찾을 수 없습니다")
                
            # 도매 상품 확인
            ws_product = self.db.query(WholesaleProduct).filter(
                WholesaleProduct.product_code == wholesale_product_code
            ).first()
            
            if not ws_product:
                raise Exception("도매 상품을 찾을 수 없습니다")
                
            # 매핑 업데이트
            mp_product.wholesale_product_code = wholesale_product_code
            
            # 매핑 이력 생성
            mapping = ProductMapping(
                wholesale_product_code=wholesale_product_code,
                marketplace=mp_product.marketplace,
                marketplace_product_id=marketplace_product_id,
                mapping_type='manual',
                confidence_score=confidence,
                created_at=datetime.now()
            )
            self.db.add(mapping)
            self.db.commit()
            
            return True
            
        except Exception as e:
            print(f"매핑 오류: {e}")
            self.db.rollback()
            return False