#!/usr/bin/env python3
"""
수정된 API 클래스 통합 테스트
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

# 수정된 API 클래스 임포트
from app.services.wholesalers.ownerclan_api_fixed import OwnerClanAPIFixed
from app.services.wholesalers.zentrade_api_fixed import ZentradeAPIFixed
from app.services.wholesalers.base_wholesaler import CollectionType


async def test_ownerclan():
    """오너클랜 API 테스트"""
    print("\n" + "=" * 60)
    print("오너클랜 API 테스트")
    print("=" * 60)
    
    credentials = {
        'username': os.getenv('OWNERCLAN_USERNAME'),
        'password': os.getenv('OWNERCLAN_PASSWORD'),
        'use_sandbox': False  # Production 사용
    }
    
    api = OwnerClanAPIFixed(credentials)
    
    # 연결 테스트
    print("\n1. 연결 테스트")
    test_result = await api.test_connection()
    print(f"결과: {test_result}")
    
    if test_result['success']:
        # 카테고리 조회
        print("\n2. 카테고리 조회")
        categories = await api.get_categories()
        print(f"카테고리 수: {len(categories)}")
        if categories:
            print("샘플 카테고리:")
            for cat in categories[:3]:
                print(f"  - {cat.get('name')} (ID: {cat.get('id')})")
        
        # 상품 수집
        print("\n3. 상품 수집")
        products = []
        async for product in api.collect_products(max_products=5):
            products.append({
                'id': product.wholesaler_product_id,
                'name': product.name,
                'price': product.wholesale_price,
                'stock': product.stock_quantity,
                'category': product.category_path,
                'options': len(product.options)
            })
            print(f"  - {product.name[:50]}... ({product.wholesale_price}원)")
        
        return {
            'status': 'success',
            'connected': True,
            'category_count': len(categories),
            'product_count': len(products),
            'products': products
        }
    else:
        return {
            'status': 'failed',
            'connected': False,
            'error': test_result.get('message')
        }


async def test_zentrade():
    """젠트레이드 API 테스트"""
    print("\n" + "=" * 60)
    print("젠트레이드 API 테스트")
    print("=" * 60)
    
    credentials = {
        'api_key': os.getenv('ZENTRADE_API_KEY'),
        'api_secret': os.getenv('ZENTRADE_API_SECRET')
    }
    
    api = ZentradeAPIFixed(credentials)
    
    # 연결 테스트
    print("\n1. 연결 테스트")
    test_result = await api.test_connection()
    print(f"결과: {test_result}")
    
    if test_result['success']:
        # 상품 수집
        print("\n2. 상품 수집")
        products = []
        async for product in api.collect_products(max_products=5):
            products.append({
                'id': product.wholesaler_product_id,
                'name': product.name,
                'price': product.wholesale_price,
                'stock': product.stock_quantity,
                'category': product.category_path,
                'brand': product.brand,
                'model': product.model_name
            })
            print(f"  - {product.name[:50]}... ({product.wholesale_price}원)")
        
        # 카테고리 추출 (상품에서)
        print("\n3. 카테고리 수집 (상품에서 추출)")
        categories = await api.get_categories()
        print(f"카테고리 수: {len(categories)}")
        
        return {
            'status': 'success',
            'connected': True,
            'product_count': test_result['details'].get('product_count', 0),
            'collected_products': len(products),
            'category_count': len(categories),
            'products': products
        }
    else:
        return {
            'status': 'failed',
            'connected': False,
            'error': test_result.get('message')
        }


async def main():
    """메인 테스트 함수"""
    print("수정된 API 클래스 통합 테스트")
    print("실행 시간:", datetime.now())
    
    results = {}
    
    # 오너클랜 테스트
    try:
        ownerclan_result = await test_ownerclan()
        results['ownerclan'] = ownerclan_result
    except Exception as e:
        results['ownerclan'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 젠트레이드 테스트
    try:
        zentrade_result = await test_zentrade()
        results['zentrade'] = zentrade_result
    except Exception as e:
        results['zentrade'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for wholesaler, result in results.items():
        print(f"\n{wholesaler}:")
        print(f"  상태: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"  상품 수: {result.get('product_count', 0)}")
            print(f"  수집된 상품: {result.get('collected_products', 0)}")
            print(f"  카테고리 수: {result.get('category_count', 0)}")
        else:
            print(f"  오류: {result.get('error')}")
    
    # 결과 저장
    filename = f'integrated_api_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 파일: {filename}")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())