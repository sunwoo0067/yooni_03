#!/usr/bin/env python3
"""
도매꾹 실제 API 테스트
"""

import os
import sys
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()


class DomeggookAPI:
    """도매꾹 실제 API 클라이언트"""
    
    def __init__(self):
        self.api_key = os.getenv('DOMEGGOOK_API_KEY')
        self.base_url = 'https://domeggook.com/ssl/api/'
        self.version = '4.3'  # API 버전
        
    def get_categories(self):
        """카테고리 목록 조회"""
        print("\n[도매꾹] 카테고리 목록 조회...")
        
        params = {
            'ver': self.version,
            'mode': 'getCategoryList',
            'aid': self.api_key,
            'om': 'json'  # JSON 형식으로 요청
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                # JSON 파싱 시도
                try:
                    data = response.json()
                    print(f"✓ 카테고리 조회 성공")
                    return data
                except json.JSONDecodeError:
                    # XML 응답일 수 있음
                    print(f"Response content: {response.text[:500]}")
                    return None
            else:
                print(f"✗ API 호출 실패: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"✗ 오류 발생: {e}")
            return None
            
    def get_products(self, keyword=None, category=None, page=1, size=10):
        """상품 목록 조회"""
        print(f"\n[도매꾹] 상품 목록 조회 (페이지: {page}, 크기: {size})...")
        
        params = {
            'ver': self.version,
            'mode': 'getItemList',
            'aid': self.api_key,
            'om': 'json',
            'sz': size,
            'pg': page,
            'market': 'dome'  # dome 또는 supply
        }
        
        if keyword:
            params['kw'] = keyword
        if category:
            params['ca'] = category
            
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✓ 상품 목록 조회 성공")
                    return data
                except json.JSONDecodeError:
                    print(f"Response content: {response.text[:500]}")
                    return None
            else:
                print(f"✗ API 호출 실패: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"✗ 오류 발생: {e}")
            return None
            
    def get_product_detail(self, product_no):
        """상품 상세 정보 조회"""
        print(f"\n[도매꾹] 상품 상세 조회 (상품번호: {product_no})...")
        
        params = {
            'ver': self.version,
            'mode': 'getItemView',
            'aid': self.api_key,
            'no': product_no,
            'om': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✓ 상품 상세 조회 성공")
                    return data
                except json.JSONDecodeError:
                    print(f"Response content: {response.text[:500]}")
                    return None
            else:
                print(f"✗ API 호출 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"✗ 오류 발생: {e}")
            return None


def test_api_versions():
    """다양한 API 버전 테스트"""
    print("\n" + "=" * 60)
    print("도매꾹 API 버전 테스트")
    print("=" * 60)
    
    api_key = os.getenv('DOMEGGOOK_API_KEY')
    base_url = 'https://domeggook.com/ssl/api/'
    
    # 다양한 버전 시도
    versions = ['1.0', '2.0', '3.0', '4.0', '4.1', '4.3', '4.5', '5.0']
    
    for version in versions:
        print(f"\n[버전 {version} 테스트]")
        params = {
            'ver': version,
            'mode': 'getCategoryList',
            'aid': api_key,
            'om': 'json'
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=5)
            if response.status_code == 200:
                print(f"✓ 버전 {version} 작동함")
                # 응답 타입 확인
                if response.headers.get('content-type', '').startswith('application/json'):
                    print("  응답 타입: JSON")
                else:
                    print(f"  응답 타입: {response.headers.get('content-type')}")
                return version
            else:
                print(f"✗ 버전 {version} 실패 ({response.status_code})")
        except Exception as e:
            print(f"✗ 버전 {version} 오류: {e}")
            
    return None


def main():
    """메인 테스트 함수"""
    print("도매꾹 실제 API 테스트")
    print(f"실행 시간: {datetime.now()}")
    print(f"API Key: {os.getenv('DOMEGGOOK_API_KEY')}")
    
    # 1. API 버전 확인
    working_version = test_api_versions()
    
    if not working_version:
        print("\n작동하는 API 버전을 찾을 수 없습니다.")
        return
        
    print(f"\n작동하는 버전: {working_version}")
    
    # 2. API 클라이언트 생성
    api = DomeggookAPI()
    api.version = working_version
    
    # 3. 카테고리 조회
    categories = api.get_categories()
    if categories:
        print(f"\n카테고리 응답:")
        print(json.dumps(categories, ensure_ascii=False, indent=2)[:1000])
    
    # 4. 상품 목록 조회
    products = api.get_products(size=5)
    if products:
        print(f"\n상품 목록 응답:")
        print(json.dumps(products, ensure_ascii=False, indent=2)[:1000])
        
        # 5. 첫 번째 상품의 상세 정보 조회
        if isinstance(products, dict) and 'item' in products:
            items = products.get('item', [])
            if items and len(items) > 0:
                first_item = items[0]
                product_no = first_item.get('no')
                if product_no:
                    detail = api.get_product_detail(product_no)
                    if detail:
                        print(f"\n상품 상세 응답:")
                        print(json.dumps(detail, ensure_ascii=False, indent=2)[:1000])


if __name__ == "__main__":
    main()