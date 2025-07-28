"""
간단한 도매처 상품 수집 테스트
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.database.database import get_db
from app.models.collected_product import CollectedProduct, CollectionStatus, WholesalerSource
from app.models.collected_product_history import CollectedProductHistory, ChangeType

def collect_sample_products():
    """샘플 상품 데이터를 DB에 저장"""
    print("\n=== 도매처 상품 수집 시작 ===\n")
    
    # DB 세션 생성
    db = next(get_db())
    
    try:
        # 샘플 상품 데이터
        sample_products = [
            {
                "source": WholesalerSource.OWNERCLAN,
                "name": "프리미엄 블루투스 무선이어폰 TWS-X100",
                "price": 25000,
                "category": "전자제품/이어폰",
                "supplier_id": "OC_TWS_001",
                "brand": "SoundPro",
                "description": "최신 블루투스 5.3 지원, 노이즈 캔슬링 기능",
                "stock_quantity": 150
            },
            {
                "source": WholesalerSource.OWNERCLAN,
                "name": "게이밍 무선이어폰 GX-2000",
                "price": 32000,
                "category": "전자제품/이어폰",
                "supplier_id": "OC_GX_002",
                "brand": "GameAudio",
                "description": "초저지연 게이밍 모드, RGB LED",
                "stock_quantity": 80
            },
            {
                "source": WholesalerSource.DOMEME,
                "name": "스마트워치 프로 2024",
                "price": 45000,
                "category": "전자제품/스마트워치",
                "supplier_id": "DM_SW_001",
                "brand": "TechWatch",
                "description": "심박수 측정, GPS, 방수 기능",
                "stock_quantity": 200
            },
            {
                "source": WholesalerSource.DOMEME,
                "name": "무선충전 보조배터리 20000mAh",
                "price": 28000,
                "category": "전자제품/충전기",
                "supplier_id": "DM_PB_002",
                "brand": "PowerBank",
                "description": "고속충전 지원, 무선충전 패드 내장",
                "stock_quantity": 120
            },
            {
                "source": WholesalerSource.GENTRADE,
                "name": "프리미엄 가죽 스마트폰 케이스",
                "price": 15000,
                "category": "액세서리/케이스",
                "supplier_id": "GT_CASE_001",
                "brand": "LuxCase",
                "description": "진짜 가죽 소재, 카드 수납 가능",
                "stock_quantity": 300
            }
        ]
        
        # 배치 ID 생성
        batch_id = f"manual_collect_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        print(f"배치 ID: {batch_id}\n")
        
        # 상품 저장
        saved_count = 0
        for product_data in sample_products:
            try:
                # CollectedProduct 생성
                product = CollectedProduct(
                    source=product_data["source"],
                    collection_keyword="manual_test",
                    collection_batch_id=batch_id,
                    supplier_id=product_data["supplier_id"],
                    supplier_name=f"{product_data['source'].value} 공급업체",
                    supplier_url=f"https://{product_data['source'].value}.com/product/{product_data['supplier_id']}",
                    name=product_data["name"],
                    description=product_data["description"],
                    brand=product_data["brand"],
                    category=product_data["category"],
                    price=product_data["price"],
                    original_price=int(product_data["price"] * 1.3),  # 30% 할인된 가격으로 가정
                    wholesale_price=int(product_data["price"] * 0.8),  # 도매가는 판매가의 80%
                    stock_status="available",
                    stock_quantity=product_data["stock_quantity"],
                    main_image_url=f"https://example.com/images/{product_data['supplier_id']}.jpg",
                    status=CollectionStatus.COLLECTED,
                    quality_score=8.5,
                    popularity_score=7.0,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7)
                )
                
                db.add(product)
                saved_count += 1
                
                print(f"[OK] 저장됨: {product.name}")
                print(f"  - 도매처: {product.source.value}")
                print(f"  - 가격: {product.price:,}원")
                print(f"  - 재고: {product.stock_quantity}개\n")
                
                # 초기 가격 이력 추가
                history = CollectedProductHistory(
                    collected_product_id=product.id,
                    source=product.source,
                    supplier_id=product.supplier_id,
                    change_type=ChangeType.NEW_COLLECTION,
                    new_price=product.price,
                    new_stock_quantity=product.stock_quantity,
                    new_stock_status="available",
                    batch_id=batch_id
                )
                db.add(history)
                
            except Exception as e:
                print(f"[FAIL] 실패: {product_data['name']} - {str(e)}\n")
        
        # 변경사항 커밋
        db.commit()
        
        print(f"\n총 {saved_count}개 상품 저장 완료!")
        
        # 저장된 상품 통계
        print("\n=== 수집 통계 ===")
        total = db.query(CollectedProduct).count()
        print(f"전체 수집된 상품: {total}개")
        
        for source in WholesalerSource:
            count = db.query(CollectedProduct).filter(
                CollectedProduct.source == source
            ).count()
            print(f"- {source.value}: {count}개")
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n=== 수집 완료 ===")

if __name__ == "__main__":
    collect_sample_products()