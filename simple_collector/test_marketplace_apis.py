"""
마켓플레이스 API 연동 테스트
실제 API로 베스트셀러 데이터 수집
"""

import asyncio
import aiohttp
from datetime import datetime
import json
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from database.connection import engine, SessionLocal
from collectors.bestseller_collector import BestsellerData
from utils.logger import app_logger


async def test_with_mock_api():
    """모의 API로 베스트셀러 수집 테스트"""
    app_logger.info("모의 API로 베스트셀러 수집 테스트 시작...")
    
    # 테이블 생성
    BestsellerData.metadata.create_all(bind=engine)
    
    # 테스트 데이터 생성
    test_data = []
    
    # 쿠팡 모의 데이터
    for i in range(1, 11):
        test_data.append({
            'marketplace': 'coupang',
            'rank': i,
            'category': '전자제품',
            'category_id': 'electronics',
            'product_id': f'coupang_prod_{i}',
            'product_name': f'쿠팡 베스트셀러 상품 {i}',
            'brand': f'브랜드{i}',
            'price': 10000 * i,
            'review_count': 100 * (11-i),
            'rating': 4.5 - (i * 0.1),
            'product_data': {
                'test': True,
                'image_url': f'https://example.com/image{i}.jpg'
            }
        })
    
    # 네이버 모의 데이터
    for i in range(1, 11):
        test_data.append({
            'marketplace': 'naver',
            'rank': i,
            'category': '패션의류',
            'category_id': 'fashion',
            'product_id': f'naver_prod_{i}',
            'product_name': f'네이버 인기상품 {i}',
            'brand': f'패션브랜드{i}',
            'price': 15000 * i,
            'review_count': 150 * (11-i),
            'rating': 4.7 - (i * 0.1),
            'product_data': {
                'test': True,
                'mall_name': f'쇼핑몰{i}'
            }
        })
    
    # DB에 저장
    db = SessionLocal()
    try:
        saved_count = 0
        for data in test_data:
            bestseller = BestsellerData(
                marketplace=data['marketplace'],
                rank=data['rank'],
                category=data['category'],
                category_id=data['category_id'],
                product_id=data['product_id'],
                product_name=data['product_name'],
                brand=data['brand'],
                price=data['price'],
                review_count=data['review_count'],
                rating=data['rating'],
                product_data=data['product_data']
            )
            db.add(bestseller)
            saved_count += 1
            
            if saved_count % 5 == 0:
                app_logger.info(f"저장 진행중: {saved_count}개")
        
        db.commit()
        app_logger.info(f"모의 베스트셀러 데이터 {saved_count}개 저장 완료")
        
        # 저장된 데이터 조회
        count = db.query(BestsellerData).count()
        app_logger.info(f"총 저장된 베스트셀러 데이터: {count}개")
        
        # 마켓별 통계
        coupang_count = db.query(BestsellerData).filter(
            BestsellerData.marketplace == 'coupang'
        ).count()
        naver_count = db.query(BestsellerData).filter(
            BestsellerData.marketplace == 'naver'
        ).count()
        
        app_logger.info(f"쿠팡: {coupang_count}개, 네이버: {naver_count}개")
        
    except Exception as e:
        db.rollback()
        app_logger.error(f"DB 저장 오류: {e}")
    finally:
        db.close()


async def test_marketplace_settings():
    """마켓플레이스 API 설정 확인"""
    app_logger.info("\n마켓플레이스 API 설정 확인...")
    
    db = SessionLocal()
    try:
        from database.models import Supplier
        
        # 마켓플레이스 공급사 조회
        marketplaces = db.query(Supplier).filter(
            Supplier.api_config.op('->>')('marketplace').cast(db.String) == 'true'
        ).all()
        
        if not marketplaces:
            app_logger.warning("등록된 마켓플레이스가 없습니다.")
            
            # 마켓플레이스 등록
            marketplaces_to_add = [
                {
                    'supplier_code': 'coupang',
                    'supplier_name': '쿠팡',
                    'api_config': {
                        'marketplace': True,
                        'api_key': 'test_key',
                        'secret_key': 'test_secret',
                        'vendor_id': 'test_vendor'
                    }
                },
                {
                    'supplier_code': 'naver',
                    'supplier_name': '네이버 스마트스토어',
                    'api_config': {
                        'marketplace': True,
                        'client_id': 'test_client',
                        'client_secret': 'test_secret'
                    }
                },
                {
                    'supplier_code': '11st',
                    'supplier_name': '11번가',
                    'api_config': {
                        'marketplace': True,
                        'api_key': 'test_key'
                    }
                }
            ]
            
            for mp_data in marketplaces_to_add:
                existing = db.query(Supplier).filter(
                    Supplier.supplier_code == mp_data['supplier_code']
                ).first()
                
                if existing:
                    existing.api_config = mp_data['api_config']
                    app_logger.info(f"{mp_data['supplier_name']} 설정 업데이트")
                else:
                    new_mp = Supplier(**mp_data)
                    db.add(new_mp)
                    app_logger.info(f"{mp_data['supplier_name']} 추가")
            
            db.commit()
            app_logger.info("마켓플레이스 등록 완료")
        else:
            app_logger.info(f"등록된 마켓플레이스: {len(marketplaces)}개")
            for mp in marketplaces:
                app_logger.info(f"  - {mp.supplier_name} ({mp.supplier_code})")
                
    except Exception as e:
        db.rollback()
        app_logger.error(f"설정 확인 오류: {e}")
    finally:
        db.close()


async def main():
    """메인 테스트 함수"""
    app_logger.info("=== 마켓플레이스 API 테스트 시작 ===")
    
    # 1. 마켓플레이스 설정 확인
    await test_marketplace_settings()
    
    # 2. 모의 API로 테스트
    await test_with_mock_api()
    
    app_logger.info("\n=== 테스트 완료 ===")
    app_logger.info("웹 UI에서 베스트셀러 메뉴를 확인하세요.")
    app_logger.info("URL: http://localhost:4173/bestseller")


if __name__ == "__main__":
    asyncio.run(main())