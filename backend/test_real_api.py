#!/usr/bin/env python3
"""
실제 API 키를 사용한 테스트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import requests
import json

# 프로젝트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

# API 설정
BASE_URL = "http://localhost:8000"
API_V1_URL = f"{BASE_URL}/api/v1"


def test_ai_service():
    """AI 서비스 테스트 (Gemini)"""
    print("\n" + "=" * 60)
    print("[TEST] AI 서비스 테스트 (Google Gemini)")
    print("=" * 60)
    
    # Gemini API 키 확인
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다.")
        return
    
    print(f"[INFO] Gemini API 키: {gemini_key[:10]}...")
    
    # AI 분석 요청
    test_product = {
        "title": "무선 블루투스 이어폰 TWS Pro",
        "description": "노이즈 캔슬링 기능이 탑재된 프리미엄 무선 이어폰",
        "price": 89000,
        "category": "전자제품"
    }
    
    try:
        response = requests.post(
            f"{API_V1_URL}/ai/analyze-product",
            json=test_product,
            timeout=30
        )
        
        print(f"\n[상품 분석 요청]")
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"분석 결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
            print("[PASS] AI 분석 성공")
        else:
            print(f"에러: {response.text}")
            print("[FAIL] AI 분석 실패")
            
    except Exception as e:
        print(f"[ERROR] {e}")


def test_wholesaler_api():
    """도매처 실제 API 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] 도매처 API 테스트")
    print("=" * 60)
    
    # 실제 도매처 상품 수집 테스트
    wholesalers = ["ownerclan", "domeggook", "zentrade"]
    
    for wholesaler in wholesalers:
        print(f"\n[{wholesaler.upper()}] 상품 수집 테스트")
        
        try:
            # 실제 상품 수집 API 호출
            response = requests.post(
                f"{API_V1_URL}/wholesaler-sync/collect/{wholesaler}",
                params={
                    "limit": 3,  # 테스트용으로 3개만
                    "use_cache": False  # 캐시 사용 안함 (실제 API 호출)
                },
                timeout=30
            )
            
            print(f"상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"수집된 상품 수: {result.get('collected_count', 0)}")
                
                # 첫 번째 상품 정보 출력
                if result.get('products'):
                    product = result['products'][0]
                    print(f"\n첫 번째 상품 정보:")
                    print(f"- 이름: {product.get('name', 'N/A')}")
                    print(f"- 가격: {product.get('price', 0):,}원")
                    print(f"- 재고: {product.get('stock_quantity', 0)}개")
                    print(f"- 이미지: {product.get('main_image_url', 'N/A')}")
                
                print(f"[PASS] {wholesaler} 수집 성공")
            else:
                print(f"에러: {response.text}")
                print(f"[FAIL] {wholesaler} 수집 실패")
                
        except Exception as e:
            print(f"[ERROR] {e}")


def test_marketplace_api():
    """마켓플레이스 API 테스트 (쿠팡, 네이버 등)"""
    print("\n" + "=" * 60)
    print("[TEST] 마켓플레이스 API 테스트")
    print("=" * 60)
    
    # 환경 변수에서 API 키 확인
    marketplaces = {
        "coupang": {
            "access_key": os.getenv("COUPANG_ACCESS_KEY"),
            "secret_key": os.getenv("COUPANG_SECRET_KEY"),
            "vendor_id": os.getenv("COUPANG_VENDOR_ID")
        },
        "naver": {
            "client_id": os.getenv("NAVER_CLIENT_ID"),
            "client_secret": os.getenv("NAVER_CLIENT_SECRET"),
            "store_id": os.getenv("NAVER_STORE_ID")
        },
        "11st": {
            "api_key": os.getenv("ELEVENTH_STREET_API_KEY"),
            "seller_id": os.getenv("ELEVENTH_STREET_SELLER_ID")
        }
    }
    
    for platform, keys in marketplaces.items():
        print(f"\n[{platform.upper()}] API 키 확인")
        for key_name, key_value in keys.items():
            if key_value and key_value != f"your-{platform}-{key_name.replace('_', '-')}":
                print(f"- {key_name}: {key_value[:10]}... [설정됨]")
            else:
                print(f"- {key_name}: [미설정]")


def test_product_sync():
    """상품 동기화 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] 상품 동기화 테스트")
    print("=" * 60)
    
    # 플랫폼 계정 목록 조회
    try:
        response = requests.get(f"{API_V1_URL}/platform-accounts")
        
        if response.status_code == 200:
            accounts = response.json()
            print(f"등록된 플랫폼 계정: {len(accounts)}개")
            
            for account in accounts:
                print(f"\n[{account['platform']}] {account['name']}")
                print(f"- 상태: {account['status']}")
                print(f"- 연결: {'연결됨' if account['is_connected'] else '미연결'}")
                print(f"- 마지막 동기화: {account.get('last_sync', 'N/A')}")
                
                # 동기화 테스트
                if account['is_connected'] and account['id']:
                    print(f"- 동기화 테스트 중...")
                    sync_response = requests.post(
                        f"{API_V1_URL}/platforms/{account['id']}/sync",
                        timeout=10
                    )
                    if sync_response.status_code == 200:
                        print(f"  [PASS] 동기화 시작됨")
                    else:
                        print(f"  [FAIL] 동기화 실패: {sync_response.text}")
        else:
            print(f"[ERROR] 플랫폼 계정 조회 실패: {response.text}")
            
    except Exception as e:
        print(f"[ERROR] {e}")


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("실제 API 키를 사용한 통합 테스트")
    print("=" * 60)
    
    # 서버 상태 확인
    print("\n[서버 상태 확인]")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[PASS] 서버가 정상 실행 중입니다.")
        else:
            print("[FAIL] 서버가 응답하지 않습니다.")
            print("서버를 먼저 실행해주세요: python main.py")
            return
    except:
        print("[ERROR] 서버에 연결할 수 없습니다.")
        print("서버를 먼저 실행해주세요: python main.py")
        return
    
    # 각 테스트 실행
    test_ai_service()
    test_wholesaler_api()
    test_marketplace_api()
    test_product_sync()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    # 실제 main.py를 사용하려면 포트를 8000으로 변경
    print("\n[NOTE] 실제 API를 테스트하려면 main.py를 실행해야 합니다.")
    print("1. 새 터미널을 열고: cd backend")
    print("2. 실행: python main.py")
    print("3. 이 스크립트를 다시 실행하세요.\n")
    
    main()