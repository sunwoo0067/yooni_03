"""
도매처 상품 수집 직접 실행 스크립트
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.database.database import get_db
from app.services.collection.wholesaler_sync_service import WholesalerSyncService
from app.models.collected_product import CollectedProduct, CollectionStatus, WholesalerSource

async def collect_products():
    """도매처 상품 수집 실행"""
    print("\n=== 도매처 상품 수집 시작 ===\n")
    
    # DB 세션 생성
    db = next(get_db())
    
    try:
        # 동기화 서비스 생성
        sync_service = WholesalerSyncService(db)
        
        # 1. 오너클랜에서 무선이어폰 수집
        print("1. 오너클랜에서 '무선이어폰' 검색...")
        result1 = await sync_service.sync_specific_keyword(
            source=WholesalerSource.OWNERCLAN,
            keyword="무선이어폰",
            max_products=10
        )
        print(f"   - 수집 결과: {result1['success']}")
        print(f"   - 수집된 상품 수: {result1['collected_count']}")
        print(f"   - 배치 ID: {result1['batch_id']}")
        
        # 2. 도매매에서 스마트워치 수집
        print("\n2. 도매매에서 '스마트워치' 검색...")
        result2 = await sync_service.sync_specific_keyword(
            source=WholesalerSource.DOMEME,
            keyword="스마트워치",
            max_products=5
        )
        print(f"   - 수집 결과: {result2['success']}")
        print(f"   - 수집된 상품 수: {result2['collected_count']}")
        
        # 3. 수집된 상품 조회
        print("\n3. 수집된 상품 목록 조회...")
        collected_products = db.query(CollectedProduct).filter(
            CollectedProduct.status == CollectionStatus.COLLECTED
        ).order_by(CollectedProduct.collected_at.desc()).limit(10).all()
        
        print(f"\n최근 수집된 상품 {len(collected_products)}개:")
        for i, product in enumerate(collected_products, 1):
            print(f"\n{i}. {product.name}")
            print(f"   - 도매처: {product.source.value}")
            print(f"   - 가격: {product.price:,}원")
            print(f"   - 재고: {product.stock_status}")
            print(f"   - 카테고리: {product.category}")
            print(f"   - 수집시간: {product.collected_at}")
            print(f"   - ID: {product.id}")
        
        # 4. 통계 출력
        print("\n4. 수집 통계:")
        total_count = db.query(CollectedProduct).count()
        collected_count = db.query(CollectedProduct).filter(
            CollectedProduct.status == CollectionStatus.COLLECTED
        ).count()
        sourced_count = db.query(CollectedProduct).filter(
            CollectedProduct.status == CollectionStatus.SOURCED
        ).count()
        
        print(f"   - 전체 수집 상품: {total_count}개")
        print(f"   - 대기 중 상품: {collected_count}개")
        print(f"   - 소싱된 상품: {sourced_count}개")
        
        # 도매처별 통계
        print("\n   도매처별 상품 수:")
        for source in WholesalerSource:
            count = db.query(CollectedProduct).filter(
                CollectedProduct.source == source
            ).count()
            print(f"   - {source.value}: {count}개")
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n=== 수집 완료 ===")

# 비동기 함수 실행
if __name__ == "__main__":
    asyncio.run(collect_products())