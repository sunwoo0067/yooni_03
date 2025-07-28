#!/usr/bin/env python3
"""
도매처 통합 테스트 및 상품 수집
기존 구현과 실제 API 키를 활용
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

# 기존 구현 임포트
try:
    from app.services.wholesalers.ownerclan_api import OwnerClanAPI
    from app.services.wholesalers.domeggook_api import DomeggookAPI
    from app.services.wholesalers.base_wholesaler import CollectionType
except ImportError as e:
    print(f"임포트 오류: {e}")
    print("기존 구현을 사용할 수 없습니다.")
    exit(1)


async def test_and_collect():
    """도매처 테스트 및 상품 수집"""
    
    print("=" * 60)
    print("도매처 통합 테스트")
    print("=" * 60)
    
    results = {
        'ownerclan': {'status': 'pending', 'products': []},
        'domeggook': {'status': 'pending', 'products': []},
        'summary': {
            'total_products': 0,
            'execution_time': None,
            'timestamp': datetime.now().isoformat()
        }
    }
    
    start_time = datetime.now()
    
    # 1. 오너클랜 테스트
    print("\n[1] 오너클랜 테스트")
    print("-" * 40)
    
    ownerclan_credentials = {
        'username': os.getenv('OWNERCLAN_USERNAME'),
        'password': os.getenv('OWNERCLAN_PASSWORD'),
        'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
        'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
    }
    
    if ownerclan_credentials['username'] and ownerclan_credentials['password']:
        try:
            api = OwnerClanAPI(ownerclan_credentials)
            
            # 연결 테스트
            test_result = await api.test_connection()
            print(f"연결 테스트: {test_result['success']}")
            
            if test_result['success']:
                results['ownerclan']['status'] = 'connected'
                results['ownerclan']['test_result'] = test_result
                
                # 상품 수집 시도
                print("상품 수집 중...")
                product_count = 0
                
                async for product in api.collect_products(
                    collection_type=CollectionType.RECENT,
                    filters={'days': 30},
                    max_products=10
                ):
                    product_data = {
                        'id': product.wholesaler_product_id,
                        'name': product.name,
                        'price': product.wholesale_price,
                        'stock': product.stock_quantity,
                        'category': product.category_path
                    }
                    results['ownerclan']['products'].append(product_data)
                    product_count += 1
                    print(f"  수집: {product.name[:50]}...")
                    
                print(f"  총 {product_count}개 상품 수집")
            else:
                results['ownerclan']['status'] = 'failed'
                results['ownerclan']['error'] = test_result.get('message', 'Unknown error')
                print(f"  오류: {test_result.get('message')}")
                
        except Exception as e:
            results['ownerclan']['status'] = 'error'
            results['ownerclan']['error'] = str(e)
            print(f"  예외 발생: {e}")
    else:
        results['ownerclan']['status'] = 'no_credentials'
        print("  인증 정보가 없습니다.")
    
    # 2. 도매꾹 테스트
    print("\n[2] 도매꾹 테스트")
    print("-" * 40)
    
    domeggook_credentials = {
        'api_key': os.getenv('DOMEGGOOK_API_KEY'),
        'api_url': 'https://openapi.domeggook.com'
    }
    
    if domeggook_credentials['api_key']:
        try:
            api = DomeggookAPI(domeggook_credentials)
            
            # 연결 테스트
            test_result = await api.test_connection()
            print(f"연결 테스트: {test_result['success']}")
            
            if test_result['success']:
                results['domeggook']['status'] = 'connected'
                results['domeggook']['test_result'] = test_result
                
                # 카테고리 조회
                categories = await api.get_categories()
                print(f"카테고리 수: {len(categories)}")
                
                # 상품 수집 시도
                print("상품 수집 중...")
                product_count = 0
                
                async for product in api.collect_products(
                    collection_type=CollectionType.ALL,
                    max_products=10
                ):
                    product_data = {
                        'id': product.wholesaler_product_id,
                        'name': product.name,
                        'price': product.wholesale_price,
                        'stock': product.stock_quantity,
                        'category': product.category_path
                    }
                    results['domeggook']['products'].append(product_data)
                    product_count += 1
                    print(f"  수집: {product.name[:50]}...")
                    
                print(f"  총 {product_count}개 상품 수집")
            else:
                results['domeggook']['status'] = 'failed'
                results['domeggook']['error'] = test_result.get('message', 'Unknown error')
                print(f"  오류: {test_result.get('message')}")
                
        except Exception as e:
            results['domeggook']['status'] = 'error'
            results['domeggook']['error'] = str(e)
            print(f"  예외 발생: {e}")
    else:
        results['domeggook']['status'] = 'no_credentials'
        print("  API 키가 없습니다.")
    
    # 실행 시간 계산
    execution_time = (datetime.now() - start_time).total_seconds()
    results['summary']['execution_time'] = execution_time
    
    # 총 상품 수 계산
    total_products = (
        len(results['ownerclan']['products']) + 
        len(results['domeggook']['products'])
    )
    results['summary']['total_products'] = total_products
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    print(f"오너클랜: {results['ownerclan']['status']} ({len(results['ownerclan']['products'])}개 상품)")
    print(f"도매꾹: {results['domeggook']['status']} ({len(results['domeggook']['products'])}개 상품)")
    print(f"\n총 상품 수: {total_products}개")
    print(f"실행 시간: {execution_time:.2f}초")
    
    # 결과 저장
    filename = f'wholesaler_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 파일: {filename}")
    
    return results


async def main():
    """메인 실행 함수"""
    
    # 환경 변수 확인
    print("환경 변수 확인:")
    env_vars = {
        'OWNERCLAN_USERNAME': os.getenv('OWNERCLAN_USERNAME'),
        'OWNERCLAN_PASSWORD': os.getenv('OWNERCLAN_PASSWORD'),
        'DOMEGGOOK_API_KEY': os.getenv('DOMEGGOOK_API_KEY')
    }
    
    for key, value in env_vars.items():
        if value and not value.startswith('your-'):
            print(f"[OK] {key}: {value[:5]}...")
        else:
            print(f"[NO] {key}: 미설정")
    
    print()
    
    # 테스트 실행
    results = await test_and_collect()
    
    # 수집된 상품이 있으면 데이터베이스에 저장 제안
    if results['summary']['total_products'] > 0:
        print("\n수집된 상품을 데이터베이스에 저장하시겠습니까?")
        print("(이 기능은 별도 구현이 필요합니다)")


if __name__ == "__main__":
    asyncio.run(main())