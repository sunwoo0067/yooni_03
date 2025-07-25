"""
벤치마크 데이터 관리 서비스
모든 마켓 데이터를 중앙에서 관리
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from app.models.benchmark import (
    BenchmarkProduct, BenchmarkPriceHistory, BenchmarkKeyword,
    BenchmarkReview, BenchmarkCompetitor, BenchmarkMarketTrend
)


class BenchmarkManager:
    """벤치마크 데이터 통합 관리"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    async def save_product_data(self, product_data: Dict[str, Any], market_type: str) -> BenchmarkProduct:
        """상품 데이터 저장"""
        try:
            # 기존 상품 확인
            existing = self.db.query(BenchmarkProduct).filter(
                and_(
                    BenchmarkProduct.market_product_id == product_data['product_id'],
                    BenchmarkProduct.market_type == market_type
                )
            ).first()
            
            if existing:
                # 업데이트
                for key, value in product_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
            else:
                # 신규 생성
                product = BenchmarkProduct(
                    market_product_id=product_data['product_id'],
                    market_type=market_type,
                    product_name=product_data.get('name'),
                    brand=product_data.get('brand'),
                    category_path=product_data.get('category_path'),
                    main_category=product_data.get('main_category'),
                    sub_category=product_data.get('sub_category'),
                    original_price=product_data.get('original_price'),
                    sale_price=product_data.get('sale_price'),
                    discount_rate=product_data.get('discount_rate'),
                    delivery_fee=product_data.get('delivery_fee'),
                    monthly_sales=product_data.get('monthly_sales'),
                    review_count=product_data.get('review_count'),
                    rating=product_data.get('rating'),
                    bestseller_rank=product_data.get('bestseller_rank'),
                    category_rank=product_data.get('category_rank'),
                    seller_name=product_data.get('seller_name'),
                    seller_grade=product_data.get('seller_grade'),
                    is_power_seller=product_data.get('is_power_seller', False),
                    options=product_data.get('options'),
                    keywords=product_data.get('keywords'),
                    attributes=product_data.get('attributes')
                )
                self.db.add(product)
                existing = product
            
            # 가격 이력 저장
            await self._save_price_history(product_data, market_type)
            
            self.db.commit()
            return existing
            
        except Exception as e:
            self.logger.error(f"상품 데이터 저장 실패: {str(e)}")
            self.db.rollback()
            raise
    
    async def _save_price_history(self, product_data: Dict[str, Any], market_type: str):
        """가격 변동 이력 저장"""
        price_history = BenchmarkPriceHistory(
            market_product_id=product_data['product_id'],
            market_type=market_type,
            original_price=product_data.get('original_price'),
            sale_price=product_data.get('sale_price'),
            discount_rate=product_data.get('discount_rate')
        )
        self.db.add(price_history)
    
    async def get_category_bestsellers(
        self, 
        category: str, 
        market_type: Optional[str] = None,
        limit: int = 100
    ) -> List[BenchmarkProduct]:
        """카테고리별 베스트셀러 조회"""
        query = self.db.query(BenchmarkProduct).filter(
            BenchmarkProduct.main_category == category
        )
        
        if market_type:
            query = query.filter(BenchmarkProduct.market_type == market_type)
        
        return query.order_by(
            BenchmarkProduct.bestseller_rank.asc()
        ).limit(limit).all()
    
    async def get_price_trends(
        self, 
        product_id: str, 
        market_type: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """가격 트렌드 조회"""
        since = datetime.utcnow() - timedelta(days=days)
        
        history = self.db.query(BenchmarkPriceHistory).filter(
            and_(
                BenchmarkPriceHistory.market_product_id == product_id,
                BenchmarkPriceHistory.market_type == market_type,
                BenchmarkPriceHistory.recorded_at >= since
            )
        ).order_by(BenchmarkPriceHistory.recorded_at).all()
        
        return [
            {
                'date': h.recorded_at,
                'original_price': h.original_price,
                'sale_price': h.sale_price,
                'discount_rate': h.discount_rate
            }
            for h in history
        ]
    
    async def find_similar_products(
        self,
        product_name: str,
        category: Optional[str] = None,
        price_range: Optional[tuple] = None
    ) -> List[BenchmarkProduct]:
        """유사 상품 검색"""
        query = self.db.query(BenchmarkProduct)
        
        # 이름으로 검색
        search_terms = product_name.split()
        for term in search_terms:
            query = query.filter(BenchmarkProduct.product_name.contains(term))
        
        # 카테고리 필터
        if category:
            query = query.filter(BenchmarkProduct.main_category == category)
        
        # 가격 범위 필터
        if price_range:
            query = query.filter(
                and_(
                    BenchmarkProduct.sale_price >= price_range[0],
                    BenchmarkProduct.sale_price <= price_range[1]
                )
            )
        
        return query.order_by(BenchmarkProduct.monthly_sales.desc()).limit(50).all()
    
    async def get_market_insights(self, category: str) -> Dict[str, Any]:
        """시장 인사이트 조회"""
        # 평균 가격
        avg_price = self.db.query(func.avg(BenchmarkProduct.sale_price)).filter(
            BenchmarkProduct.main_category == category
        ).scalar() or 0
        
        # 상위 브랜드
        top_brands = self.db.query(
            BenchmarkProduct.brand,
            func.count(BenchmarkProduct.id).label('count')
        ).filter(
            BenchmarkProduct.main_category == category
        ).group_by(
            BenchmarkProduct.brand
        ).order_by(
            func.count(BenchmarkProduct.id).desc()
        ).limit(10).all()
        
        # 가격 분포
        price_distribution = self.db.query(
            func.count(BenchmarkProduct.id).label('count'),
            func.min(BenchmarkProduct.sale_price).label('min_price'),
            func.max(BenchmarkProduct.sale_price).label('max_price')
        ).filter(
            BenchmarkProduct.main_category == category
        ).first()
        
        return {
            'average_price': int(avg_price),
            'top_brands': [
                {'brand': b[0], 'product_count': b[1]} 
                for b in top_brands if b[0]
            ],
            'price_range': {
                'min': price_distribution.min_price if price_distribution else 0,
                'max': price_distribution.max_price if price_distribution else 0
            },
            'total_products': price_distribution.count if price_distribution else 0
        }
    
    async def update_keyword_trend(self, keyword_data: Dict[str, Any]):
        """키워드 트렌드 업데이트"""
        keyword = self.db.query(BenchmarkKeyword).filter(
            BenchmarkKeyword.keyword == keyword_data['keyword']
        ).first()
        
        if keyword:
            for key, value in keyword_data.items():
                if hasattr(keyword, key):
                    setattr(keyword, key, value)
        else:
            keyword = BenchmarkKeyword(**keyword_data)
            self.db.add(keyword)
        
        self.db.commit()
    
    async def get_competitor_analysis(self, competitor_name: str) -> Optional[BenchmarkCompetitor]:
        """경쟁사 분석 데이터 조회"""
        return self.db.query(BenchmarkCompetitor).filter(
            BenchmarkCompetitor.competitor_name == competitor_name
        ).first()
    
    async def get_trending_products(
        self,
        days: int = 7,
        min_growth_rate: float = 20.0
    ) -> List[Dict[str, Any]]:
        """급상승 상품 조회"""
        # 최근 판매량과 이전 판매량 비교
        recent_date = datetime.utcnow() - timedelta(days=days)
        
        trending = self.db.query(
            BenchmarkProduct,
            func.count(BenchmarkPriceHistory.id).label('price_changes')
        ).join(
            BenchmarkPriceHistory,
            BenchmarkProduct.market_product_id == BenchmarkPriceHistory.market_product_id
        ).filter(
            BenchmarkPriceHistory.recorded_at >= recent_date
        ).group_by(
            BenchmarkProduct.id
        ).having(
            func.count(BenchmarkPriceHistory.id) > 3  # 가격 변동이 잦은 상품
        ).order_by(
            BenchmarkProduct.monthly_sales.desc()
        ).limit(100).all()
        
        return [
            {
                'product': product,
                'price_volatility': price_changes
            }
            for product, price_changes in trending
        ]