#!/usr/bin/env python3
"""
작동하는 API 테스트 (디버깅 결과 반영)
"""

import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


class OwnerClanWorkingAPI:
    """작동하는 오너클랜 API"""
    
    def __init__(self):
        self.username = os.getenv('OWNERCLAN_USERNAME')
        self.password = os.getenv('OWNERCLAN_PASSWORD')
        # Production과 Sandbox 둘 다 토큰만 반환하는 것으로 보임
        self.auth_url = 'https://auth.ownerclan.com/auth'
        self.api_url = 'https://api.ownerclan.com/v1/graphql'
        self.token = None
        
    def authenticate(self):
        """JWT 토큰 발급 (텍스트로 반환됨)"""
        print("\n[오너클랜] 인증 시도...")
        
        auth_data = {
            "service": "ownerclan",
            "userType": "seller",
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(self.auth_url, json=auth_data, timeout=30)
            
            if response.status_code == 200:
                # 응답이 JSON이 아닌 순수 토큰 텍스트
                self.token = response.text.strip()
                
                # JWT 토큰 형식 확인
                if self.token.startswith('eyJ') and len(self.token) > 100:
                    print(f"[✓] 토큰 발급 성공 (길이: {len(self.token)})")
                    return True
                else:
                    print(f"[✗] 예상치 못한 토큰 형식: {self.token[:50]}...")
                    
                    # JSON 응답일 가능성 체크
                    try:
                        data = json.loads(self.token)
                        if 'token' in data:
                            self.token = data['token']
                            print("[✓] JSON에서 토큰 추출 성공")
                            return True
                    except:
                        pass
                        
                    return False
            else:
                print(f"[✗] 인증 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[✗] 인증 오류: {e}")
            return False
            
    def get_products(self, limit=5):
        """상품 목록 조회"""
        if not self.token:
            print("[✗] 토큰이 없습니다")
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
                    print(f"[✗] GraphQL 오류: {data['errors']}")
                    return []
                    
                products = []
                edges = data.get('data', {}).get('allItems', {}).get('edges', [])
                
                for edge in edges:
                    product = edge.get('node', {})
                    products.append({
                        'id': product.get('key'),
                        'name': product.get('name'),
                        'price': product.get('price'),
                        'status': product.get('status')
                    })
                    
                print(f"[✓] {len(products)}개 상품 조회 성공")
                return products
            else:
                print(f"[✗] API 호출 실패: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
                
        except Exception as e:
            print(f"[✗] 상품 조회 오류: {e}")
            return []


class DomeggookWorkingAPI:
    """작동하는 도매꾹 API"""
    
    def __init__(self):
        self.api_key = os.getenv('DOMEGGOOK_API_KEY')
        # 올바른 base URL
        self.base_url = 'https://www.domeggook.com'
        
    def test_api_key(self):
        """API 키 테스트"""
        print("\n[도매꾹] API 키 검증...")
        
        # 간단한 API 호출로 테스트
        url = f"{self.base_url}/main/mpartner/pdealer_url.php"
        params = {
            'apikey': self.api_key,
            'pro_no': '1'  # 테스트용 상품번호
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                print(f"[✓] API 키 유효")
                return True
            else:
                print(f"[✗] API 키 검증 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"[✗] API 키 검증 오류: {e}")
            return False
            
    def get_products_web(self):
        """웹 페이지에서 상품 정보 가져오기 (API 대체)"""
        print("\n[도매꾹] 웹 페이지에서 상품 수집 시도...")
        
        # 도매꾹은 표준 API가 없고 웹 페이지 파싱이 필요할 수 있음
        print("[!] 도매꾹은 표준 REST API를 제공하지 않습니다.")
        print("[!] 상품 수집을 위해서는 웹 스크래핑이나 별도 협의가 필요합니다.")
        
        return []


class ZentradeWorkingAPI:
    """작동하는 젠트레이드 API"""
    
    def __init__(self):
        self.api_id = os.getenv('ZENTRADE_API_KEY')
        self.api_key = os.getenv('ZENTRADE_API_SECRET')
        self.base_url = 'https://www.zentrade.co.kr'
        
    def test_connection(self):
        """연결 테스트"""
        print("\n[젠트레이드] 연결 테스트...")
        
        # 기본 페이지 접근 테스트
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                print("[✓] 웹사이트 접근 가능")
                return True
            else:
                print(f"[✗] 웹사이트 접근 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"[✗] 연결 오류: {e}")
            return False
            
    def get_products_alternative(self):
        """대체 방법으로 상품 조회"""
        print("\n[젠트레이드] 대체 방법 시도...")
        
        # User-Agent 추가하여 재시도
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/xml,application/xml',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        url = f"{self.base_url}/shop/proc/product_api.php"
        params = {
            'id': self.api_id,
            'm_skey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 400:
                print("[✗] 요청이 차단되었습니다 (400 Bad Request)")
                print("[!] 젠트레이드는 IP 화이트리스트가 필요할 수 있습니다.")
                print("[!] 또는 API 계정 활성화가 필요할 수 있습니다.")
                
            return []
            
        except Exception as e:
            print(f"[✗] API 호출 오류: {e}")
            return []


def save_results(results):
    """결과 저장"""
    filename = f'working_api_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    # 요약 정보 추가
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_apis_tested': 3,
        'successful_apis': sum(1 for r in results.values() if r.get('status') == 'success'),
        'results': results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 파일: {filename}")
    return filename


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("실제 작동하는 API 테스트")
    print("=" * 60)
    print(f"실행 시간: {datetime.now()}")
    
    results = {}
    
    # 1. 오너클랜 테스트
    print("\n[1] 오너클랜 API 테스트")
    print("-" * 40)
    
    ownerclan_api = OwnerClanWorkingAPI()
    if ownerclan_api.authenticate():
        products = ownerclan_api.get_products(limit=3)
        results['ownerclan'] = {
            'status': 'success' if products else 'authenticated_but_no_products',
            'authenticated': True,
            'products': products,
            'notes': 'JWT 토큰이 텍스트로 반환됨'
        }
    else:
        results['ownerclan'] = {
            'status': 'failed',
            'authenticated': False,
            'error': 'Authentication failed'
        }
    
    # 2. 도매꾹 테스트
    print("\n[2] 도매꾹 API 테스트")
    print("-" * 40)
    
    domeggook_api = DomeggookWorkingAPI()
    api_valid = domeggook_api.test_api_key()
    products = domeggook_api.get_products_web()
    
    results['domeggook'] = {
        'status': 'api_key_valid' if api_valid else 'failed',
        'api_key_valid': api_valid,
        'products': products,
        'notes': '표준 REST API 미제공, 웹 스크래핑 필요'
    }
    
    # 3. 젠트레이드 테스트
    print("\n[3] 젠트레이드 API 테스트")
    print("-" * 40)
    
    zentrade_api = ZentradeWorkingAPI()
    connected = zentrade_api.test_connection()
    products = zentrade_api.get_products_alternative()
    
    results['zentrade'] = {
        'status': 'blocked',
        'website_accessible': connected,
        'products': products,
        'notes': 'API 요청 차단됨, IP 화이트리스트 또는 계정 활성화 필요'
    }
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for wholesaler, result in results.items():
        status = result.get('status', 'unknown')
        notes = result.get('notes', '')
        print(f"\n{wholesaler}:")
        print(f"  상태: {status}")
        if notes:
            print(f"  참고: {notes}")
    
    # 결과 저장
    save_results(results)
    
    # 추천사항
    print("\n" + "=" * 60)
    print("추천사항")
    print("=" * 60)
    print("\n1. 오너클랜: JWT 토큰은 발급되지만 API 호출 시 추가 디버깅 필요")
    print("2. 도매꾹: 공식 API가 없으므로 웹 스크래핑 구현 필요")
    print("3. 젠트레이드: 고객지원에 API 활성화 요청 필요")


if __name__ == "__main__":
    main()