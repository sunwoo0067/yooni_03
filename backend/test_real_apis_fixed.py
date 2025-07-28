#!/usr/bin/env python3
"""
실제 API 문서 기반 도매처 API 테스트
"""

import os
import sys
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


class OwnerClanRealAPI:
    """실제 오너클랜 API (문서 기반)"""
    
    def __init__(self):
        self.username = os.getenv('OWNERCLAN_USERNAME')
        self.password = os.getenv('OWNERCLAN_PASSWORD')
        # Production URL 사용
        self.auth_url = 'https://auth.ownerclan.com/auth'
        self.api_url = 'https://api.ownerclan.com/v1/graphql'
        self.token = None
        
    def authenticate(self):
        """JWT 토큰 발급"""
        print("\n[오너클랜] 인증 시도...")
        
        auth_data = {
            "service": "ownerclan",
            "userType": "seller",
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(self.auth_url, json=auth_data, timeout=30)
            print(f"Auth Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                expires_in = data.get('expiresIn', 3600)
                print(f"[OK] 토큰 발급 성공 (유효시간: {expires_in}초)")
                return True
            else:
                print(f"[NO] 인증 실패: {response.status_code}")
                print(f"Response: {response.text}")
                
                # Sandbox로 재시도
                print("\n[오너클랜] Sandbox URL로 재시도...")
                self.auth_url = 'https://auth-sandbox.ownerclan.com/auth'
                self.api_url = 'https://api-sandbox.ownerclan.com/v1/graphql'
                
                response = requests.post(self.auth_url, json=auth_data, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get('token')
                    print("[OK] Sandbox 인증 성공")
                    return True
                    
                return False
                
        except Exception as e:
            print(f"[NO] 인증 오류: {e}")
            return False
            
    def get_products(self, limit=5):
        """상품 목록 조회"""
        if not self.token:
            print("[NO] 토큰이 없습니다")
            return []
            
        print(f"\n[오너클랜] 상품 {limit}개 조회...")
        
        query = """
        query GetAllItems($first: Int) {
            allItems(first: $first) {
                edges {
                    node {
                        key
                        name
                        price
                        status
                        category {
                            name
                        }
                        options {
                            price
                            quantity
                        }
                    }
                }
            }
        }
        """
        
        try:
            response = requests.post(
                self.api_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.token}'
                },
                json={
                    'query': query,
                    'variables': {'first': limit}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    print(f"[NO] GraphQL 오류: {data['errors']}")
                    return []
                    
                products = []
                edges = data.get('data', {}).get('allItems', {}).get('edges', [])
                
                for edge in edges:
                    product = edge.get('node', {})
                    products.append({
                        'id': product.get('key'),
                        'name': product.get('name'),
                        'price': product.get('price'),
                        'status': product.get('status'),
                        'category': product.get('category', {}).get('name', ''),
                        'stock': sum(opt.get('quantity', 0) for opt in product.get('options', []))
                    })
                    
                print(f"[OK] {len(products)}개 상품 조회 성공")
                return products
            else:
                print(f"[NO] API 호출 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[NO] 상품 조회 오류: {e}")
            return []


class DomeggookRealAPI:
    """실제 도매꾹 API (문서 기반)"""
    
    def __init__(self):
        self.api_key = os.getenv('DOMEGGOOK_API_KEY')
        self.base_url = 'https://openapi.domeggook.com'
        
    def get_categories(self):
        """카테고리 목록 조회"""
        print("\n[도매꾹] 카테고리 목록 조회...")
        
        url = f"{self.base_url}/api/category/list"
        params = {
            'version': '1.0',
            'api_key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 'error':
                    print(f"[NO] API 오류: {data.get('message')}")
                    return []
                    
                categories = data.get('data', [])
                print(f"[OK] {len(categories)}개 카테고리 조회 성공")
                return categories
            else:
                print(f"[NO] 카테고리 조회 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[NO] 카테고리 조회 오류: {e}")
            return []
            
    def get_products(self, category_code=None, limit=5):
        """상품 목록 조회"""
        print(f"\n[도매꾹] 상품 {limit}개 조회...")
        
        url = f"{self.base_url}/api/product/list"
        params = {
            'version': '4.1',
            'api_key': self.api_key,
            'page': 1,
            'limit': limit
        }
        
        if category_code:
            params['category_code'] = category_code
            
        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 'error':
                    print(f"[NO] API 오류: {data.get('message')}")
                    return []
                    
                products = []
                items = data.get('data', {}).get('items', [])
                
                for item in items:
                    products.append({
                        'id': item.get('product_id'),
                        'name': item.get('product_name'),
                        'price': item.get('dom_price', 0),
                        'category': item.get('category_name', ''),
                        'stock': item.get('stock_quantity', 0)
                    })
                    
                print(f"[OK] {len(products)}개 상품 조회 성공")
                return products
            else:
                print(f"[NO] 상품 조회 실패: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
                
        except Exception as e:
            print(f"[NO] 상품 조회 오류: {e}")
            return []


class ZentradeRealAPI:
    """실제 젠트레이드 API (문서 기반)"""
    
    def __init__(self):
        self.api_id = os.getenv('ZENTRADE_API_KEY')  # 실제로는 ID
        self.api_key = os.getenv('ZENTRADE_API_SECRET')  # 실제로는 m_skey
        self.base_url = 'https://www.zentrade.co.kr/shop/proc'
        
    def get_products(self, limit=None):
        """상품 목록 조회 (XML)"""
        print("\n[젠트레이드] 상품 목록 조회...")
        
        url = f"{self.base_url}/product_api.php"
        params = {
            'id': self.api_id,
            'm_skey': self.api_key,
            'runout': '0'  # 정상 상품만
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                # XML 파싱
                try:
                    # EUC-KR 인코딩 처리
                    content = response.content.decode('euc-kr')
                    root = ET.fromstring(content)
                    
                    products = []
                    product_elements = root.findall('product')
                    
                    for product in product_elements[:limit] if limit else product_elements:
                        code = product.get('code')
                        name_elem = product.find('prdtname')
                        price_elem = product.find('price')
                        status_elem = product.find('status')
                        
                        products.append({
                            'id': code,
                            'name': name_elem.text.strip() if name_elem is not None else '',
                            'price': int(price_elem.get('buyprice', 0)) if price_elem is not None else 0,
                            'runout': status_elem.get('runout', '0') if status_elem is not None else '0'
                        })
                        
                    print(f"[OK] {len(products)}개 상품 조회 성공")
                    return products
                    
                except ET.ParseError as e:
                    print(f"[NO] XML 파싱 오류: {e}")
                    print(f"Response content: {response.text[:500]}")
                    return []
                except UnicodeDecodeError as e:
                    print(f"[NO] 인코딩 오류: {e}")
                    # UTF-8로 재시도
                    try:
                        content = response.content.decode('utf-8')
                        print(f"UTF-8 Response: {content[:500]}")
                    except:
                        print(f"Raw Response: {response.content[:500]}")
                    return []
            else:
                print(f"[NO] API 호출 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[NO] 상품 조회 오류: {e}")
            return []


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("실제 API 문서 기반 도매처 테스트")
    print("=" * 60)
    print(f"실행 시간: {datetime.now()}")
    
    results = {}
    
    # 1. 오너클랜 테스트
    print("\n[1] 오너클랜 API 테스트")
    print("-" * 40)
    
    ownerclan_api = OwnerClanRealAPI()
    if ownerclan_api.authenticate():
        products = ownerclan_api.get_products(limit=3)
        results['ownerclan'] = {
            'status': 'success',
            'products': products
        }
        
        if products:
            print("\n수집된 상품:")
            for p in products[:3]:
                print(f"  - {p['name'][:50]}... ({p['price']}원)")
    else:
        results['ownerclan'] = {
            'status': 'failed',
            'error': 'Authentication failed'
        }
    
    # 2. 도매꾹 테스트
    print("\n[2] 도매꾹 API 테스트")
    print("-" * 40)
    
    domeggook_api = DomeggookRealAPI()
    
    # 카테고리 먼저 조회
    categories = domeggook_api.get_categories()
    if categories:
        # 첫 번째 카테고리로 상품 조회
        first_category = categories[0].get('category_code') if categories else None
        products = domeggook_api.get_products(category_code=first_category, limit=3)
        
        results['domeggook'] = {
            'status': 'success',
            'categories': len(categories),
            'products': products
        }
        
        if products:
            print("\n수집된 상품:")
            for p in products[:3]:
                print(f"  - {p['name'][:50]}... ({p['price']}원)")
    else:
        # 카테고리 없이 시도
        products = domeggook_api.get_products(limit=3)
        results['domeggook'] = {
            'status': 'partial',
            'categories': 0,
            'products': products
        }
    
    # 3. 젠트레이드 테스트
    print("\n[3] 젠트레이드 API 테스트")
    print("-" * 40)
    
    zentrade_api = ZentradeRealAPI()
    products = zentrade_api.get_products(limit=3)
    
    results['zentrade'] = {
        'status': 'success' if products else 'failed',
        'products': products
    }
    
    if products:
        print("\n수집된 상품:")
        for p in products[:3]:
            print(f"  - {p['name'][:50]}... ({p['price']}원)")
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for wholesaler, result in results.items():
        status = result['status']
        product_count = len(result.get('products', []))
        print(f"{wholesaler}: {status} ({product_count}개 상품)")
    
    # 결과 저장
    filename = f'real_api_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 파일: {filename}")


if __name__ == "__main__":
    main()