#!/usr/bin/env python3
"""
도매꾹 API v4.1 테스트 (실제 API URL 사용)
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


class DomeggookAPIv41:
    """도매꾹 API v4.1 클라이언트"""
    
    def __init__(self):
        self.api_key = os.getenv('DOMEGGOOK_API_KEY')
        self.base_url = 'https://domeggook.com/ssl/api/'
        self.version = '4.1'
        
    def get_categories(self):
        """카테고리 목록 조회 (v1.0 사용)"""
        print("\n[도매꾹] 카테고리 목록 조회...")
        
        params = {
            'ver': '1.0',  # 카테고리는 v1.0 사용
            'mode': 'getCategoryList',
            'aid': self.api_key,
            'om': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"✗ API 오류: {data['errors']['message']}")
                    return None
                    
                print("✓ 카테고리 조회 성공")
                return data
                
        except Exception as e:
            print(f"✗ 오류: {e}")
            return None
            
    def extract_categories(self, category_data):
        """카테고리 데이터에서 중분류 추출"""
        categories = []
        
        def extract_recursive(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        code = value.get('code', '')
                        name = value.get('name', '')
                        
                        # 중분류 패턴: XX_XX_00_00_00
                        if code.endswith('_00_00_00') and code.count('00') == 3:
                            categories.append({
                                'code': code,
                                'name': name,
                                'path': path + " > " + name if path else name
                            })
                            print(f"  - {code}: {name}")
                            
                        # 자식 카테고리 확인
                        if 'child' in value:
                            extract_recursive(value['child'], path + " > " + name if path else name)
                            
        if category_data and 'domeggook' in category_data:
            items = category_data['domeggook'].get('items', {})
            extract_recursive(items)
            
        return categories
        
    def get_products(self, category_code=None, page=1, size=100):
        """상품 목록 조회 (v4.1)"""
        print(f"\n[도매꾹] 상품 목록 조회 (카테고리: {category_code}, 페이지: {page})...")
        
        params = {
            'ver': self.version,
            'mode': 'getItemList',
            'aid': self.api_key,
            'om': 'json',
            'sz': size,
            'pg': page,
            'so': 'rd'  # 정렬: 랭킹순
        }
        
        if category_code:
            params['ca'] = category_code
            
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"✗ API 오류: {data['errors']['message']}")
                    return None
                    
                # 응답 구조 확인
                if 'header' in data and 'item' in data:
                    header = data['header']
                    items = data['item']
                    
                    print(f"✓ 상품 목록 조회 성공")
                    print(f"  총 상품 수: {header.get('ttl_cnt', 0)}")
                    print(f"  현재 페이지 상품 수: {len(items)}")
                    
                    return data
                else:
                    print("✗ 예상치 못한 응답 구조")
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                    return None
                    
        except Exception as e:
            print(f"✗ 오류: {e}")
            return None
            
    def get_product_detail(self, product_no):
        """상품 상세 정보 조회 (v4.5)"""
        print(f"\n[도매꾹] 상품 상세 조회 (상품번호: {product_no})...")
        
        params = {
            'ver': '4.5',  # 상세정보는 v4.5 사용
            'mode': 'getItemView',
            'aid': self.api_key,
            'no': product_no,
            'om': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"✗ API 오류: {data['errors']['message']}")
                    return None
                    
                print("✓ 상품 상세 조회 성공")
                return data
                
        except Exception as e:
            print(f"✗ 오류: {e}")
            return None


def main():
    """메인 테스트 함수"""
    print("도매꾹 API v4.1 테스트")
    print("=" * 80)
    print(f"실행 시간: {datetime.now()}")
    print(f"API Key: {os.getenv('DOMEGGOOK_API_KEY')}")
    print("=" * 80)
    
    # API 클라이언트 생성
    api = DomeggookAPIv41()
    
    # 1. 카테고리 조회
    print("\n[1단계] 카테고리 조회")
    print("-" * 60)
    
    categories_data = api.get_categories()
    if categories_data:
        # 응답 구조 확인
        print("\n응답 데이터 구조:")
        print(json.dumps(categories_data, ensure_ascii=False, indent=2)[:1000])
        
        print("\n중분류 카테고리 추출:")
        categories = api.extract_categories(categories_data)
        print(f"\n총 {len(categories)}개 중분류 카테고리")
        
        # 카테고리 저장
        with open('domeggook_categories.json', 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        print("카테고리 정보 저장: domeggook_categories.json")
    else:
        print("카테고리 조회 실패")
        return
        
    # 2. 상품 목록 조회 (첫 번째 카테고리 사용)
    if categories:
        print("\n[2단계] 상품 목록 조회")
        print("-" * 60)
        
        # 첫 번째 카테고리로 테스트
        test_category = categories[0]
        print(f"테스트 카테고리: {test_category['name']} ({test_category['code']})")
        
        products_data = api.get_products(category_code=test_category['code'], size=10)
        
        if products_data and 'item' in products_data:
            items = products_data['item']
            
            print(f"\n수집된 상품 ({len(items)}개):")
            for idx, item in enumerate(items[:5]):  # 처음 5개만 출력
                print(f"\n{idx + 1}. {item.get('tit', 'N/A')}")
                print(f"   가격: {item.get('prc', 0):,}원")
                print(f"   판매자: {item.get('mmb', 'N/A')}")
                print(f"   상품번호: {item.get('no', 'N/A')}")
                print(f"   배송비: {item.get('dlvPrc', 'N/A')}")
                
            # 상품 데이터 저장
            with open('domeggook_products_sample.json', 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print("\n상품 데이터 저장: domeggook_products_sample.json")
            
            # 3. 상품 상세 조회
            if items:
                print("\n[3단계] 상품 상세 조회")
                print("-" * 60)
                
                first_item_no = items[0].get('no')
                if first_item_no:
                    detail = api.get_product_detail(first_item_no)
                    
                    if detail:
                        print(f"\n상품 상세 정보:")
                        print(f"  상품명: {detail.get('tit', 'N/A')}")
                        print(f"  가격: {detail.get('prc', 0):,}원")
                        print(f"  재고: {detail.get('qty', 'N/A')}")
                        print(f"  배송비: {detail.get('dlv_fee', 'N/A')}")
                        print(f"  카테고리: {detail.get('ca_ko', 'N/A')}")
                        
                        # 상세 정보 저장
                        with open('domeggook_product_detail.json', 'w', encoding='utf-8') as f:
                            json.dump(detail, f, ensure_ascii=False, indent=2)
                        print("\n상품 상세 정보 저장: domeggook_product_detail.json")
    
    print("\n" + "=" * 80)
    print("테스트 완료!")


if __name__ == "__main__":
    main()