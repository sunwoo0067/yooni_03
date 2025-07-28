#!/usr/bin/env python3
"""
도매꾹 모든 API 버전 상세 테스트
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


def test_all_endpoints():
    """모든 엔드포인트와 버전 조합 테스트"""
    api_key = os.getenv('DOMEGGOOK_API_KEY')
    base_url = 'https://domeggook.com/ssl/api/'
    
    # 테스트할 모드들
    modes = ['getCategoryList', 'getItemList', 'getItemView']
    versions = ['1.0', '2.0', '3.0', '4.0', '4.1', '4.3', '4.5', '5.0']
    
    results = {}
    
    print("도매꾹 API 전체 테스트")
    print("=" * 80)
    print(f"API Key: {api_key}")
    print(f"Base URL: {base_url}")
    print("=" * 80)
    
    for mode in modes:
        print(f"\n\n[{mode} 테스트]")
        print("-" * 60)
        results[mode] = {}
        
        for version in versions:
            params = {
                'ver': version,
                'mode': mode,
                'aid': api_key,
                'om': 'json'
            }
            
            # mode별 추가 파라미터
            if mode == 'getItemList':
                params.update({
                    'sz': 5,
                    'pg': 1,
                    'market': 'dome'
                })
            elif mode == 'getItemView':
                params['no'] = '1'  # 테스트용 상품번호
                
            try:
                response = requests.get(base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 에러 체크
                        if 'errors' in data:
                            error_code = data['errors'].get('code')
                            error_msg = data['errors'].get('message', '')
                            results[mode][version] = f"❌ 오류 {error_code}: {error_msg}"
                            print(f"  v{version}: ❌ {error_msg}")
                        else:
                            # 성공적인 응답
                            if mode == 'getCategoryList':
                                cat_count = count_categories(data)
                                results[mode][version] = f"✓ 성공 (카테고리 {cat_count}개)"
                                print(f"  v{version}: ✓ 카테고리 {cat_count}개")
                            elif mode == 'getItemList':
                                item_count = len(data.get('item', []))
                                total = data.get('header', {}).get('ttl_cnt', 0)
                                results[mode][version] = f"✓ 성공 (상품 {item_count}/{total}개)"
                                print(f"  v{version}: ✓ 상품 {item_count}개 (전체 {total}개)")
                            else:
                                results[mode][version] = "✓ 성공"
                                print(f"  v{version}: ✓ 성공")
                                
                    except json.JSONDecodeError:
                        results[mode][version] = "❌ JSON 파싱 실패"
                        print(f"  v{version}: ❌ JSON 파싱 실패")
                        print(f"    응답: {response.text[:200]}")
                else:
                    results[mode][version] = f"❌ HTTP {response.status_code}"
                    print(f"  v{version}: ❌ HTTP {response.status_code}")
                    
            except Exception as e:
                results[mode][version] = f"❌ 오류: {str(e)[:30]}"
                print(f"  v{version}: ❌ {str(e)[:50]}")
    
    # 결과 요약
    print("\n\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    for mode, versions_results in results.items():
        print(f"\n{mode}:")
        working_versions = [v for v, r in versions_results.items() if r.startswith('✓')]
        if working_versions:
            print(f"  작동하는 버전: {', '.join(working_versions)}")
        else:
            print("  작동하는 버전 없음")
            
    # 작동하는 조합으로 실제 테스트
    print("\n\n" + "=" * 80)
    print("실제 데이터 테스트")
    print("=" * 80)
    
    # getItemList가 작동하는 버전 찾기
    for version, result in results.get('getItemList', {}).items():
        if result.startswith('✓'):
            print(f"\n[상품 목록 - 버전 {version}]")
            test_product_list(api_key, version)
            break
            
    return results


def count_categories(data):
    """카테고리 개수 계산"""
    count = 0
    
    def count_recursive(items):
        nonlocal count
        if isinstance(items, dict):
            for key, value in items.items():
                count += 1
                if 'child' in value:
                    count_recursive(value['child'])
                    
    if 'domeggook' in data and 'items' in data['domeggook']:
        count_recursive(data['domeggook']['items'])
        
    return count


def test_product_list(api_key, version):
    """상품 목록 상세 테스트"""
    base_url = 'https://domeggook.com/ssl/api/'
    
    params = {
        'ver': version,
        'mode': 'getItemList',
        'aid': api_key,
        'om': 'json',
        'sz': 10,
        'pg': 1,
        'market': 'dome',
        'so': 'rd'  # 정렬: 랭킹순
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            if 'item' in data:
                items = data['item']
                print(f"상품 {len(items)}개 조회 성공:")
                
                for idx, item in enumerate(items[:3]):  # 처음 3개만
                    print(f"\n{idx + 1}. {item.get('tit', 'N/A')}")
                    print(f"   가격: {item.get('prc', 0):,}원")
                    print(f"   판매자: {item.get('mmb', 'N/A')}")
                    print(f"   상품번호: {item.get('no', 'N/A')}")
                    
                # 첫 번째 상품의 상세 정보 조회
                if items:
                    first_item_no = items[0].get('no')
                    if first_item_no:
                        print(f"\n\n[상품 상세 - 상품번호 {first_item_no}]")
                        test_product_detail(api_key, version, first_item_no)
                        
    except Exception as e:
        print(f"오류: {e}")


def test_product_detail(api_key, version, product_no):
    """상품 상세 정보 테스트"""
    base_url = 'https://domeggook.com/ssl/api/'
    
    params = {
        'ver': version,
        'mode': 'getItemView',
        'aid': api_key,
        'no': product_no,
        'om': 'json'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            if 'errors' not in data:
                print("상품 상세 정보:")
                print(f"  상품명: {data.get('tit', 'N/A')}")
                print(f"  가격: {data.get('prc', 0):,}원")
                print(f"  재고: {data.get('qty', 'N/A')}")
                print(f"  배송비: {data.get('dlv_fee', 'N/A')}")
                print(f"  카테고리: {data.get('ca_ko', 'N/A')}")
            else:
                print(f"오류: {data['errors'].get('message')}")
                
    except Exception as e:
        print(f"오류: {e}")


def main():
    """메인 함수"""
    print(f"실행 시간: {datetime.now()}\n")
    
    results = test_all_endpoints()
    
    # 결과 저장
    filename = f'domeggook_api_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n결과 파일: {filename}")


if __name__ == "__main__":
    main()