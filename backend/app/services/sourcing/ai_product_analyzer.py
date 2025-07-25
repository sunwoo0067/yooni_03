"""AI 기반 상품 분석 및 예측 서비스"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from sqlalchemy.orm import Session

from ...models.product import Product
from ...models.market import MarketProduct, MarketSalesData
from ...models.trend import TrendKeyword
from ...models.order import Order


class AIProductAnalyzer:
    """AI 기반 상품 분석기"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.sales_predictor = None
        self.trend_predictor = None
        self.price_optimizer = None
        self.market_saturation_model = None
        self._load_or_train_models()
        
    def _load_or_train_models(self):
        """모델 로드 또는 학습"""
        try:
            # 저장된 모델 로드 시도
            self.sales_predictor = joblib.load('models/sales_predictor.pkl')
            self.trend_predictor = joblib.load('models/trend_predictor.pkl')
            self.price_optimizer = joblib.load('models/price_optimizer.pkl')
            self.market_saturation_model = joblib.load('models/market_saturation.pkl')
        except:
            # 모델이 없으면 새로 학습
            self.logger.info("AI 모델 학습 시작")
            self._train_all_models()
            
    async def analyze_product_potential(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """상품 잠재력 종합 분석"""
        analysis = {
            'product_info': product_data,
            'sales_prediction': await self._predict_sales(product_data),
            'trend_analysis': await self._analyze_trend_fit(product_data),
            'price_optimization': await self._optimize_price(product_data),
            'market_saturation': await self._check_market_saturation(product_data),
            'competition_analysis': await self._analyze_competition(product_data),
            'seasonality_score': await self._calculate_seasonality(product_data),
            'profit_estimation': await self._estimate_profit(product_data),
            'risk_assessment': await self._assess_risks(product_data),
            'recommendation': await self._generate_recommendation(product_data),
            'analyzed_at': datetime.now()
        }
        
        # 종합 점수 계산
        analysis['total_score'] = self._calculate_total_score(analysis)
        
        return analysis
        
    async def _predict_sales(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """판매량 예측"""
        features = self._extract_sales_features(product_data)
        
        if self.sales_predictor and len(features) > 0:
            # 30일, 60일, 90일 판매량 예측
            predictions = {}
            
            for days in [30, 60, 90]:
                features_with_time = features + [days]
                prediction = self.sales_predictor.predict([features_with_time])[0]
                predictions[f'day_{days}'] = int(prediction)
                
            # 예측 신뢰도 계산
            confidence = self._calculate_prediction_confidence(features)
            
            return {
                'predictions': predictions,
                'confidence': confidence,
                'factors': self._get_sales_factors(product_data),
                'growth_rate': self._calculate_growth_rate(predictions)
            }
        else:
            # 모델이 없거나 특징이 부족한 경우 휴리스틱 예측
            return self._heuristic_sales_prediction(product_data)
            
    async def _analyze_trend_fit(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """트렌드 적합성 분석"""
        # 상품 키워드 추출
        keywords = self._extract_keywords(product_data.get('name', ''))
        
        # 트렌드 키워드와 매칭
        trend_scores = []
        matched_trends = []
        
        for keyword in keywords:
            trends = self.db.query(TrendKeyword).filter(
                TrendKeyword.keyword.ilike(f'%{keyword}%'),
                TrendKeyword.analyzed_at >= datetime.now() - timedelta(days=7)
            ).all()
            
            for trend in trends:
                score = trend.trend_score * (1.5 if trend.trend_direction == 'rising' else 1.0)
                trend_scores.append(score)
                matched_trends.append({
                    'keyword': trend.keyword,
                    'score': score,
                    'direction': trend.trend_direction,
                    'platform': trend.platform
                })
                
        avg_trend_score = np.mean(trend_scores) if trend_scores else 0
        
        return {
            'trend_fit_score': round(avg_trend_score, 2),
            'matched_trends': matched_trends[:5],  # 상위 5개
            'trend_lifecycle': self._estimate_trend_lifecycle(avg_trend_score),
            'recommended_timing': self._get_trend_timing_advice(avg_trend_score)
        }
        
    async def _optimize_price(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """최적 가격 분석"""
        current_price = product_data.get('price', 0)
        category = product_data.get('category', '')
        
        # 카테고리별 가격 분포 분석
        similar_products = self.db.query(MarketProduct).filter(
            MarketProduct.category == category,
            MarketProduct.price > 0
        ).limit(100).all()
        
        if similar_products:
            prices = [p.price for p in similar_products]
            price_stats = {
                'min': min(prices),
                'max': max(prices),
                'mean': np.mean(prices),
                'median': np.median(prices),
                'std': np.std(prices)
            }
            
            # 최적 가격 구간 계산
            optimal_ranges = self._calculate_optimal_price_ranges(
                price_stats, 
                product_data
            )
            
            return {
                'current_price': current_price,
                'market_stats': price_stats,
                'optimal_ranges': optimal_ranges,
                'price_positioning': self._get_price_positioning(current_price, price_stats),
                'elasticity_estimate': self._estimate_price_elasticity(category)
            }
        else:
            return {
                'current_price': current_price,
                'message': '가격 데이터 부족',
                'suggestion': '시장 평균가 대비 10-20% 할인 시작 권장'
            }
            
    async def _check_market_saturation(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 포화도 분석"""
        category = product_data.get('category', '')
        
        # 해당 카테고리 상품 수와 증가율
        total_products = self.db.query(Product).filter(
            Product.category == category,
            Product.is_active == True
        ).count()
        
        # 최근 30일 신규 상품
        new_products = self.db.query(Product).filter(
            Product.category == category,
            Product.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        # 평균 판매량 추이
        sales_trend = await self._get_category_sales_trend(category)
        
        # 포화도 점수 계산 (0-100)
        saturation_score = self._calculate_saturation_score(
            total_products,
            new_products,
            sales_trend
        )
        
        return {
            'saturation_score': saturation_score,
            'saturation_level': self._get_saturation_level(saturation_score),
            'total_competitors': total_products,
            'new_entrants_monthly': new_products,
            'market_growth_rate': sales_trend.get('growth_rate', 0),
            'entry_recommendation': self._get_entry_recommendation(saturation_score),
            'differentiation_needed': saturation_score > 70
        }
        
    async def _analyze_competition(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """경쟁 분석"""
        category = product_data.get('category', '')
        price = product_data.get('price', 0)
        
        # 유사 가격대 경쟁 상품
        competitors = self.db.query(MarketProduct).filter(
            MarketProduct.category == category,
            MarketProduct.price.between(price * 0.8, price * 1.2)
        ).order_by(MarketProduct.rank).limit(20).all()
        
        if competitors:
            # 경쟁 강도 분석
            competition_analysis = {
                'direct_competitors': len(competitors),
                'avg_review_count': np.mean([c.review_count for c in competitors]),
                'avg_rating': np.mean([c.rating for c in competitors if c.rating > 0]),
                'price_competition': self._analyze_price_competition(competitors, price),
                'top_competitors': [
                    {
                        'name': c.product_name[:50],
                        'price': c.price,
                        'reviews': c.review_count,
                        'rank': c.rank
                    }
                    for c in competitors[:5]
                ],
                'competitive_advantages': self._identify_advantages(product_data, competitors),
                'market_gaps': self._find_market_gaps(competitors)
            }
        else:
            competition_analysis = {
                'direct_competitors': 0,
                'message': '직접 경쟁 상품 없음 - 블루오션 가능성',
                'recommendation': '시장 테스트 권장'
            }
            
        return competition_analysis
        
    async def _calculate_seasonality(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """계절성 분석"""
        keywords = self._extract_keywords(product_data.get('name', ''))
        category = product_data.get('category', '')
        
        # 계절 키워드 매칭
        seasonal_patterns = {
            'spring': ['봄', '춘', '벚꽃', '신학기', '새싹'],
            'summer': ['여름', '하', '바캉스', '수영', '시원한'],
            'autumn': ['가을', '추', '단풍', '추석', '김장'],
            'winter': ['겨울', '동', '크리스마스', '따뜻한', '연말']
        }
        
        seasonality_scores = {}
        for season, patterns in seasonal_patterns.items():
            score = sum(1 for pattern in patterns if any(pattern in kw for kw in keywords))
            seasonality_scores[season] = score
            
        # 카테고리별 계절성 가중치
        category_seasonality = self._get_category_seasonality(category)
        
        # 현재 시즌과의 적합성
        current_season = self._get_current_season()
        season_fit = seasonality_scores.get(current_season, 0) * 2
        
        return {
            'seasonality_scores': seasonality_scores,
            'current_season_fit': season_fit,
            'peak_seasons': [s for s, score in seasonality_scores.items() if score > 0],
            'year_round': sum(seasonality_scores.values()) == 0,
            'category_seasonality': category_seasonality,
            'timing_advice': self._get_seasonality_advice(seasonality_scores, current_season)
        }
        
    async def _estimate_profit(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """수익성 예측"""
        price = product_data.get('price', 0)
        wholesale_price = product_data.get('wholesale_price', price * 0.6)
        
        # 예상 판매량 (이전 예측 결과 활용)
        sales_prediction = await self._predict_sales(product_data)
        monthly_sales = sales_prediction['predictions'].get('day_30', 0)
        
        # 비용 계산
        costs = {
            'product_cost': wholesale_price,
            'platform_fee': price * 0.1,  # 플랫폼 수수료 10% 가정
            'shipping_cost': 3000,  # 평균 배송비
            'marketing_cost': price * 0.05,  # 마케팅 비용 5%
            'other_costs': price * 0.02  # 기타 비용 2%
        }
        
        total_cost = sum(costs.values())
        profit_per_unit = price - total_cost
        profit_margin = (profit_per_unit / price) * 100 if price > 0 else 0
        
        # 월별 예상 수익
        monthly_profit = profit_per_unit * monthly_sales
        
        # ROI 계산
        initial_investment = wholesale_price * 50  # 초기 재고 50개 가정
        monthly_roi = (monthly_profit / initial_investment) * 100 if initial_investment > 0 else 0
        
        return {
            'unit_profit': round(profit_per_unit),
            'profit_margin': round(profit_margin, 1),
            'monthly_profit_estimate': round(monthly_profit),
            'monthly_roi': round(monthly_roi, 1),
            'break_even_units': int(initial_investment / profit_per_unit) if profit_per_unit > 0 else 999,
            'cost_breakdown': costs,
            'profitability_rating': self._rate_profitability(profit_margin, monthly_roi)
        }
        
    async def _assess_risks(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """리스크 평가"""
        risks = {
            'market_risk': await self._assess_market_risk(product_data),
            'competition_risk': await self._assess_competition_risk(product_data),
            'seasonality_risk': await self._assess_seasonality_risk(product_data),
            'supplier_risk': await self._assess_supplier_risk(product_data),
            'regulatory_risk': await self._assess_regulatory_risk(product_data)
        }
        
        # 종합 리스크 점수 (0-100, 높을수록 위험)
        total_risk_score = np.mean([r['score'] for r in risks.values()])
        
        return {
            'total_risk_score': round(total_risk_score, 1),
            'risk_level': self._get_risk_level(total_risk_score),
            'risk_factors': risks,
            'mitigation_strategies': self._get_mitigation_strategies(risks),
            'risk_adjusted_score': self._calculate_risk_adjusted_score(
                product_data, 
                total_risk_score
            )
        }
        
    async def _generate_recommendation(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI 추천 생성"""
        # 모든 분석 결과를 종합
        all_analyses = {
            'sales': await self._predict_sales(product_data),
            'trend': await self._analyze_trend_fit(product_data),
            'price': await self._optimize_price(product_data),
            'saturation': await self._check_market_saturation(product_data),
            'competition': await self._analyze_competition(product_data),
            'seasonality': await self._calculate_seasonality(product_data),
            'profit': await self._estimate_profit(product_data),
            'risk': await self._assess_risks(product_data)
        }
        
        # 종합 점수 계산
        scores = {
            'sales_score': all_analyses['sales'].get('confidence', 0) * 100,
            'trend_score': all_analyses['trend']['trend_fit_score'],
            'saturation_score': 100 - all_analyses['saturation']['saturation_score'],
            'profit_score': min(100, all_analyses['profit']['profit_margin'] * 2),
            'risk_score': 100 - all_analyses['risk']['total_risk_score']
        }
        
        total_score = np.mean(list(scores.values()))
        
        # 추천 결정
        if total_score >= 80:
            decision = 'STRONG_BUY'
            confidence = '매우 높음'
        elif total_score >= 65:
            decision = 'BUY'
            confidence = '높음'
        elif total_score >= 50:
            decision = 'CONSIDER'
            confidence = '보통'
        elif total_score >= 35:
            decision = 'CAUTION'
            confidence = '낮음'
        else:
            decision = 'AVOID'
            confidence = '매우 낮음'
            
        # 상세 추천 사항
        recommendations = []
        
        # 판매 전략
        if all_analyses['sales']['predictions']['day_30'] > 100:
            recommendations.append("대량 구매 준비 - 높은 판매량 예상")
        else:
            recommendations.append("소량 테스트 판매 권장")
            
        # 가격 전략
        price_position = all_analyses['price'].get('price_positioning', '')
        if 'high' in price_position:
            recommendations.append("가격 인하 검토 - 경쟁력 확보")
        elif 'low' in price_position:
            recommendations.append("프리미엄 포지셔닝 가능")
            
        # 타이밍 전략
        if all_analyses['seasonality']['current_season_fit'] > 2:
            recommendations.append("즉시 진입 - 시즌 적합성 높음")
        else:
            recommendations.append(f"진입 시기: {all_analyses['seasonality']['peak_seasons']}")
            
        # 차별화 전략
        if all_analyses['saturation']['saturation_score'] > 70:
            recommendations.append("차별화 필수 - 포화 시장")
            recommendations.extend(all_analyses['competition'].get('market_gaps', []))
            
        return {
            'decision': decision,
            'confidence': confidence,
            'total_score': round(total_score, 1),
            'score_breakdown': scores,
            'key_recommendations': recommendations[:5],
            'action_items': self._generate_action_items(decision, all_analyses),
            'expected_outcome': self._predict_outcome(total_score, all_analyses)
        }
        
    def _extract_sales_features(self, product_data: Dict[str, Any]) -> List[float]:
        """판매 예측을 위한 특징 추출"""
        features = []
        
        # 기본 특징
        features.append(product_data.get('price', 0))
        features.append(product_data.get('review_count', 0))
        features.append(product_data.get('rating', 0))
        features.append(1 if product_data.get('is_prime', False) else 0)
        
        # 카테고리 인코딩
        category = product_data.get('category', '')
        category_map = {
            '패션': 1, '뷰티': 2, '식품': 3, '생활용품': 4,
            '디지털': 5, '스포츠': 6, '육아': 7
        }
        features.append(category_map.get(category, 0))
        
        # 계절 특징
        month = datetime.now().month
        features.append(month)
        
        return features
        
    def _calculate_prediction_confidence(self, features: List[float]) -> float:
        """예측 신뢰도 계산"""
        # 특징의 완전성 체크
        non_zero_features = sum(1 for f in features if f != 0)
        completeness = non_zero_features / len(features)
        
        # 데이터 품질 점수
        quality_score = min(1.0, completeness * 1.2)
        
        return round(quality_score * 100, 1)
        
    def _heuristic_sales_prediction(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """휴리스틱 기반 판매량 예측"""
        base_sales = 10  # 기본 판매량
        
        # 리뷰 수 기반 보정
        reviews = product_data.get('review_count', 0)
        if reviews > 1000:
            base_sales *= 5
        elif reviews > 500:
            base_sales *= 3
        elif reviews > 100:
            base_sales *= 2
            
        # 가격 기반 보정
        price = product_data.get('price', 30000)
        if price < 10000:
            base_sales *= 1.5
        elif price > 50000:
            base_sales *= 0.7
            
        # 평점 기반 보정
        rating = product_data.get('rating', 0)
        if rating >= 4.5:
            base_sales *= 1.3
        elif rating < 3.5:
            base_sales *= 0.5
            
        return {
            'predictions': {
                'day_30': int(base_sales * 30),
                'day_60': int(base_sales * 55),
                'day_90': int(base_sales * 80)
            },
            'confidence': 60.0,
            'method': 'heuristic'
        }
        
    def _calculate_total_score(self, analysis: Dict[str, Any]) -> float:
        """종합 점수 계산"""
        weights = {
            'sales': 0.25,
            'trend': 0.20,
            'profit': 0.25,
            'risk': 0.15,
            'competition': 0.15
        }
        
        scores = {
            'sales': analysis['sales_prediction'].get('confidence', 0),
            'trend': analysis['trend_analysis']['trend_fit_score'],
            'profit': min(100, analysis['profit_estimation']['profit_margin'] * 2),
            'risk': 100 - analysis['risk_assessment']['total_risk_score'],
            'competition': 100 - min(100, analysis['competition_analysis'].get('direct_competitors', 0) * 5)
        }
        
        total = sum(scores[k] * weights[k] for k in weights.keys())
        
        return round(total, 1)
        
    def _train_all_models(self):
        """모든 AI 모델 학습"""
        # 실제 구현에서는 충분한 데이터로 학습
        # 여기서는 기본 모델 초기화만
        self.sales_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.trend_predictor = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.price_optimizer = RandomForestRegressor(n_estimators=50, random_state=42)
        self.market_saturation_model = GradientBoostingClassifier(n_estimators=50, random_state=42)
        
        # 더미 데이터로 초기 학습 (실제로는 실제 데이터 사용)
        X_dummy = np.random.rand(100, 6)
        y_sales_dummy = np.random.randint(10, 1000, 100)
        
        self.sales_predictor.fit(X_dummy, y_sales_dummy)
        
    # 추가 헬퍼 메서드들...
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        import re
        # 간단한 키워드 추출 (실제로는 더 정교한 NLP 사용)
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if len(w) > 1]
        
    def _get_current_season(self) -> str:
        """현재 계절"""
        month = datetime.now().month
        if 3 <= month <= 5:
            return 'spring'
        elif 6 <= month <= 8:
            return 'summer'
        elif 9 <= month <= 11:
            return 'autumn'
        else:
            return 'winter'