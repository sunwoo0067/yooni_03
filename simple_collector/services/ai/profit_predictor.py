"""
수익성 예측 모델
- 마진율 계산
- 판매 예측
- 수익성 점수 산출
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from database.models_v2 import WholesaleProduct, MarketplaceProduct
from collectors.bestseller_collector import BestsellerData
from utils.logger import app_logger


class ProfitPredictor:
    """수익성 예측기"""
    
    def __init__(self, db: Session):
        self.db = db
        # 기본 마진율 설정 (사용자 요구사항: 최소 20%)
        self.min_margin_rate = 0.20
        # 카테고리별 가중치
        self.category_weights = {
            '전자제품': 0.15,
            '패션의류': 0.25,
            '생활용품': 0.20,
            '식품': 0.30,
            '화장품': 0.25,
            '스포츠': 0.20
        }
        # 가격대별 마진율
        self.price_margins = {
            (0, 10000): 0.30,
            (10000, 30000): 0.25,
            (30000, 50000): 0.20,
            (50000, 100000): 0.18,
            (100000, float('inf')): 0.15
        }
    
    def calculate_profit_potential(self, wholesale_product: WholesaleProduct, 
                                 marketplace: str = 'coupang') -> Dict[str, Any]:
        """상품의 수익성 잠재력 계산"""
        try:
            # 도매가
            wholesale_price = wholesale_product.wholesale_price
            
            # 카테고리별 마진율 결정
            category = wholesale_product.category or '기타'
            base_margin = self.category_weights.get(category, 0.20)
            
            # 가격대별 마진율 조정
            price_margin = self._get_price_margin(wholesale_price)
            final_margin = max(base_margin, price_margin, self.min_margin_rate)
            
            # 예상 판매가 계산
            selling_price = int(wholesale_price * (1 + final_margin))
            
            # 마켓플레이스 수수료 (쿠팡 기준 약 10%)
            marketplace_fee = selling_price * 0.10
            
            # 배송비 고려
            shipping_cost = self._estimate_shipping_cost(wholesale_product)
            
            # 순수익 계산
            net_profit = selling_price - wholesale_price - marketplace_fee - shipping_cost
            net_margin = net_profit / selling_price if selling_price > 0 else 0
            
            # 경쟁 상품 분석
            competition = self._analyze_competition(
                category=category,
                price_range=(selling_price * 0.8, selling_price * 1.2),
                marketplace=marketplace
            )
            
            # 판매 예측
            sales_forecast = self._predict_sales(
                category=category,
                price=selling_price,
                competition=competition
            )
            
            # 수익성 점수 계산
            profit_score = self._calculate_profit_score(
                net_margin=net_margin,
                sales_forecast=sales_forecast,
                competition=competition
            )
            
            return {
                'wholesale_price': wholesale_price,
                'recommended_price': selling_price,
                'margin_rate': round(final_margin, 3),
                'marketplace_fee': round(marketplace_fee),
                'shipping_cost': shipping_cost,
                'net_profit': round(net_profit),
                'net_margin': round(net_margin, 3),
                'monthly_revenue_forecast': sales_forecast['monthly_revenue'],
                'monthly_profit_forecast': round(net_profit * sales_forecast['monthly_units']),
                'competition_level': competition['level'],
                'profit_score': profit_score,
                'recommendation': self._get_recommendation(profit_score)
            }
            
        except Exception as e:
            app_logger.error(f"수익성 계산 오류: {e}")
            return {
                'error': str(e),
                'profit_score': 0,
                'recommendation': '분석 실패'
            }
    
    def _get_price_margin(self, price: int) -> float:
        """가격대별 마진율 반환"""
        for (min_price, max_price), margin in self.price_margins.items():
            if min_price <= price < max_price:
                return margin
        return self.min_margin_rate
    
    def _estimate_shipping_cost(self, product: WholesaleProduct) -> int:
        """배송비 추정"""
        # 상품 정보에서 배송비 확인
        product_info = product.product_info or {}
        
        # 명시된 배송비가 있으면 사용
        if 'shipping_fee' in product_info:
            return int(product_info['shipping_fee'])
        
        # 없으면 가격대별 추정
        if product.wholesale_price < 10000:
            return 3000
        elif product.wholesale_price < 30000:
            return 2500
        else:
            return 0  # 무료배송
    
    def _analyze_competition(self, category: str, price_range: Tuple[float, float], 
                           marketplace: str) -> Dict[str, Any]:
        """경쟁 상품 분석"""
        min_price, max_price = price_range
        
        # 동일 카테고리, 비슷한 가격대의 베스트셀러 조회
        competitors = self.db.query(BestsellerData).filter(
            and_(
                BestsellerData.category == category,
                BestsellerData.marketplace == marketplace,
                BestsellerData.price >= min_price,
                BestsellerData.price <= max_price,
                BestsellerData.collected_at >= datetime.now() - timedelta(days=7)
            )
        ).all()
        
        if not competitors:
            return {
                'count': 0,
                'level': '낮음',
                'avg_rank': 100,
                'avg_reviews': 0
            }
        
        # 경쟁 지표 계산
        avg_rank = np.mean([c.rank for c in competitors])
        avg_reviews = np.mean([c.review_count for c in competitors])
        
        # 경쟁 수준 판단
        if len(competitors) > 50 and avg_rank < 30:
            level = '매우 높음'
        elif len(competitors) > 30 and avg_rank < 50:
            level = '높음'
        elif len(competitors) > 10:
            level = '보통'
        else:
            level = '낮음'
        
        return {
            'count': len(competitors),
            'level': level,
            'avg_rank': round(avg_rank, 1),
            'avg_reviews': round(avg_reviews)
        }
    
    def _predict_sales(self, category: str, price: int, 
                      competition: Dict[str, Any]) -> Dict[str, Any]:
        """판매량 예측"""
        # 기본 판매량 (카테고리별)
        base_sales = {
            '전자제품': 50,
            '패션의류': 100,
            '생활용품': 80,
            '식품': 150,
            '화장품': 70,
            '스포츠': 60
        }
        
        monthly_units = base_sales.get(category, 50)
        
        # 경쟁 수준에 따른 조정
        competition_multiplier = {
            '매우 높음': 0.5,
            '높음': 0.7,
            '보통': 1.0,
            '낮음': 1.5
        }
        
        monthly_units *= competition_multiplier.get(competition['level'], 1.0)
        
        # 가격대에 따른 조정
        if price < 10000:
            monthly_units *= 1.3
        elif price > 50000:
            monthly_units *= 0.7
        
        monthly_units = int(monthly_units)
        
        return {
            'monthly_units': monthly_units,
            'monthly_revenue': monthly_units * price,
            'confidence': self._calculate_confidence(competition)
        }
    
    def _calculate_confidence(self, competition: Dict[str, Any]) -> str:
        """예측 신뢰도 계산"""
        if competition['count'] >= 30:
            return '높음'
        elif competition['count'] >= 10:
            return '보통'
        else:
            return '낮음'
    
    def _calculate_profit_score(self, net_margin: float, 
                              sales_forecast: Dict[str, Any],
                              competition: Dict[str, Any]) -> float:
        """수익성 점수 계산 (0-100)"""
        # 마진율 점수 (40점 만점)
        margin_score = min(net_margin / 0.3 * 40, 40)
        
        # 예상 판매량 점수 (30점 만점)
        sales_score = min(sales_forecast['monthly_units'] / 100 * 30, 30)
        
        # 경쟁 수준 점수 (30점 만점)
        competition_scores = {
            '낮음': 30,
            '보통': 20,
            '높음': 10,
            '매우 높음': 5
        }
        comp_score = competition_scores.get(competition['level'], 15)
        
        total_score = margin_score + sales_score + comp_score
        
        return round(total_score, 1)
    
    def _get_recommendation(self, score: float) -> str:
        """수익성 점수에 따른 추천"""
        if score >= 80:
            return "강력 추천 - 높은 수익성 예상"
        elif score >= 60:
            return "추천 - 양호한 수익성"
        elif score >= 40:
            return "조건부 추천 - 신중한 검토 필요"
        elif score >= 20:
            return "비추천 - 낮은 수익성"
        else:
            return "강력 비추천 - 손실 위험"
    
    def analyze_batch_products(self, product_codes: List[str]) -> List[Dict[str, Any]]:
        """여러 상품 일괄 분석"""
        results = []
        
        for code in product_codes:
            product = self.db.query(WholesaleProduct).filter(
                WholesaleProduct.product_code == code
            ).first()
            
            if product:
                analysis = self.calculate_profit_potential(product)
                analysis['product_code'] = code
                analysis['product_name'] = product.product_name
                results.append(analysis)
        
        # 수익성 점수로 정렬
        return sorted(results, key=lambda x: x.get('profit_score', 0), reverse=True)
    
    def get_profit_distribution(self, days: int = 30) -> Dict[str, Any]:
        """수익성 분포 분석"""
        try:
            # 최근 분석된 상품들
            recent_products = self.db.query(WholesaleProduct).filter(
                WholesaleProduct.updated_at >= datetime.now() - timedelta(days=days)
            ).limit(100).all()
            
            if not recent_products:
                return {"status": "no_data"}
            
            # 각 상품의 수익성 계산
            profit_scores = []
            margin_rates = []
            
            for product in recent_products:
                analysis = self.calculate_profit_potential(product)
                if 'profit_score' in analysis:
                    profit_scores.append(analysis['profit_score'])
                    margin_rates.append(analysis.get('net_margin', 0))
            
            if not profit_scores:
                return {"status": "no_valid_data"}
            
            # 분포 계산
            return {
                "status": "success",
                "total_products": len(profit_scores),
                "avg_profit_score": round(np.mean(profit_scores), 1),
                "avg_margin_rate": round(np.mean(margin_rates), 3),
                "score_distribution": {
                    "excellent": len([s for s in profit_scores if s >= 80]),
                    "good": len([s for s in profit_scores if 60 <= s < 80]),
                    "fair": len([s for s in profit_scores if 40 <= s < 60]),
                    "poor": len([s for s in profit_scores if 20 <= s < 40]),
                    "very_poor": len([s for s in profit_scores if s < 20])
                },
                "margin_distribution": {
                    "over_30": len([m for m in margin_rates if m >= 0.3]),
                    "20_30": len([m for m in margin_rates if 0.2 <= m < 0.3]),
                    "10_20": len([m for m in margin_rates if 0.1 <= m < 0.2]),
                    "under_10": len([m for m in margin_rates if m < 0.1])
                }
            }
            
        except Exception as e:
            app_logger.error(f"수익성 분포 분석 오류: {e}")
            return {"status": "error", "message": str(e)}