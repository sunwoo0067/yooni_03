"""
상품 추천 엔진
사용자 구매 이력, 상품 유사도, 인기도 기반 추천 시스템
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import numpy as np

from app.models.product import Product
from app.models.order_core import Order, OrderItem
from app.models.user import User
from app.core.exceptions import AppException


class RecommendationEngine:
    """상품 추천 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def get_user_recommendations(
        self, 
        user_id: int, 
        limit: int = 10,
        exclude_purchased: bool = True
    ) -> List[Dict[str, Any]]:
        """
        사용자별 개인화된 추천 상품 조회
        
        Args:
            user_id: 사용자 ID
            limit: 추천 상품 수
            exclude_purchased: 이미 구매한 상품 제외 여부
            
        Returns:
            추천 상품 리스트
        """
        recommendations = []
        
        # 1. 구매 이력 기반 추천
        history_based = self._get_purchase_history_recommendations(
            user_id, limit=limit*2, exclude_purchased=exclude_purchased
        )
        recommendations.extend(history_based)
        
        # 2. 협업 필터링 기반 추천 (유사 사용자)
        collaborative = self._get_collaborative_recommendations(
            user_id, limit=limit, exclude_purchased=exclude_purchased
        )
        recommendations.extend(collaborative)
        
        # 3. 인기 상품 추천
        popular = self._get_popular_recommendations(
            limit=limit//2, exclude_user_id=user_id if exclude_purchased else None
        )
        recommendations.extend(popular)
        
        # 중복 제거 및 점수 기준 정렬
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec['product_id'] not in seen:
                seen.add(rec['product_id'])
                unique_recommendations.append(rec)
                
        # 점수 기준으로 정렬하여 상위 N개 반환
        unique_recommendations.sort(key=lambda x: x['score'], reverse=True)
        return unique_recommendations[:limit]
        
    def _get_purchase_history_recommendations(
        self, 
        user_id: int, 
        limit: int = 20,
        exclude_purchased: bool = True
    ) -> List[Dict[str, Any]]:
        """구매 이력 기반 추천"""
        # 사용자의 최근 구매 상품 조회
        recent_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.status == 'completed'
        ).order_by(desc(Order.created_at)).limit(10).all()
        
        if not recent_orders:
            return []
            
        # 구매한 상품의 카테고리와 브랜드 수집
        purchased_products = []
        category_count = defaultdict(int)
        brand_count = defaultdict(int)
        
        for order in recent_orders:
            for item in order.items:
                purchased_products.append(item.product_id)
                if item.product.category:
                    category_count[item.product.category] += item.quantity
                if hasattr(item.product, 'brand') and item.product.brand:
                    brand_count[item.product.brand] += item.quantity
                    
        # 선호 카테고리와 브랜드 추출
        top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:3]
        top_brands = sorted(brand_count.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # 유사 상품 검색
        query = self.db.query(Product).filter(
            Product.is_active == True,
            Product.stock > 0
        )
        
        if exclude_purchased:
            query = query.filter(~Product.id.in_(purchased_products))
            
        # 카테고리 또는 브랜드가 일치하는 상품 우선
        category_names = [cat[0] for cat in top_categories]
        brand_names = [brand[0] for brand in top_brands]
        
        recommendations = []
        
        # 카테고리 기반 추천
        if category_names:
            category_products = query.filter(
                Product.category.in_(category_names)
            ).order_by(desc(Product.created_at)).limit(limit).all()
            
            for product in category_products:
                score = 0.7  # 기본 점수
                # 카테고리 가중치 적용
                if product.category in category_names:
                    idx = category_names.index(product.category)
                    score += (0.3 * (1 - idx * 0.1))  # 상위 카테고리일수록 높은 점수
                    
                recommendations.append({
                    'product_id': product.id,
                    'product': product,
                    'score': score,
                    'reason': f'{product.category} 카테고리 상품'
                })
                
        return recommendations
        
    def _get_collaborative_recommendations(
        self, 
        user_id: int, 
        limit: int = 10,
        exclude_purchased: bool = True
    ) -> List[Dict[str, Any]]:
        """협업 필터링 기반 추천 (유사 사용자의 구매 패턴)"""
        # 현재 사용자의 구매 상품
        user_products = self.db.query(OrderItem.product_id).join(Order).filter(
            Order.user_id == user_id,
            Order.status == 'completed'
        ).distinct().all()
        
        if not user_products:
            return []
            
        user_product_ids = [p[0] for p in user_products]
        
        # 동일한 상품을 구매한 다른 사용자 찾기
        similar_users = self.db.query(
            Order.user_id,
            func.count(OrderItem.product_id).label('common_products')
        ).join(OrderItem).filter(
            OrderItem.product_id.in_(user_product_ids),
            Order.user_id != user_id,
            Order.status == 'completed'
        ).group_by(Order.user_id).order_by(
            desc('common_products')
        ).limit(20).all()
        
        if not similar_users:
            return []
            
        similar_user_ids = [u[0] for u in similar_users[:10]]
        
        # 유사 사용자들이 구매한 상품 중 현재 사용자가 구매하지 않은 상품
        query = self.db.query(
            OrderItem.product_id,
            func.count(OrderItem.product_id).label('purchase_count'),
            Product
        ).join(Order).join(Product).filter(
            Order.user_id.in_(similar_user_ids),
            Order.status == 'completed',
            Product.is_active == True,
            Product.stock > 0
        )
        
        if exclude_purchased:
            query = query.filter(~OrderItem.product_id.in_(user_product_ids))
            
        recommended_products = query.group_by(
            OrderItem.product_id, Product.id
        ).order_by(desc('purchase_count')).limit(limit).all()
        
        recommendations = []
        for product_id, count, product in recommended_products:
            score = min(0.9, 0.5 + (count * 0.1))  # 구매 횟수에 따른 점수
            recommendations.append({
                'product_id': product_id,
                'product': product,
                'score': score,
                'reason': f'{count}명의 유사 고객이 구매'
            })
            
        return recommendations
        
    def _get_popular_recommendations(
        self, 
        limit: int = 5,
        days: int = 30,
        exclude_user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """인기 상품 추천"""
        # 최근 N일간 가장 많이 팔린 상품
        since_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.count(distinct(Order.user_id)).label('unique_buyers'),
            Product
        ).join(Order).join(Product).filter(
            Order.created_at >= since_date,
            Order.status == 'completed',
            Product.is_active == True,
            Product.stock > 0
        )
        
        if exclude_user_id:
            # 사용자가 이미 구매한 상품 제외
            user_products = self.db.query(OrderItem.product_id).join(Order).filter(
                Order.user_id == exclude_user_id,
                Order.status == 'completed'
            ).subquery()
            query = query.filter(~OrderItem.product_id.in_(user_products))
            
        popular_products = query.group_by(
            OrderItem.product_id, Product.id
        ).order_by(desc('total_quantity')).limit(limit).all()
        
        recommendations = []
        for product_id, quantity, buyers, product in popular_products:
            score = min(0.8, 0.4 + (buyers * 0.01))  # 구매자 수에 따른 점수
            recommendations.append({
                'product_id': product_id,
                'product': product,
                'score': score,
                'reason': f'최근 {buyers}명이 구매한 인기 상품'
            })
            
        return recommendations
        
    def get_product_similarities(
        self, 
        product_id: int, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """특정 상품과 유사한 상품 추천"""
        # 기준 상품 조회
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise AppException("상품을 찾을 수 없습니다", status_code=404)
            
        # 같은 카테고리의 상품
        similar_products = self.db.query(Product).filter(
            Product.category == product.category,
            Product.id != product_id,
            Product.is_active == True,
            Product.stock > 0
        ).all()
        
        if not similar_products:
            return []
            
        # 유사도 계산 (가격, 특성 기반)
        recommendations = []
        for similar in similar_products:
            # 가격 유사도 (0~1)
            price_diff = abs(product.price - similar.price) / max(product.price, similar.price)
            price_similarity = 1 - min(price_diff, 1)
            
            # 이름 유사도 (간단한 방식)
            name_similarity = self._calculate_name_similarity(product.name, similar.name)
            
            # 전체 유사도 점수
            score = (price_similarity * 0.4) + (name_similarity * 0.3) + 0.3
            
            recommendations.append({
                'product_id': similar.id,
                'product': similar,
                'score': score,
                'reason': '유사 상품'
            })
            
        # 점수 기준 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
        
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """상품명 유사도 계산 (간단한 버전)"""
        # 공통 단어 비율로 유사도 계산
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        return len(common_words) / len(total_words)
        
    def get_bundle_recommendations(
        self, 
        product_ids: List[int], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """함께 구매하면 좋은 상품 추천 (장바구니 기반)"""
        # 해당 상품들과 함께 구매된 상품 조회
        co_purchased = self.db.query(
            OrderItem.product_id,
            func.count(OrderItem.product_id).label('co_purchase_count'),
            Product
        ).join(Order).join(Product).filter(
            Order.id.in_(
                self.db.query(Order.id).join(OrderItem).filter(
                    OrderItem.product_id.in_(product_ids),
                    Order.status == 'completed'
                )
            ),
            ~OrderItem.product_id.in_(product_ids),
            Product.is_active == True,
            Product.stock > 0
        ).group_by(
            OrderItem.product_id, Product.id
        ).order_by(desc('co_purchase_count')).limit(limit).all()
        
        recommendations = []
        for product_id, count, product in co_purchased:
            score = min(0.9, 0.5 + (count * 0.05))
            recommendations.append({
                'product_id': product_id,
                'product': product,
                'score': score,
                'reason': f'{count}번 함께 구매됨'
            })
            
        return recommendations