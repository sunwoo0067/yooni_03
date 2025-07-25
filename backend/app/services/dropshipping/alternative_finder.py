"""
드롭쉬핑 대체 상품 추천 서비스

품절 시 유사한 상품을 자동으로 찾아 추천하여
매출 손실을 최소화하는 서비스
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.services.database.database import get_db


class AlternativeType(Enum):
    """대체 상품 유형"""
    SAME_SUPPLIER = "same_supplier"      # 동일 공급업체 다른 상품
    DIFFERENT_SUPPLIER = "different_supplier"  # 다른 공급업체 유사 상품
    HIGHER_PRICE = "higher_price"        # 상위 가격대
    LOWER_PRICE = "lower_price"          # 하위 가격대


@dataclass
class AlternativeProduct:
    """대체 상품 정보"""
    product_id: int
    name: str
    wholesaler_id: int
    wholesaler_name: str
    category: str
    wholesale_price: float
    selling_price: float
    current_stock: int
    similarity_score: float
    alternative_type: AlternativeType
    reliability_score: float
    profit_margin: float
    recommendation_reason: str


class AlternativeFinder:
    """대체 상품 찾기 서비스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.min_similarity_score = 0.6  # 최소 유사도 점수
        self.max_alternatives = 10       # 최대 추천 개수
        
    async def find_alternatives(self, 
                              category: str,
                              price_range: Tuple[float, float],
                              exclude_product_id: int,
                              original_product_name: Optional[str] = None) -> List[AlternativeProduct]:
        """대체 상품 찾기"""
        db = next(get_db())
        try:
            self.logger.info(f"대체 상품 검색 시작 - 카테고리: {category}, 가격대: {price_range}")
            
            alternatives = []
            
            # 1. 동일 카테고리 상품 검색
            category_alternatives = await self._find_by_category(
                db, category, price_range, exclude_product_id
            )
            alternatives.extend(category_alternatives)
            
            # 2. 유사 키워드 상품 검색
            if original_product_name:
                keyword_alternatives = await self._find_by_keywords(
                    db, original_product_name, price_range, exclude_product_id
                )
                alternatives.extend(keyword_alternatives)
            
            # 3. 가격대별 대안 검색
            price_alternatives = await self._find_by_extended_price_range(
                db, category, price_range, exclude_product_id
            )
            alternatives.extend(price_alternatives)
            
            # 중복 제거 및 점수 계산
            unique_alternatives = self._remove_duplicates(alternatives)
            scored_alternatives = await self._calculate_recommendation_scores(db, unique_alternatives)
            
            # 상위 추천 선별
            top_alternatives = sorted(
                scored_alternatives,
                key=lambda x: x.similarity_score,
                reverse=True
            )[:self.max_alternatives]
            
            self.logger.info(f"대체 상품 {len(top_alternatives)}개 발견")
            return top_alternatives
            
        finally:
            db.close()
            
    async def _find_by_category(self, 
                               db: Session,
                               category: str,
                               price_range: Tuple[float, float],
                               exclude_product_id: int) -> List[AlternativeProduct]:
        """카테고리별 대체 상품 검색"""
        from app.models.product import Product, ProductStatus
        from app.models.inventory import Inventory
        
        min_price, max_price = price_range
        
        # 동일 카테고리, 활성 상품, 재고 있는 상품
        products = db.query(Product).join(Inventory).filter(
            Product.category == category,
            Product.status == ProductStatus.ACTIVE,
            Product.id != exclude_product_id,
            Product.selling_price >= min_price,
            Product.selling_price <= max_price,
            Inventory.quantity > 0
        ).all()
        
        alternatives = []
        for product in products:
            alternative = await self._create_alternative_product(
                db, product, AlternativeType.SAME_SUPPLIER, 0.8
            )
            if alternative:
                alternatives.append(alternative)
                
        return alternatives
        
    async def _find_by_keywords(self,
                               db: Session,
                               product_name: str,
                               price_range: Tuple[float, float],
                               exclude_product_id: int) -> List[AlternativeProduct]:
        """키워드 기반 대체 상품 검색"""
        from app.models.product import Product, ProductStatus
        from app.models.inventory import Inventory
        
        # 상품명에서 핵심 키워드 추출
        keywords = self._extract_keywords(product_name)
        if not keywords:
            return []
            
        min_price, max_price = price_range
        
        # 키워드 매칭 상품 검색
        keyword_filters = []
        for keyword in keywords:
            keyword_filters.append(Product.name.ilike(f"%{keyword}%"))
            
        products = db.query(Product).join(Inventory).filter(
            or_(*keyword_filters),
            Product.status == ProductStatus.ACTIVE,
            Product.id != exclude_product_id,
            Product.selling_price >= min_price * 0.8,  # 가격 범위 확장
            Product.selling_price <= max_price * 1.2,
            Inventory.quantity > 0
        ).all()
        
        alternatives = []
        for product in products:
            # 키워드 유사도 계산
            similarity = self._calculate_keyword_similarity(product_name, product.name, keywords)
            if similarity >= self.min_similarity_score:
                alternative = await self._create_alternative_product(
                    db, product, AlternativeType.DIFFERENT_SUPPLIER, similarity
                )
                if alternative:
                    alternatives.append(alternative)
                    
        return alternatives
        
    async def _find_by_extended_price_range(self,
                                           db: Session,
                                           category: str,
                                           price_range: Tuple[float, float],
                                           exclude_product_id: int) -> List[AlternativeProduct]:
        """확장 가격대 대체 상품 검색"""
        from app.models.product import Product, ProductStatus
        from app.models.inventory import Inventory
        
        min_price, max_price = price_range
        
        # 상위 가격대 (20% 더 비싼)
        higher_price_products = db.query(Product).join(Inventory).filter(
            Product.category == category,
            Product.status == ProductStatus.ACTIVE,
            Product.id != exclude_product_id,
            Product.selling_price > max_price,
            Product.selling_price <= max_price * 1.2,
            Inventory.quantity > 0
        ).limit(3).all()
        
        # 하위 가격대 (20% 더 저렴한)
        lower_price_products = db.query(Product).join(Inventory).filter(
            Product.category == category,
            Product.status == ProductStatus.ACTIVE,
            Product.id != exclude_product_id,
            Product.selling_price < min_price,
            Product.selling_price >= min_price * 0.8,
            Inventory.quantity > 0
        ).limit(3).all()
        
        alternatives = []
        
        # 상위 가격대 상품 처리
        for product in higher_price_products:
            alternative = await self._create_alternative_product(
                db, product, AlternativeType.HIGHER_PRICE, 0.7
            )
            if alternative:
                alternatives.append(alternative)
                
        # 하위 가격대 상품 처리
        for product in lower_price_products:
            alternative = await self._create_alternative_product(
                db, product, AlternativeType.LOWER_PRICE, 0.6
            )
            if alternative:
                alternatives.append(alternative)
                
        return alternatives
        
    def _extract_keywords(self, product_name: str) -> List[str]:
        """상품명에서 핵심 키워드 추출"""
        # 불용어 제거 및 의미있는 키워드 추출
        stop_words = {'의', '이', '가', '을', '를', '은', '는', '으로', '와', '과', '도', '만', '부터', '까지'}
        
        # 특수문자 제거 및 단어 분할
        import re
        cleaned = re.sub(r'[^\w\s]', ' ', product_name)
        words = cleaned.split()
        
        # 불용어 제거 및 2글자 이상 단어만 선택
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words]
        
        return keywords[:5]  # 상위 5개 키워드만 사용
        
    def _calculate_keyword_similarity(self, original_name: str, target_name: str, keywords: List[str]) -> float:
        """키워드 기반 유사도 계산"""
        target_lower = target_name.lower()
        matched_keywords = 0
        
        for keyword in keywords:
            if keyword.lower() in target_lower:
                matched_keywords += 1
                
        return matched_keywords / len(keywords) if keywords else 0.0
        
    async def _create_alternative_product(self,
                                         db: Session,
                                         product,
                                         alternative_type: AlternativeType,
                                         base_similarity: float) -> Optional[AlternativeProduct]:
        """대체 상품 객체 생성"""
        try:
            # 공급업체 신뢰도 조회
            from app.models.dropshipping import SupplierReliability
            from app.models.wholesaler import Wholesaler
            
            reliability = db.query(SupplierReliability).filter(
                SupplierReliability.supplier_id == product.wholesaler_id
            ).first()
            
            wholesaler = db.query(Wholesaler).filter(
                Wholesaler.id == product.wholesaler_id
            ).first()
            
            reliability_score = reliability.reliability_score if reliability else 50.0
            wholesaler_name = wholesaler.name if wholesaler else "Unknown"
            
            # 재고 정보 조회
            from app.models.inventory import Inventory
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product.id
            ).first()
            
            current_stock = inventory.quantity if inventory else 0
            
            # 수익률 계산
            profit_margin = ((product.selling_price - product.wholesale_price) / product.selling_price) * 100
            
            # 추천 이유 생성
            recommendation_reason = self._generate_recommendation_reason(
                alternative_type, reliability_score, profit_margin, current_stock
            )
            
            return AlternativeProduct(
                product_id=product.id,
                name=product.name,
                wholesaler_id=product.wholesaler_id,
                wholesaler_name=wholesaler_name,
                category=product.category,
                wholesale_price=product.wholesale_price,
                selling_price=product.selling_price,
                current_stock=current_stock,
                similarity_score=base_similarity,
                alternative_type=alternative_type,
                reliability_score=reliability_score,
                profit_margin=profit_margin,
                recommendation_reason=recommendation_reason
            )
            
        except Exception as e:
            self.logger.error(f"대체 상품 생성 실패 - 상품 {product.id}: {e}")
            return None
            
    def _generate_recommendation_reason(self,
                                      alternative_type: AlternativeType,
                                      reliability_score: float,
                                      profit_margin: float,
                                      stock: int) -> str:
        """추천 이유 생성"""
        reasons = []
        
        if alternative_type == AlternativeType.SAME_SUPPLIER:
            reasons.append("동일 공급업체")
        elif alternative_type == AlternativeType.DIFFERENT_SUPPLIER:
            reasons.append("유사 상품")
        elif alternative_type == AlternativeType.HIGHER_PRICE:
            reasons.append("상위 가격대 대안")
        elif alternative_type == AlternativeType.LOWER_PRICE:
            reasons.append("하위 가격대 대안")
            
        if reliability_score >= 80:
            reasons.append("신뢰할 수 있는 공급업체")
        elif reliability_score >= 60:
            reasons.append("보통 신뢰도 공급업체")
            
        if stock >= 100:
            reasons.append("충분한 재고")
        elif stock >= 20:
            reasons.append("적정 재고")
            
        if profit_margin >= 30:
            reasons.append("높은 수익률")
        elif profit_margin >= 20:
            reasons.append("적정 수익률")
            
        return ", ".join(reasons)
        
    def _remove_duplicates(self, alternatives: List[AlternativeProduct]) -> List[AlternativeProduct]:
        """중복 상품 제거"""
        seen_ids = set()
        unique_alternatives = []
        
        for alternative in alternatives:
            if alternative.product_id not in seen_ids:
                seen_ids.add(alternative.product_id)
                unique_alternatives.append(alternative)
                
        return unique_alternatives
        
    async def _calculate_recommendation_scores(self,
                                             db: Session,
                                             alternatives: List[AlternativeProduct]) -> List[AlternativeProduct]:
        """추천 점수 재계산"""
        for alternative in alternatives:
            # 종합 점수 계산 (유사도 + 신뢰도 + 재고 + 수익률)
            stock_score = min(1.0, alternative.current_stock / 100)  # 재고 점수
            profit_score = min(1.0, alternative.profit_margin / 50)   # 수익률 점수
            reliability_score = alternative.reliability_score / 100   # 신뢰도 점수
            
            # 가중 평균으로 최종 점수 계산
            final_score = (
                alternative.similarity_score * 0.4 +
                reliability_score * 0.3 +
                stock_score * 0.2 +
                profit_score * 0.1
            )
            
            alternative.similarity_score = final_score
            
        return alternatives
        
    async def get_emergency_alternatives(self, 
                                       category: str,
                                       max_price: float,
                                       limit: int = 5) -> List[AlternativeProduct]:
        """긴급 대체 상품 추천 (빠른 재고 회전)"""
        db = next(get_db())
        try:
            from app.models.product import Product, ProductStatus
            from app.models.inventory import Inventory
            from app.models.dropshipping import SupplierReliability
            
            # 신뢰도 높고 재고 많은 상품 우선
            products = db.query(Product).join(Inventory).join(
                SupplierReliability, Product.wholesaler_id == SupplierReliability.supplier_id
            ).filter(
                Product.category == category,
                Product.status == ProductStatus.ACTIVE,
                Product.selling_price <= max_price,
                Inventory.quantity >= 50,  # 최소 50개 이상 재고
                SupplierReliability.reliability_score >= 70  # 신뢰도 70점 이상
            ).order_by(
                SupplierReliability.reliability_score.desc(),
                Inventory.quantity.desc()
            ).limit(limit).all()
            
            alternatives = []
            for product in products:
                alternative = await self._create_alternative_product(
                    db, product, AlternativeType.SAME_SUPPLIER, 0.9
                )
                if alternative:
                    alternatives.append(alternative)
                    
            return alternatives
            
        finally:
            db.close()
            
    async def suggest_cross_selling_alternatives(self,
                                               original_product_id: int,
                                               customer_purchase_history: List[int]) -> List[AlternativeProduct]:
        """크로스셀링 대체 상품 추천"""
        db = next(get_db())
        try:
            from app.models.product import Product
            from app.models.order import Order
            
            # 원본 상품과 함께 구매된 상품들 분석
            cross_sell_products = db.query(Product).join(Order).filter(
                Order.product_id.in_(customer_purchase_history),
                Product.id != original_product_id,
                Product.status == ProductStatus.ACTIVE
            ).group_by(Product.id).order_by(
                func.count(Order.id).desc()
            ).limit(5).all()
            
            alternatives = []
            for product in cross_sell_products:
                alternative = await self._create_alternative_product(
                    db, product, AlternativeType.DIFFERENT_SUPPLIER, 0.85
                )
                if alternative:
                    alternative.recommendation_reason += ", 고객 구매 패턴 기반"
                    alternatives.append(alternative)
                    
            return alternatives
            
        finally:
            db.close()
            
    async def get_seasonal_alternatives(self,
                                      category: str,
                                      season: str) -> List[AlternativeProduct]:
        """계절별 대체 상품 추천"""
        db = next(get_db())
        try:
            # 계절별 키워드 매핑
            seasonal_keywords = {
                'spring': ['봄', '새싹', '꽃', '파스텔'],
                'summer': ['여름', '시원', '수영', '바캉스', '휴가'],
                'autumn': ['가을', '단풍', '추수', '따뜻한'],
                'winter': ['겨울', '따뜻한', '크리스마스', '눈', '방한']
            }
            
            keywords = seasonal_keywords.get(season.lower(), [])
            if not keywords:
                return []
                
            from app.models.product import Product, ProductStatus
            from app.models.inventory import Inventory
            
            # 계절 키워드가 포함된 상품 검색
            keyword_filters = []
            for keyword in keywords:
                keyword_filters.append(Product.name.ilike(f"%{keyword}%"))
                keyword_filters.append(Product.description.ilike(f"%{keyword}%"))
                
            products = db.query(Product).join(Inventory).filter(
                Product.category == category,
                Product.status == ProductStatus.ACTIVE,
                or_(*keyword_filters),
                Inventory.quantity > 0
            ).limit(10).all()
            
            alternatives = []
            for product in products:
                alternative = await self._create_alternative_product(
                    db, product, AlternativeType.DIFFERENT_SUPPLIER, 0.75
                )
                if alternative:
                    alternative.recommendation_reason += f", {season} 시즌 상품"
                    alternatives.append(alternative)
                    
            return alternatives
            
        finally:
            db.close()