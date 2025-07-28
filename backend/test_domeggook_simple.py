#!/usr/bin/env python3
"""
도매매 API 간단한 테스트
"""

import os
import sys
import requests
import json
from datetime import datetime

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()


def test_domeggook_api():
    """도매매 API 직접 테스트"""
    print("도매매 API 테스트")
    print("=" * 60)
    
    api_key = os.getenv('DOMEGGOOK_API_KEY')
    print(f"API Key: {api_key}")
    
    # 여러 URL 형식 시도
    test_urls = [
        # v4.1 형식
        f"https://openapi.domeggook.com/api/product/list?version=4.1&api_key={api_key}&page=1&limit=10",
        # v1.0 카테고리
        f"https://openapi.domeggook.com/api/category/list?version=1.0&api_key={api_key}",
        # 다른 가능한 URL들
        f"http://api.domeggook.com/product/list?api_key={api_key}",
        f"https://www.domeggook.com/api/product/list?api_key={api_key}",
        f"https://openapi.domeggook.com/main/open_api?api_key={api_key}",
    ]
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n테스트 {i}: {url[:50]}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                # JSON 응답 시도
                try:
                    data = response.json()
                    print("✓ JSON 응답 성공")
                    print(f"응답 미리보기: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
                    
                    # 성공한 URL 저장
                    with open('domeggook_working_url.txt', 'w') as f:
                        f.write(f"Working URL: {url}\n")
                        f.write(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                    
                    return True
                    
                except json.JSONDecodeError:
                    print("✗ JSON 파싱 실패")
                    print(f"응답 텍스트: {response.text[:200]}...")
            else:
                print(f"✗ 실패: {response.status_code}")
                if response.status_code == 404:
                    print("페이지를 찾을 수 없음")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ 요청 오류: {e}")
    
    # 도매매 웹사이트에서 정보 수집 시도
    print("\n\n도매매 웹사이트 접근 테스트...")
    try:
        response = requests.get("https://www.domeggook.com", headers=headers, timeout=10)
        print(f"웹사이트 응답: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ 웹사이트 접근 가능")
            print("\n참고: 도매매 API는 별도의 승인 절차가 필요할 수 있습니다.")
            print("1. 도매매 사이트에서 API 사용 신청")
            print("2. API 키 발급 및 활성화")
            print("3. API 문서 확인 후 올바른 엔드포인트 사용")
            
    except Exception as e:
        print(f"웹사이트 접근 오류: {e}")
    
    return False


def create_sample_domeggook_data():
    """도매매 샘플 데이터 생성"""
    print("\n\n도매매 샘플 데이터 생성")
    print("=" * 60)
    
    sample_products = [
        {
            'wholesaler': 'Domeggook',
            'product_id': 'DG001',
            'name': '도매매 샘플 의류 - 여성 블라우스',
            'price': 12000,
            'stock': 150,
            'category': '의류/여성의류',
            'supplier': '패션플러스',
            'image_url': 'https://sample.domeggook.com/image1.jpg'
        },
        {
            'wholesaler': 'Domeggook',
            'product_id': 'DG002',
            'name': '도매매 샘플 가방 - 크로스백',
            'price': 18000,
            'stock': 80,
            'category': '가방/지갑',
            'supplier': '백앤백',
            'image_url': 'https://sample.domeggook.com/image2.jpg'
        },
        {
            'wholesaler': 'Domeggook',
            'product_id': 'DG003',
            'name': '도매매 샘플 액세서리 - 목걸이',
            'price': 8500,
            'stock': 200,
            'category': '액세서리/주얼리',
            'supplier': '쥬얼리하우스',
            'image_url': 'https://sample.domeggook.com/image3.jpg'
        },
        {
            'wholesaler': 'Domeggook',
            'product_id': 'DG004',
            'name': '도매매 샘플 신발 - 운동화',
            'price': 35000,
            'stock': 50,
            'category': '신발/운동화',
            'supplier': '슈즈마켓',
            'image_url': 'https://sample.domeggook.com/image4.jpg'
        },
        {
            'wholesaler': 'Domeggook',
            'product_id': 'DG005',
            'name': '도매매 샘플 화장품 - 스킨케어 세트',
            'price': 25000,
            'stock': 100,
            'category': '뷰티/화장품',
            'supplier': '뷰티서플라이',
            'image_url': 'https://sample.domeggook.com/image5.jpg'
        }
    ]
    
    # 샘플 데이터 저장
    filename = f'domeggook_sample_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_products': len(sample_products),
            'products': sample_products,
            'note': '도매매 API 연동이 실패하여 샘플 데이터를 생성했습니다.'
        }, f, ensure_ascii=False, indent=2)
    
    print(f"샘플 데이터 생성 완료: {len(sample_products)}개")
    print(f"파일 저장: {filename}")
    
    # 통계 출력
    categories = {}
    for product in sample_products:
        cat = product['category'].split('/')[0]
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n카테고리별 분포:")
    for cat, count in categories.items():
        print(f"  - {cat}: {count}개")
    
    return sample_products


def main():
    """메인 함수"""
    print("도매매 API 연동 테스트")
    print(f"실행 시간: {datetime.now()}")
    print("\n")
    
    # API 테스트
    api_success = test_domeggook_api()
    
    if not api_success:
        print("\n\nAPI 연동 실패 - 샘플 데이터로 대체합니다.")
        sample_products = create_sample_domeggook_data()
        
        print("\n\n도매매 API 연동 정보:")
        print("1. API 키는 도매매 사이트에서 별도 신청 필요")
        print("2. API 문서: https://openapi.domeggook.com/main/reference")
        print("3. 현재 API 키가 활성화되지 않았거나 잘못된 것으로 보임")
        print("4. 실제 연동을 위해서는 도매매 고객센터 문의 필요")
    
    print("\n\n테스트 완료")


if __name__ == "__main__":
    main()