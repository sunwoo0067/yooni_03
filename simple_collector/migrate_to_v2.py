"""
v2 모델로 마이그레이션
- 도매처/마켓플레이스 테이블 분리
- 기존 데이터 이전
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from database.connection import engine, SessionLocal
from database.models import Product, Supplier
from database.models_v2 import (
    Base as BaseV2,
    WholesaleProduct, MarketplaceProduct, ProductMapping,
    PriceHistory, StockHistory
)
from datetime import datetime
import json

def migrate_to_v2():
    """v2 모델로 마이그레이션"""
    print("v2 마이그레이션 시작...")
    
    # 1. 새 테이블 생성
    print("1. 새 테이블 생성 중...")
    BaseV2.metadata.create_all(engine, checkfirst=True)
    print("   - wholesale_products")
    print("   - marketplace_products")
    print("   - product_mappings")
    print("   - price_history")
    print("   - stock_history")
    
    db = SessionLocal()
    
    try:
        # 2. 기존 데이터 마이그레이션
        print("\n2. 기존 데이터 마이그레이션...")
        
        # 기존 products 테이블의 모든 데이터 조회
        products = db.query(Product).all()
        
        wholesale_count = 0
        marketplace_count = 0
        
        for product in products:
            # supplier 정보로 타입 구분
            supplier_info = db.query(Supplier).filter(
                Supplier.supplier_code == product.supplier
            ).first()
            
            is_marketplace = (
                supplier_info and 
                supplier_info.api_config and 
                supplier_info.api_config.get('marketplace', False)
            )
            
            if is_marketplace:
                # 마켓플레이스 상품으로 이전
                marketplace_count += 1
                
                # product_id가 있으면 사용, 없으면 product_code 사용
                marketplace_id = getattr(product, 'product_id', None) or product.product_code
                
                new_marketplace = MarketplaceProduct(
                    marketplace_product_id=marketplace_id,
                    marketplace=product.supplier,
                    product_name=getattr(product, 'product_name', '') or product.product_info.get('name', ''),
                    selling_price=getattr(product, 'price', 0) or product.product_info.get('price', 0),
                    listing_info=product.product_info,
                    status=getattr(product, 'status', 'active'),
                    stock_quantity=getattr(product, 'stock', 0),
                    marketplace_category=getattr(product, 'category', ''),
                    marketplace_url=getattr(product, 'product_url', ''),
                    created_at=product.created_at,
                    updated_at=product.updated_at
                )
                db.add(new_marketplace)
                
            else:
                # 도매 상품으로 이전
                wholesale_count += 1
                
                # 가격 정보 추출
                price = 0
                if hasattr(product, 'price') and product.price:
                    price = product.price
                elif product.product_info:
                    # 다양한 형태의 가격 정보 추출
                    price_str = product.product_info.get('price') or product.product_info.get('sale_price') or product.product_info.get('wholesale_price') or "0"
                    try:
                        # 문자열이면 숫자만 추출
                        if isinstance(price_str, str):
                            price = int(''.join(filter(str.isdigit, price_str)) or 0)
                        else:
                            price = int(price_str or 0)
                    except:
                        price = 0
                
                # 가격이 여전히 0이면 기본값 설정
                if price == 0:
                    price = 10000  # 기본 가격
                
                new_wholesale = WholesaleProduct(
                    product_code=product.product_code,
                    supplier=product.supplier,
                    product_name=getattr(product, 'product_name', '') or product.product_info.get('name', ''),
                    wholesale_price=price,
                    product_info=product.product_info,
                    category=getattr(product, 'category', ''),
                    brand=getattr(product, 'brand', ''),
                    created_at=product.created_at,
                    updated_at=product.updated_at,
                    is_active=product.is_active
                )
                db.add(new_wholesale)
            
            # 100개마다 커밋
            if (wholesale_count + marketplace_count) % 100 == 0:
                db.commit()
                print(f"   처리 중... 도매: {wholesale_count}, 마켓: {marketplace_count}")
        
        # 최종 커밋
        db.commit()
        print(f"\n   마이그레이션 완료!")
        print(f"   - 도매 상품: {wholesale_count}개")
        print(f"   - 마켓플레이스 상품: {marketplace_count}개")
        
        # 3. suppliers 테이블 업데이트
        print("\n3. suppliers 테이블 업데이트...")
        
        # supplier_type 컬럼 추가 (이미 있으면 무시)
        try:
            db.execute(text("ALTER TABLE suppliers ADD COLUMN supplier_type VARCHAR(20) DEFAULT 'wholesale'"))
            db.commit()
        except:
            db.rollback()
        
        # 마켓플레이스 공급사 타입 업데이트
        marketplace_codes = ['coupang', 'naver', '11st']
        for code in marketplace_codes:
            db.execute(
                text("UPDATE suppliers SET supplier_type = 'marketplace' WHERE supplier_code = :code"),
                {"code": code}
            )
        db.commit()
        print("   공급사 타입 업데이트 완료")
        
        # 4. 통계 출력
        print("\n4. 마이그레이션 통계:")
        wholesale_total = db.query(WholesaleProduct).count()
        marketplace_total = db.query(MarketplaceProduct).count()
        
        print(f"   - wholesale_products: {wholesale_total}개")
        print(f"   - marketplace_products: {marketplace_total}개")
        
        # 공급사별 통계
        print("\n   도매처별 상품 수:")
        for supplier in ['zentrade', 'ownerclan', 'domeggook', 'domomae']:
            count = db.query(WholesaleProduct).filter(
                WholesaleProduct.supplier == supplier
            ).count()
            if count > 0:
                print(f"   - {supplier}: {count}개")
        
        print("\n   마켓플레이스별 상품 수:")
        for marketplace in ['coupang', 'naver', '11st']:
            count = db.query(MarketplaceProduct).filter(
                MarketplaceProduct.marketplace == marketplace
            ).count()
            if count > 0:
                print(f"   - {marketplace}: {count}개")
        
        print("\n마이그레이션 성공!")
        
    except Exception as e:
        db.rollback()
        print(f"\n마이그레이션 실패: {e}")
        raise
        
    finally:
        db.close()


def rollback_migration():
    """마이그레이션 롤백 (필요시)"""
    print("마이그레이션 롤백...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 새 테이블 삭제
            tables = [
                'stock_history',
                'price_history', 
                'product_mappings',
                'marketplace_products',
                'wholesale_products'
            ]
            
            for table in tables:
                if 'postgresql' in str(engine.url):
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                else:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"   - {table} 삭제됨")
            
            trans.commit()
            print("롤백 완료!")
            
        except Exception as e:
            trans.rollback()
            print(f"롤백 실패: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback_migration()
    else:
        migrate_to_v2()