"""
최적화된 상품 CRUD - N+1 쿼리 해결 및 성능 개선
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session, selectinload, joinedload, subqueryload
from sqlalchemy import func, and_, or_, text
from sqlalchemy.orm import aliased

from ..models.product import Product, ProductCategory, ProductVariant, ProductImage
from ..schemas.product import ProductCreate, ProductUpdate
from ..core.cache import cache_result, invalidate_cache
from .base import CRUDBase


class CRUDProductOptimized(CRUDBase[Product, ProductCreate, ProductUpdate]):
    """최적화된 상품 CRUD 작업"""
    
    @cache_result(prefix="products", ttl=300)
    async def get_multi_with_relations(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        platform_account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = False
    ) -> Tuple[List[Product], int]:
        """
        관계 데이터를 포함한 상품 목록 조회 (N+1 쿼리 해결)
        """
        # Eager loading으로 관련 데이터 한번에 로드
        query = db.query(Product).options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.platform_listings),
            joinedload(Product.category),  # 카테고리는 보통 1:1이므로 joinedload
            subqueryload(Product.price_history).limit(10)  # 최근 10개만
        )
        
        # 필터 적용
        if platform_account_id:
            query = query.filter(Product.platform_account_id == platform_account_id)
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        if search:
            # 인덱스가 있는 필드부터 검색
            query = query.filter(
                or_(
                    Product.sku.ilike(f"%{search}%"),
                    Product.name.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%")
                )
            )
        
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        
        if in_stock_only:
            query = query.filter(Product.stock_quantity > 0)
        
        # 효율적인 카운트 (서브쿼리 사용)
        count_query = query.statement.compile(compile_kwargs={"literal_binds": True})
        total = db.execute(
            text(f"SELECT COUNT(*) FROM ({count_query}) as count_query")
        ).scalar()
        
        # 페이지네이션
        products = query.offset(skip).limit(limit).all()
        
        return products, total
    
    def get_category_path_optimized(self, db: Session, category_id: UUID) -> str:
        """
        재귀 CTE를 사용한 카테고리 경로 조회 (N+1 쿼리 해결)
        """
        # PostgreSQL용 재귀 CTE
        if db.bind.dialect.name == 'postgresql':
            query = text("""
                WITH RECURSIVE category_path AS (
                    SELECT id, name, parent_id, 0 as level
                    FROM product_categories
                    WHERE id = :category_id
                    
                    UNION ALL
                    
                    SELECT c.id, c.name, c.parent_id, cp.level + 1
                    FROM product_categories c
                    INNER JOIN category_path cp ON c.id = cp.parent_id
                )
                SELECT name FROM category_path
                ORDER BY level DESC
            """)
            
            result = db.execute(query, {"category_id": str(category_id)})
            categories = [row[0] for row in result]
            return " > ".join(categories)
        
        # SQLite나 다른 DB용 대체 구현
        else:
            path = []
            current = db.query(ProductCategory).filter(
                ProductCategory.id == category_id
            ).first()
            
            while current:
                path.append(current.name)
                if current.parent_id:
                    current = db.query(ProductCategory).filter(
                        ProductCategory.id == current.parent_id
                    ).first()
                else:
                    break
            
            return " > ".join(reversed(path))
    
    @invalidate_cache(pattern="products:*")
    async def bulk_create_optimized(
        self,
        db: Session,
        *,
        products: List[ProductCreate]
    ) -> List[Product]:
        """
        최적화된 대량 상품 생성
        """
        # 1. 모든 SKU를 한번에 체크
        skus = [p.sku for p in products]
        existing_skus = set(
            db.query(Product.sku)
            .filter(Product.sku.in_(skus))
            .scalar_all()
        )
        
        # 2. 중복되지 않는 상품만 필터링
        new_products = [
            p for p in products 
            if p.sku not in existing_skus
        ]
        
        if not new_products:
            return []
        
        # 3. bulk_insert_mappings 사용
        product_dicts = []
        for product_data in new_products:
            product_dict = product_data.dict()
            # 관계 데이터는 별도 처리
            product_dict.pop('variants', None)
            product_dict.pop('images', None)
            product_dicts.append(product_dict)
        
        db.bulk_insert_mappings(Product, product_dicts)
        db.flush()
        
        # 4. 생성된 상품 조회 (관계 데이터 포함)
        created_products = db.query(Product).filter(
            Product.sku.in_([p.sku for p in new_products])
        ).options(
            selectinload(Product.variants),
            selectinload(Product.images)
        ).all()
        
        # 5. 관계 데이터 일괄 처리
        variants_to_create = []
        images_to_create = []
        
        for i, product in enumerate(created_products):
            product_data = new_products[i]
            
            # Variants
            if hasattr(product_data, 'variants'):
                for variant_data in product_data.variants:
                    variant_dict = variant_data.dict()
                    variant_dict['product_id'] = product.id
                    variants_to_create.append(variant_dict)
            
            # Images
            if hasattr(product_data, 'images'):
                for image_data in product_data.images:
                    image_dict = image_data.dict()
                    image_dict['product_id'] = product.id
                    images_to_create.append(image_dict)
        
        # 일괄 삽입
        if variants_to_create:
            db.bulk_insert_mappings(ProductVariant, variants_to_create)
        
        if images_to_create:
            db.bulk_insert_mappings(ProductImage, images_to_create)
        
        db.commit()
        
        return created_products
    
    async def get_products_stream(
        self,
        db: Session,
        filters: Dict[str, Any],
        batch_size: int = 100
    ):
        """
        대용량 데이터를 위한 스트리밍 조회
        """
        query = db.query(Product)
        
        # 필터 적용
        if filters.get('platform_account_id'):
            query = query.filter(
                Product.platform_account_id == filters['platform_account_id']
            )
        
        if filters.get('category_id'):
            query = query.filter(Product.category_id == filters['category_id'])
        
        # yield_per를 사용한 메모리 효율적인 조회
        for product in query.yield_per(batch_size):
            yield product
    
    def get_approximate_count(self, db: Session) -> int:
        """
        대용량 테이블을 위한 근사치 카운트
        """
        if db.bind.dialect.name == 'postgresql':
            # PostgreSQL의 통계 정보 활용
            result = db.execute(
                text("""
                    SELECT reltuples::BIGINT 
                    FROM pg_class 
                    WHERE relname = 'products'
                """)
            ).scalar()
            return int(result) if result else 0
        else:
            # 다른 DB는 일반 카운트 (캐싱됨)
            return db.query(func.count(Product.id)).scalar()


# 싱글톤 인스턴스
crud_product_optimized = CRUDProductOptimized(Product)