"""
도매처 전체 상품 수집 실행 스크립트
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.database.database import get_db
from app.services.collection.wholesaler_sync_service import WholesalerSyncService
from app.models.collected_product import WholesalerSource, CollectionStatus
from app.services.wholesalers.base_wholesaler import CollectionType

async def run_full_collection():
    """전체 도매처 상품 수집 실행"""
    print("\n" + "="*60)
    print("도매처 전체 상품 수집 시작")
    print("="*60 + "\n")
    
    # DB 세션 생성
    db = next(get_db())
    
    # 동기화 서비스 초기화
    sync_service = WholesalerSyncService()
    
    try:
        # 1. 모든 도매처에서 전체 상품 수집
        print("📦 전체 도매처 동기화 시작...")
        print("주의: 실제 API가 연결되어 있지 않아 시뮬레이션 데이터만 수집됩니다.\n")
        
        results = await sync_service.sync_all_wholesalers(
            collection_type=CollectionType.ALL,
            max_products_per_wholesaler=1000  # 도매처당 최대 1000개
        )
        
        # 2. 결과 출력
        print("\n" + "="*60)
        print("📊 수집 결과")
        print("="*60)
        
        total_collected = 0
        total_updated = 0
        total_failed = 0
        
        for source, result in results.items():
            print(f"\n[{source}]")
            print(f"  - 성공: {result.success}")
            print(f"  - 수집: {result.collected}개")
            print(f"  - 업데이트: {result.updated}개")
            print(f"  - 실패: {result.failed}개")
            print(f"  - 소요시간: {result.duration:.2f}초")
            
            if result.errors:
                print(f"  - 오류: {', '.join(result.errors[:3])}")
            
            total_collected += result.collected
            total_updated += result.updated
            total_failed += result.failed
        
        # 3. 전체 통계
        print("\n" + "="*60)
        print("📈 전체 통계")
        print("="*60)
        print(f"  - 총 수집: {total_collected}개")
        print(f"  - 총 업데이트: {total_updated}개")
        print(f"  - 총 실패: {total_failed}개")
        
        # 4. DB에서 실제 저장된 데이터 확인
        from sqlalchemy import func
        
        # 도매처별 통계
        stats = db.query(
            CollectedProduct.source,
            func.count(CollectedProduct.id).label('count')
        ).group_by(CollectedProduct.source).all()
        
        print("\n📋 DB 저장 현황:")
        for stat in stats:
            print(f"  - {stat.source.value}: {stat.count}개")
        
        # 카테고리별 통계
        category_stats = db.query(
            CollectedProduct.category,
            func.count(CollectedProduct.id).label('count')
        ).filter(
            CollectedProduct.category.isnot(None)
        ).group_by(CollectedProduct.category).limit(10).all()
        
        print("\n📁 주요 카테고리:")
        for cat, count in category_stats:
            print(f"  - {cat}: {count}개")
        
        # 가격대별 통계
        price_ranges = [
            (0, 10000, "1만원 미만"),
            (10000, 30000, "1~3만원"),
            (30000, 50000, "3~5만원"),
            (50000, 100000, "5~10만원"),
            (100000, float('inf'), "10만원 이상")
        ]
        
        print("\n💰 가격대별 분포:")
        for min_price, max_price, label in price_ranges:
            count = db.query(func.count(CollectedProduct.id)).filter(
                CollectedProduct.price >= min_price,
                CollectedProduct.price < max_price
            ).scalar()
            print(f"  - {label}: {count}개")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n" + "="*60)
    print("수집 완료")
    print("="*60)

# 개별 도매처 수집 함수
async def collect_from_specific_source(source: WholesalerSource, keyword: str = None, max_products: int = 100):
    """특정 도매처에서 상품 수집"""
    print(f"\n🏪 {source.value}에서 상품 수집 중...")
    
    db = next(get_db())
    sync_service = WholesalerSyncService()
    
    try:
        if keyword:
            # 키워드 검색은 구현되지 않았으므로 전체 수집
            print(f"  키워드 '{keyword}' 검색 (전체 수집으로 대체)")
        
        result = await sync_service.sync_wholesaler(
            wholesaler_type=source,
            collection_type=CollectionType.ALL,
            max_products=max_products
        )
        
        print(f"  ✅ 수집 완료: {result.collected}개")
        return result
        
    except Exception as e:
        print(f"  ❌ 오류: {str(e)}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("\n도매처 전체 상품 수집을 시작하시겠습니까?")
    print("주의: 실제 API가 연결되지 않아 테스트 데이터만 수집됩니다.")
    print("\n1. 전체 도매처 수집")
    print("2. 오너클랜만 수집")
    print("3. 도매매만 수집") 
    print("4. 젠트레이드만 수집")
    print("5. 취소")
    
    choice = input("\n선택 (1-5): ").strip()
    
    if choice == "1":
        asyncio.run(run_full_collection())
    elif choice == "2":
        asyncio.run(collect_from_specific_source(WholesalerSource.OWNERCLAN))
    elif choice == "3":
        asyncio.run(collect_from_specific_source(WholesalerSource.DOMEME))
    elif choice == "4":
        asyncio.run(collect_from_specific_source(WholesalerSource.GENTRADE))
    else:
        print("취소되었습니다.")