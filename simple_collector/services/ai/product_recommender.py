"""
AI 기반 상품 추천 시스템
- 트렌드 기반 추천
- 수익성 기반 추천
- 복합 점수 기반 추천
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from database.models_v2 import WholesaleProduct, MarketplaceProduct
from collectors.bestseller_collector import BestsellerData
from services.ai.trend_analyzer import TrendAnalyzer
from services.ai.profit_predictor import ProfitPredictor
from utils.logger import app_logger


class ProductRecommender:
    """상품 추천 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.trend_analyzer = TrendAnalyzer(db)
        self.profit_predictor = ProfitPredictor(db)
    
    async def get_recommendations(self, 
                                recommendation_type: str = 'balanced',
                                limit: int = 20) -> Dict[str, Any]:
        """상품 추천 생성
        
        Args:
            recommendation_type: 'trend' (트렌드), 'profit' (수익성), 'balanced' (균형)
            limit: 추천 상품 수
        """
        try:
            if recommendation_type == 'trend':
                recommendations = await self._get_trend_recommendations(limit)
            elif recommendation_type == 'profit':
                recommendations = self._get_profit_recommendations(limit)
            else:  # balanced
                recommendations = await self._get_balanced_recommendations(limit)
            
            return {
                "status": "success",
                "recommendation_type": recommendation_type,
                "count": len(recommendations),
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            app_logger.error(f"추천 생성 오류: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _get_trend_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """트렌드 기반 추천"""
        # 트렌드 분석
        trends = await self.trend_analyzer.analyze_market_trends(days=14)
        
        if trends['status'] != 'success':
            return []
        
        recommendations = []
        
        # 1. 급상승 상품에서 매칭되는 도매 상품 찾기
        for rising in trends.get('rising_products', [])[:10]:
            # 카테고리와 가격대가 비슷한 도매 상품 찾기
            wholesale_products = self._find_similar_wholesale_products(
                category=rising['category'],
                target_price=rising['price'] * 0.7,  # 도매가는 판매가의 약 70%
                limit=3
            )
            
            for product in wholesale_products:
                # 수익성 분석
                profit_analysis = self.profit_predictor.calculate_profit_potential(product)
                
                recommendation = {
                    'product_code': product.product_code,
                    'product_name': product.product_name,
                    'supplier': product.supplier,
                    'category': product.category,
                    'wholesale_price': product.wholesale_price,
                    'trend_info': {
                        'matching_bestseller': rising['product_name'],
                        'rank_change': rising['rank_change'],
                        'current_rank': rising['current_rank']
                    },
                    'profit_analysis': profit_analysis,
                    'recommendation_score': self._calculate_trend_score(
                        rising['rank_change'],
                        profit_analysis.get('profit_score', 0)
                    ),
                    'reason': f"'{rising['product_name']}'와 유사한 상품으로 순위 {rising['rank_change']}위 상승 중"
                }
                
                recommendations.append(recommendation)
        
        # 점수순 정렬 및 중복 제거
        seen_codes = set()
        unique_recommendations = []
        
        for rec in sorted(recommendations, key=lambda x: x['recommendation_score'], reverse=True):
            if rec['product_code'] not in seen_codes:
                seen_codes.add(rec['product_code'])
                unique_recommendations.append(rec)
                if len(unique_recommendations) >= limit:
                    break
        
        return unique_recommendations
    
    def _get_profit_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """수익성 기반 추천"""
        # 최근 업데이트된 상품 중 수익성 분석
        recent_products = self.db.query(WholesaleProduct).filter(
            and_(
                WholesaleProduct.is_active == True,
                WholesaleProduct.wholesale_price > 0,
                WholesaleProduct.updated_at >= datetime.now() - timedelta(days=7)
            )
        ).limit(100).all()
        
        recommendations = []
        
        for product in recent_products:
            profit_analysis = self.profit_predictor.calculate_profit_potential(product)
            
            # 수익성 점수가 60점 이상인 상품만
            if profit_analysis.get('profit_score', 0) >= 60:
                # 베스트셀러 매칭 확인
                bestseller_match = self._find_bestseller_match(
                    category=product.category,
                    price_range=(
                        profit_analysis['recommended_price'] * 0.8,
                        profit_analysis['recommended_price'] * 1.2
                    )
                )
                
                recommendation = {
                    'product_code': product.product_code,
                    'product_name': product.product_name,
                    'supplier': product.supplier,
                    'category': product.category,
                    'wholesale_price': product.wholesale_price,
                    'profit_analysis': profit_analysis,
                    'bestseller_match': bestseller_match,
                    'recommendation_score': profit_analysis['profit_score'],
                    'reason': profit_analysis['recommendation']
                }
                
                recommendations.append(recommendation)
        
        # 점수순 정렬
        return sorted(recommendations, key=lambda x: x['recommendation_score'], reverse=True)[:limit]
    
    async def _get_balanced_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """균형잡힌 추천 (트렌드 + 수익성)"""
        # 트렌드 추천 가져오기
        trend_recs = await self._get_trend_recommendations(limit * 2)
        
        # 수익성 추천 가져오기
        profit_recs = self._get_profit_recommendations(limit * 2)
        
        # 통합 및 재점수 계산
        all_recommendations = {}
        
        # 트렌드 추천 추가
        for rec in trend_recs:
            code = rec['product_code']
            all_recommendations[code] = rec
            all_recommendations[code]['has_trend'] = True
            all_recommendations[code]['has_profit'] = False
        
        # 수익성 추천 추가/병합
        for rec in profit_recs:
            code = rec['product_code']
            if code in all_recommendations:
                # 이미 트렌드에 있으면 병합
                all_recommendations[code]['has_profit'] = True
                all_recommendations[code]['profit_analysis'] = rec['profit_analysis']
                # 복합 점수 재계산
                all_recommendations[code]['recommendation_score'] = (
                    all_recommendations[code]['recommendation_score'] * 0.5 +
                    rec['recommendation_score'] * 0.5
                )
                all_recommendations[code]['reason'] = "트렌드와 수익성 모두 우수"
            else:
                all_recommendations[code] = rec
                all_recommendations[code]['has_trend'] = False
                all_recommendations[code]['has_profit'] = True
        
        # 복합 점수가 높은 순으로 정렬
        recommendations = sorted(
            all_recommendations.values(),
            key=lambda x: (
                x.get('has_trend', False) and x.get('has_profit', False),  # 둘 다 있는 것 우선
                x['recommendation_score']
            ),
            reverse=True
        )
        
        return recommendations[:limit]
    
    def _find_similar_wholesale_products(self, category: str, 
                                       target_price: float,
                                       limit: int = 5) -> List[WholesaleProduct]:
        """유사한 도매 상품 찾기"""
        # 가격 범위 설정 (±30%)
        min_price = target_price * 0.7
        max_price = target_price * 1.3
        
        products = self.db.query(WholesaleProduct).filter(
            and_(
                WholesaleProduct.category == category,
                WholesaleProduct.wholesale_price >= min_price,
                WholesaleProduct.wholesale_price <= max_price,
                WholesaleProduct.is_active == True
            )
        ).order_by(
            func.abs(WholesaleProduct.wholesale_price - target_price)
        ).limit(limit).all()
        
        return products
    
    def _find_bestseller_match(self, category: str, 
                             price_range: tuple) -> Optional[Dict[str, Any]]:
        """베스트셀러 매칭 찾기"""
        min_price, max_price = price_range
        
        bestseller = self.db.query(BestsellerData).filter(
            and_(
                BestsellerData.category == category,
                BestsellerData.price >= min_price,
                BestsellerData.price <= max_price,
                BestsellerData.rank <= 50  # 50위 이내
            )
        ).order_by(BestsellerData.rank).first()
        
        if bestseller:
            return {
                'product_name': bestseller.product_name,
                'rank': bestseller.rank,
                'marketplace': bestseller.marketplace,
                'price': bestseller.price,
                'reviews': bestseller.review_count
            }
        
        return None
    
    def _calculate_trend_score(self, rank_change: int, profit_score: float) -> float:
        """트렌드 추천 점수 계산"""
        # 순위 상승 점수 (최대 50점)
        trend_score = min(rank_change * 2, 50)
        
        # 수익성 점수 (최대 50점)
        profit_component = profit_score * 0.5
        
        return round(trend_score + profit_component, 1)
    
    def get_category_opportunities(self) -> List[Dict[str, Any]]:
        """카테고리별 기회 분석"""
        try:
            # 카테고리별 추천
            category_recs = self.trend_analyzer.get_category_recommendations()
            
            opportunities = []
            
            for cat_rec in category_recs[:10]:
                category = cat_rec['category']
                
                # 해당 카테고리의 도매 상품 수
                wholesale_count = self.db.query(func.count(WholesaleProduct.product_code)).filter(
                    WholesaleProduct.category == category
                ).scalar()
                
                # 수익성 분석 샘플
                sample_products = self.db.query(WholesaleProduct).filter(
                    WholesaleProduct.category == category
                ).limit(5).all()
                
                avg_profit_score = 0
                if sample_products:
                    profit_scores = []
                    for product in sample_products:
                        analysis = self.profit_predictor.calculate_profit_potential(product)
                        profit_scores.append(analysis.get('profit_score', 0))
                    avg_profit_score = np.mean(profit_scores)
                
                opportunity = {
                    'category': category,
                    'market_potential': cat_rec['recommendation_score'],
                    'current_bestsellers': cat_rec['product_count'],
                    'wholesale_available': wholesale_count,
                    'avg_profit_score': round(avg_profit_score, 1),
                    'opportunity_score': self._calculate_opportunity_score(
                        market_potential=cat_rec['recommendation_score'],
                        supply_demand_ratio=wholesale_count / max(cat_rec['product_count'], 1),
                        profit_potential=avg_profit_score
                    ),
                    'recommendation': self._get_opportunity_recommendation(
                        wholesale_count,
                        cat_rec['product_count'],
                        avg_profit_score
                    )
                }
                
                opportunities.append(opportunity)
            
            return sorted(opportunities, key=lambda x: x['opportunity_score'], reverse=True)
            
        except Exception as e:
            app_logger.error(f"카테고리 기회 분석 오류: {e}")
            return []
    
    def _calculate_opportunity_score(self, market_potential: float,
                                   supply_demand_ratio: float,
                                   profit_potential: float) -> float:
        """기회 점수 계산"""
        # 시장 잠재력 (40%)
        market_score = market_potential * 0.4
        
        # 공급/수요 비율 (30%) - 적절한 비율일수록 높은 점수
        if supply_demand_ratio < 0.5:  # 공급 부족
            supply_score = 30
        elif supply_demand_ratio > 2:  # 공급 과잉
            supply_score = 10
        else:  # 적절한 비율
            supply_score = 25
        
        # 수익 잠재력 (30%)
        profit_score = profit_potential * 0.3
        
        return round(market_score + supply_score + profit_score, 1)
    
    def _get_opportunity_recommendation(self, wholesale_count: int,
                                      bestseller_count: int,
                                      avg_profit_score: float) -> str:
        """기회 추천 메시지"""
        if wholesale_count < bestseller_count * 0.5 and avg_profit_score >= 60:
            return "높은 기회 - 공급 확대 필요"
        elif wholesale_count > bestseller_count * 2:
            return "경쟁 포화 - 차별화 전략 필요"
        elif avg_profit_score < 40:
            return "낮은 수익성 - 신중한 접근 필요"
        else:
            return "안정적 기회 - 선별적 진입 추천"