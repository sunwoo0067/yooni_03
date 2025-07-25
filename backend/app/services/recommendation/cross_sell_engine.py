"""
교차 판매 엔진
상품 간 연관성 분석을 통한 교차 판매 및 업셀링 추천
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from collections import defaultdict, Counter
import itertools

from ...models.order import Order
from ...models.product import Product
from ...models.crm import Customer


class CrossSellEngine:
    """교차 판매를 위한 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 연관 규칙 최소 지지도 및 신뢰도
        self.min_support = 0.01  # 1%
        self.min_confidence = 0.1  # 10%
    
    def analyze_market_basket(self, days: int = 90) -> Dict:
        """장바구니 분석 수행"""
        start_date = datetime.now() - timedelta(days=days)
        
        # 동일 주문 내 상품 조합 분석
        orders = self.db.query(Order).filter(
            and_(
                Order.order_date >= start_date,
                Order.order_status != 'cancelled'
            )
        ).all()
        
        # 주문별 상품 그룹핑
        order_products = defaultdict(list)
        for order in orders:
            order_products[order.order_id].append(order.product_id)
        
        # 상품 조합 빈도 계산
        product_combinations = Counter()
        single_products = Counter()
        
        for products in order_products.values():
            if len(products) > 1:
                # 2개 상품 조합
                for combo in itertools.combinations(products, 2):
                    product_combinations[combo] += 1
            
            # 개별 상품 빈도
            for product in products:
                single_products[product] += 1
        
        total_orders = len(order_products)
        
        # 연관 규칙 생성
        association_rules = []
        
        for (product_a, product_b), combo_count in product_combinations.items():
            support = combo_count / total_orders
            
            if support >= self.min_support:
                # A -> B 규칙
                confidence_a_to_b = combo_count / single_products[product_a]
                lift_a_to_b = confidence_a_to_b / (single_products[product_b] / total_orders)
                
                if confidence_a_to_b >= self.min_confidence:
                    association_rules.append({
                        "antecedent": product_a,
                        "consequent": product_b,
                        "support": round(support, 4),
                        "confidence": round(confidence_a_to_b, 4),
                        "lift": round(lift_a_to_b, 4),
                        "transaction_count": combo_count
                    })
                
                # B -> A 규칙
                confidence_b_to_a = combo_count / single_products[product_b]
                lift_b_to_a = confidence_b_to_a / (single_products[product_a] / total_orders)
                
                if confidence_b_to_a >= self.min_confidence:
                    association_rules.append({
                        "antecedent": product_b,
                        "consequent": product_a,
                        "support": round(support, 4),
                        "confidence": round(confidence_b_to_a, 4),
                        "lift": round(lift_b_to_a, 4),
                        "transaction_count": combo_count
                    })
        
        # Lift 기준 정렬
        association_rules.sort(key=lambda x: x["lift"], reverse=True)
        
        return {
            "analysis_period_days": days,
            "total_orders": total_orders,
            "total_combinations": len(product_combinations),
            "association_rules": association_rules[:50],  # 상위 50개
            "analysis_date": datetime.now().isoformat()
        }
    
    def get_cross_sell_recommendations(self, product_ids: List[str], 
                                     limit: int = 10) -> Dict:
        """특정 상품들에 대한 교차 판매 추천"""
        if not product_ids:
            return {"error": "상품 ID가 필요합니다."}
        
        # 연관 규칙 분석
        market_basket = self.analyze_market_basket()
        rules = market_basket["association_rules"]
        
        # 입력 상품들과 연관된 추천 상품 찾기
        recommendations = defaultdict(lambda: {"score": 0, "rules": []})
        
        for rule in rules:
            if rule["antecedent"] in product_ids:
                consequent = rule["consequent"]
                if consequent not in product_ids:  # 이미 선택된 상품 제외
                    score = rule["confidence"] * rule["lift"]
                    recommendations[consequent]["score"] += score
                    recommendations[consequent]["rules"].append(rule)
        
        # 점수 기준 정렬
        sorted_recs = sorted(
            recommendations.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        # 상품 정보 추가
        final_recommendations = []
        for product_id, data in sorted_recs[:limit]:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if product:
                final_recommendations.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": product.category,
                    "price": product.price,
                    "cross_sell_score": round(data["score"], 4),
                    "supporting_rules": data["rules"][:3]  # 상위 3개 규칙
                })
        
        return {
            "input_products": product_ids,
            "recommendations": final_recommendations,
            "total_recommendations": len(final_recommendations),
            "generated_at": datetime.now().isoformat()
        }
    
    def get_upsell_opportunities(self, customer_id: int, limit: int = 10) -> Dict:
        """업셀링 기회 분석"""
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        # 고객의 구매 이력
        customer_orders = self.db.query(Order).join(Product).filter(
            and_(
                Order.customer_id == customer_id,
                Order.order_status != 'cancelled'
            )
        ).all()
        
        if not customer_orders:
            return {"error": "구매 이력이 없습니다."}
        
        # 구매한 상품들의 카테고리별 최고가
        category_max_prices = defaultdict(float)
        purchased_products = []
        
        for order in customer_orders:
            product = self.db.query(Product).filter(Product.id == order.product_id).first()
            if product and product.price:
                category_max_prices[product.category] = max(
                    category_max_prices[product.category],
                    product.price
                )
                purchased_products.append(product)
        
        # 업셀링 추천
        upsell_opportunities = []
        
        for category, max_price in category_max_prices.items():
            # 해당 카테고리에서 더 비싼 상품들
            higher_priced_products = self.db.query(Product).filter(
                and_(
                    Product.category == category,
                    Product.price > max_price,
                    Product.is_active == True
                )
            ).order_by(Product.price).limit(5).all()
            
            for product in higher_priced_products:
                price_increase = product.price - max_price
                price_increase_percent = (price_increase / max_price) * 100
                
                upsell_opportunities.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": category,
                    "current_price": product.price,
                    "customer_max_price_in_category": max_price,
                    "price_increase": price_increase,
                    "price_increase_percent": round(price_increase_percent, 2),
                    "upsell_score": self._calculate_upsell_score(
                        price_increase_percent, product
                    )
                })
        
        # 업셀 점수 기준 정렬
        upsell_opportunities.sort(key=lambda x: x["upsell_score"], reverse=True)
        
        return {
            "customer_id": customer_id,
            "upsell_opportunities": upsell_opportunities[:limit],
            "analysis_date": datetime.now().isoformat()
        }
    
    def _calculate_upsell_score(self, price_increase_percent: float, product: Product) -> float:
        """업셀 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 가격 증가율에 따른 점수 (적당한 증가가 좋음)
        if 20 <= price_increase_percent <= 50:
            score += 0.3
        elif 10 <= price_increase_percent <= 80:
            score += 0.2
        elif price_increase_percent > 100:
            score -= 0.2
        
        # 상품 인기도
        if product.sales_count:
            popularity_score = min(product.sales_count / 100, 0.2)
            score += popularity_score
        
        # 평점
        if product.rating:
            rating_score = (product.rating / 5.0) * 0.2
            score += rating_score
        
        return round(score, 3)